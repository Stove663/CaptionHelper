## 1. Model default change

- [x] 1.1 Update `tts/moss_tts.py` default model to `OpenMOSS-Team/MOSS-TTS-Local-Transformer` (1.7B)
- [x] 1.2 Configure T4-safe inference: `dtype=bfloat16`, `attn_implementation=sdpa`, disable cuDNN SDPA per MOSS-TTS README
- [x] 1.3 Add `--tts-model` choices: `local-1.7b` (default), `local-v1.5-4b`; remove 8B from recommended options
- [x] 1.4 Update `moss-tts-segment-synthesis` references from v1.5 8B to Local-Transformer 1.7B in code comments and config

## 2. Code-mix detection and synthesis

- [x] 2.1 Implement `tts/code_mix.py`: `is_code_mixed(text)`, `detect_language_mode(text)` → `auto | Chinese | English`
- [x] 2.2 Update `synthesize()` to omit `language` tag for code-mixed cues; pass `language="Chinese"` or `language="English"` for pure text
- [x] 2.3 Add unit tests: pure Chinese, pure English, zh-en mixed (e.g., "打开 terminal 窗口"), Chinese with numbers
- [x] 2.4 Record `code_mixed` and `language_mode` in `synthesis_manifest.json`

## 3. Hardware preflight

- [x] 3.1 Implement `tts/preflight.py`: check CUDA, GPU name, total VRAM, CUDA version
- [x] 3.2 Implement model-VRAM compatibility matrix: block 8B on ≤16 GB; warn on 4B if <12 GB free
- [x] 3.3 Call preflight at `caption-helper web` startup (log GPU info) and before `POST /synthesize`
- [x] 3.4 Return HTTP 400 with actionable message when model/GPU combination is incompatible
- [x] 3.5 Add unit tests for preflight logic with mocked GPU properties (T4 16GB, 8GB, no CUDA)

## 4. Memory management for T4

- [x] 4.1 Process one cue at a time with `batch_size=1`; call `torch.cuda.empty_cache()` between cues
- [x] 4.2 Cap `max_new_tokens` per segment based on slot duration to avoid runaway generation
- [x] 4.3 Log peak VRAM usage per synthesis job in manifest

## 5. Debian 12 documentation

- [x] 5.1 Add Debian 12 section to README: `apt install ffmpeg`, NVIDIA driver link, CUDA compatibility notes
- [x] 5.2 Document `uv pip install --torch-backend cu128 -e ".[tts]"` for MOSS-TTS optional extra
- [x] 5.3 Document recommended model for T4 16 GB (1.7B default) and optional 4B upgrade
- [x] 5.4 Add troubleshooting: OOM → switch to 1.7B; CUDA not found → driver install

## 6. Verification on T4

- [x] 6.1 Synthesize pure Chinese cue on T4; verify no OOM and correct duration
- [x] 6.2 Synthesize zh-en mixed cue (e.g., "请使用 Docker 部署") on T4; verify both languages pronounced
- [x] 6.3 Verify 8B model request is blocked on 16 GB GPU
- [x] 6.4 Verify preflight logs T4 name and 16 GB VRAM on Debian 12 test environment
- [x] 6.5 Confirm peak VRAM stays below 10 GB for 1.7B model during typical segment synthesis
