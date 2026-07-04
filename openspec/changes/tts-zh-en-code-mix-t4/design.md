## Context

CaptionHelper's TTS stage re-synthesizes edited subtitle segments using [MOSS-TTS](https://github.com/OpenMOSS/MOSS-TTS) voice cloning. A primary editing pattern is replacing Chinese terms with English while keeping surrounding Chinese text — producing **zh-en code-mixed** cues such as `"请大家打开 terminal 窗口"`.

The production environment is **Debian 12 + Nvidia T4 16 GB**. The prior change `moss-tts-segment-synthesis` defaulted to MOSS-TTS-v1.5 (8B MossTTSDelay), which loads ~16 GB of weights in bf16 alone and will OOM on a 16 GB T4 once activations and the audio tokenizer are included.

MOSS-TTS Family explicitly supports multilingual and code-switched synthesis in v1.5-line models, and the 1.7B MossTTSLocal checkpoint achieves strong speaker similarity (ZH SIM 79.62%) while fitting smaller GPUs.

## Goals / Non-Goals

**Goals:**

- Reliable TTS on T4 16 GB without OOM under normal segment lengths
- Natural pronunciation of zh-en mixed `text_edited` strings
- Voice cloning still uses per-cue `segments/*.wav` reference
- Duration control via `tokens` + ffmpeg trim/pad unchanged
- Preflight warns or blocks incompatible model/GPU combinations
- Debian 12 documented as supported platform

**Non-Goals:**

- Quantized GGUF / llama.cpp inference (future optimization)
- Automatic translation — user manually inserts English words
- Multi-GPU or tensor parallelism
- Windows/macOS deployment guides (Debian 12 primary)

## Decisions

### 1. Default model: MOSS-TTS-Local-Transformer 1.7B

**Choice:** `OpenMOSS-Team/MOSS-TTS-Local-Transformer`

**Rationale:**
- **VRAM**: 1.7B parameters in bf16 ≈ 3.4 GB weights; with audio tokenizer and activations, peak ≈ 5–7 GB — safe on T4 16 GB
- **Quality**: MossTTSLocal 1.7B leads open-source ZH SIM (79.62%) per MOSS-TTS benchmarks
- **API**: Same `AutoModel` + `AutoProcessor` + `build_user_message(text, reference, tokens)` as Delay models
- **Duration control**: Supports `tokens` parameter for slot fitting

**Alternatives considered:**

| Model | Params | T4 16 GB | Code-mix | Verdict |
|-------|--------|----------|----------|---------|
| MOSS-TTS-v1.5 | 8B | OOM risk | ✓ explicit | Reject as default |
| MOSS-TTS-Local-Transformer-v1.5 | 4B | Tight (~10–12 GB) | ✓ v1.5 features | Optional `--tts-model` |
| MOSS-TTS-Nano | 0.1B | ✓ CPU/GPU | ✓ multilingual | Lower cloning quality; fallback only |

### 2. Optional upgrade: Local-Transformer-v1.5 4B

**Choice:** Expose `--tts-model OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5` for users who want 48 kHz stereo and v1.5 improvements.

**Rationale:** May fit T4 16 GB at bf16 + SDPA with `batch_size=1` and `torch.cuda.empty_cache()` between cues. Preflight checks VRAM ≥ 12 GB free before allowing 4B.

### 3. Zh-en code-mix handling

**Choice:** Pass `text_edited` as-is to `processor.build_user_message()` **without** a fixed `language` tag when the cue contains both CJK and Latin characters.

**Detection:** `is_code_mixed(text)` → `True` if text matches CJK regex AND Latin word regex.

```python
# Code-mixed cue
processor.build_user_message(text="请大家打开 terminal 窗口", reference=[seg_wav], tokens=tokens)

# Pure Chinese cue
processor.build_user_message(text="欢迎大家", reference=[seg_wav], tokens=tokens, language="Chinese")

# Pure English cue (rare)
processor.build_user_message(text="Welcome everyone", reference=[seg_wav], tokens=tokens, language="English")
```

**Rationale:** MOSS-TTS v1.5 family documents code-switched synthesis; forcing `language="Chinese"` on mixed text may degrade English word pronunciation. MOSS-TTS 1.0 Local-Transformer handles multilingual input without requiring per-language tags for every word.

**Fallback:** If synthesis quality is poor on a mixed cue, allow per-project `--tts-language Chinese` override.

### 4. T4 attention and dtype configuration

**Choice:**

```python
dtype = torch.bfloat16  # T4 supports bf16
attn_implementation = "sdpa"  # T4 sm_75; FlashAttention 2 requires sm_80+
torch.backends.cuda.enable_cudnn_sdp(False)  # per MOSS-TTS README
```

**Rationale:** MOSS-TTS README explicitly disables cuDNN SDPA and falls back to flash/mem-efficient/math SDPA on CUDA. T4 cannot use `flash_attention_2`.

### 5. Hardware preflight

**Choice:** Run at `caption-helper web` startup and before each synthesis job:

1. `torch.cuda.is_available()`
2. `torch.cuda.get_device_name()` → log GPU model
3. `torch.cuda.get_device_properties().total_memory` → if < 14 GB, block 4B model; if < 10 GB, warn
4. If user requests 8B model on ≤ 16 GB GPU → HTTP 400 with message to use 1.7B default

**Minimum spec table:**

| Model | Min VRAM | T4 16 GB |
|-------|----------|----------|
| Local-Transformer 1.7B | 8 GB | ✓ Recommended default |
| Local-Transformer-v1.5 4B | 12 GB | ✓ Optional |
| MOSS-TTS-v1.5 8B | 20 GB+ | ✗ Blocked |

### 6. Debian 12 deployment

**Choice:** Document in README:

```bash
# Debian 12
sudo apt-get install -y ffmpeg
# NVIDIA driver + CUDA (user installs per NVIDIA Debian guide)
uv pip install --torch-backend cu128 -e ".[tts]"
```

**PyTorch wheel:** Use `cu128` or `cu126` backend matching installed CUDA; MOSS-TTS pins `torch==2.9.1+cu128`.

**Python:** 3.12 recommended per MOSS-TTS docs.

### 7. Synthesis manifest extension

Add fields to `synthesis_manifest.json` per cue:

- `code_mixed: true/false`
- `language_mode: "auto" | "Chinese" | "English"`
- `model_id`
- `gpu_name`
- `peak_vram_mb`

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 1.7B lower quality vs 8B | Optional 4B model; document quality trade-off |
| Code-mix pronunciation inconsistent | No language tag on mixed text; user can preview and re-edit |
| 4B OOM on long segments | `max_new_tokens` cap; sequential one-cue-at-a-time; `empty_cache()` |
| Debian CUDA/driver mismatch | Document driver version check; preflight logs CUDA version |
| MOSS-TTS torch pin conflicts | Optional `[tts]` extra isolates heavy deps |

## Migration Plan

1. Apply after `moss-tts-segment-synthesis`
2. Delta spec overrides default model from 8B v1.5 → 1.7B Local-Transformer
3. Existing `moss-tts-segment-synthesis` tasks referencing v1.5 should follow this change's model defaults when both are present

## Open Questions

- Should 4B be auto-selected when preflight detects ≥ 14 GB free VRAM? _Default no; user opts in via `--tts-model`._
- Per-speaker language preference for mixed content? _Defer; use text-level detection only._
