## Context

CaptionHelper integrates GLM-TTS via `_GLMRuntime` in `tts/glm_tts.py`, wrapping upstream `glmtts_inference.load_models` and `generate_long`. The integration currently hardcodes `use_phoneme=False` at load and inference time. MOSS-TTS already has code-mix handling (`detect_language_mode` → `auto`) and the project has compression-risk + natural-pace guidance, but that guidance is provider-agnostic.

GLM-TTS upstream ([zai-org/GLM-TTS](https://github.com/zai-org/GLM-TTS)) implements mixed-text and phoneme-in in `cosyvoice/cli/frontend.py` and `glmtts_inference.py`.

### GLM-TTS Phoneme-in call chain (upstream)

```
CaptionHelper _GLMRuntime.synthesize_utterance(text)
        │
        ▼
load_models(use_phoneme=?)                          glmtts_inference.py
        │
        ├─ load_frontends(use_phoneme)
        │       └─ TextFrontEnd(use_phoneme)          cosyvoice/cli/frontend.py
        │              ├─ if True: G2P_zh(), G2P_able_1word.json,
        │              │           G2P_replace_dict.jsonl
        │              └─ zh/en TN models (WeTextProcessing or ttsfrd)
        │
        └─ vq32k-phoneme-tokenizer (always loaded for tokenize_fn)
        │
        ▼
generate_long(..., use_phoneme=?, text_info=[uttid, synth_text])
        │
        ├─ text_frontend.split_by_len(syn_text)     # 30–60 char chunks
        │
        └─ for each chunk:
              tts_text_tn = text_frontend.text_normalize(tts_text)
              if use_phoneme:
                  tts_text_tn = text_frontend.g2p_infer(tts_text_tn)
              tts_text_token = frontend._extract_text_token(tts_text_tn)
              local_llm_forward(...) → local_flow_forward(...) → audio
```

### `g2p_infer` behavior (critical for expectations)

`TextFrontEnd.g2p_infer` does **not** convert English graphemes to IPA. Pipeline:

1. `_tokenize_by_replace_dict` — apply `configs/G2P_replace_dict.jsonl` overrides
2. `_split_mixed_text` — split into Chinese vs non-Chinese blocks
3. **Non-Chinese blocks (English, digits)**: appended **unchanged**
4. **Chinese blocks**: `process_one` → `_align_and_replace` — hybrid phoneme+text for polyphones / whitelist chars (`G2P_able_1word.json`)

Phoneme-in therefore improves **Chinese pronunciation context** around embedded English and polyphone disambiguation; English words remain grapheme input to the phoneme tokenizer.

### `text_normalize` behavior for mixed text

When `contains_chinese(text)` is true (typical code-mixed cue), GLM applies `_normalize_chinese_text` then **`.lower()`** on the full string. This can flatten English acronyms (`API` → `api`). CaptionHelper preprocessing should protect Latin segments before handing text to GLM.

### CaptionHelper gap vs MOSS

| Concern | MOSS-TTS | GLM-TTS (current) |
|---------|----------|-------------------|
| Code-mix language hint | `language_mode=auto` omits tag | N/A |
| Duration control in fixed-slot | `tokens` param | None; `fit_duration` only |
| Phoneme / G2P | N/A | `use_phoneme=False` always |

Fixed-slot + `fit_duration` is the dominant quality risk for GLM on mixed cues; natural-pace is the primary mitigation.

## Goals / Non-Goals

**Goals:**

- Auto-enable phoneme-in for code-mixed cues when `glm_phoneme_mode=auto`
- Light mixed-text prep before GLM normalize (spacing, acronym casing)
- Provider-aware natural-pace UX when `tts_provider=glm-tts`
- Manifest provenance: `phoneme_enabled`, `text_prep_applied`
- Separate runtime cache for phoneme on/off if required by `TextFrontEnd` init

**Non-Goals:**

- GLM-TTS_RL model variant
- English IPA injection (not supported by upstream `g2p_infer`)
- Per-cue reference selection by English keyword
- Phoneme dictionary editor in UI
- Changing MOSS-TTS code-mix behavior
- Auto-switching `sync_mode` without user action

## Decisions

### 1. Phoneme mode: `auto` for code-mixed cues only

**Choice:** Add `glm_phoneme_mode` to project meta: `auto` (default) | `on` | `off`.

```python
def resolve_use_phoneme(text: str, mode: str) -> bool:
    if mode == "on": return True
    if mode == "off": return False
    return is_code_mixed(text)  # auto
```

Pass resolved flag to both `load_models(use_phoneme=...)` and `generate_long(use_phoneme=...)`.

**Rationale:** Matches GLM CLI `--phoneme` intent; avoids phoneme overhead on pure Chinese cues; upstream phoneme helps Chinese blocks in mixed sentences.

**Alternatives:**

| Approach | Verdict |
|----------|---------|
| Always `use_phoneme=True` | Reject — slower, may alter pure-Chinese prosody |
| Never phoneme | Reject — leaves capability unused |
| Per-cue UI toggle | Defer — project-level is enough for v1 |

### 2. Runtime cache keyed by `(home, use_phoneme)`

**Choice:** Extend `_GLMRuntime._cache` key from `str(home)` to `f"{home}:phoneme={use_phoneme}"` because `TextFrontEnd.__init__(use_phoneme)` loads different resources.

**Rationale:** `load_models` binds phoneme state at frontend construction; toggling per cue within one job requires correct cache partition.

### 3. Mixed-text preprocessing layer

**Choice:** New `prepare_glm_mixed_text(text) -> str` applied only when `is_code_mixed(text)`:

- Insert spaces between CJK and Latin boundaries if missing (`打开terminal` → `打开 terminal`)
- Preserve contiguous Latin runs' original casing (counteract downstream `.lower()` impact where possible by documenting limitation — full fix would require upstream patch; prep uses Unicode markers or zero-width only if tested; **v1: spacing only**)

**Rationale:** Minimal, testable, no fork of GLM frontend. Spacing is the highest-confidence fix for CosyVoice tokenization.

**v1 scope:** spacing normalization only; document that acronym casing may still be lowered by GLM `text_normalize`.

### 4. Synthesis order in `_GLMRuntime`

**Choice:**

```
synth_text = prepare_glm_mixed_text(text)  # if code_mixed
synth_text = text_frontend.text_normalize(synth_text)
# g2p_infer happens inside generate_long when use_phoneme=True
```

Do **not** call `g2p_infer` in CaptionHelper — keep single call site in upstream `generate_long` to match CLI behavior.

### 5. Provider-aware natural-pace UX

**Choice:** Extend existing compression-risk and editor banner logic:

| Condition | Banner |
|-----------|--------|
| `tts_provider=moss-tts`, code-mixed at-risk | Existing text (already shipped) |
| `tts_provider=glm-tts`, any code-mixed modified cue + `sync_mode=fixed-slot` | Stronger warning: GLM has no duration hint; fixed-slot will trim English |
| `tts_provider=glm-tts`, code-mixed at-risk | Same as above + `recommend_natural_pace: true` (existing API field) |

Add `recommend_natural_pace_glm: bool` to compression-risk response **or** reuse `recommend_natural_pace` with provider-qualified message in UI (prefer reusing field; add `warning_message` string from API to avoid hardcoding provider logic twice in frontend).

**API:** `GET /compression-risk` returns optional `provider_guidance: string | null` when `tts_provider=glm-tts` and project has code-mixed modified cues.

**Synthesize preflight:** `POST /synthesize` returns HTTP 400 with guidance message when `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and ≥1 code-mixed modified cue — **warn only** if `force=true` query param (mirror existing compression pattern if any; else soft warning in response body before job enqueue).

**Decision:** Editor banner + optional synthesize confirmation dialog; do not hard-block synthesis (user may accept quality trade-off).

### 6. Manifest fields

Add to `CueSynthesisRecord` when `tts_provider=glm-tts`:

- `phoneme_enabled: bool`
- `text_prep_applied: bool`
- `glm_phoneme_mode: str` (project setting snapshot)

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Phoneme mode changes Chinese prosody near English words | `auto` only on mixed cues; A/B via manifest |
| Two runtime caches doubles VRAM if both loaded | Sequential cues use one mode per cue; cache eviction on mode switch |
| `text_normalize().lower()` hurts `API`, `GPU` | Document; spacing prep in v1; future upstream or post-normalize patch |
| English still mispronounced with phoneme on | Set expectations in README; recommend natural-pace; MOSS may be better for heavy English |
| GLM repo API drift | Pin GLM-TTS tag in README; integration tests mock `generate_long` kwargs |

## Migration Plan

1. Default `glm_phoneme_mode=auto` via `meta.json` `setdefault` on read — no migration script
2. Existing projects gain phoneme-on for mixed cues on next GLM synthesis
3. Rollback: set `glm_phoneme_mode=off` in meta or switch provider to MOSS-TTS

## Open Questions

- Pin GLM-TTS git commit for reproducible `g2p_infer` behavior? _Recommend yes in README during implementation._
- Hard-block GLM fixed-slot + code-mixed synthesis? _v1: warn only._
- Add `provider_guidance` to compression-risk API vs frontend-only strings? _Prefer API field for i18n consistency._
