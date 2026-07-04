## Why

Users routinely replace Chinese words with English equivalents in edited subtitles (e.g., "我们今天讨论 machine learning 的问题"). TTS synthesis must handle **Chinese–English code-mixed text** naturally while cloning the speaker's voice from the original segment.

The deployment target is **Debian 12 with a single Nvidia T4 (16 GB VRAM)**. The previously proposed default model MOSS-TTS-v1.5 (8B) exceeds safe VRAM limits on this hardware. Model selection, dtype, and attention backends must be chosen to run reliably on T4 without OOM.

## What Changes

- Set default TTS model to **MOSS-TTS-Local-Transformer (1.7B)** — fits T4 16 GB with headroom; supports voice cloning and `tokens` duration control
- Offer optional **MOSS-TTS-Local-Transformer-v1.5 (4B)** via `--tts-model` for users who want higher quality and can tolerate higher VRAM
- **Exclude MOSS-TTS-v1.5 (8B)** from default/recommended configs on 16 GB GPUs; document as unsupported without quantization
- Add **zh-en code-mix synthesis** path: detect mixed cues, pass text without forcing a single language tag; use MOSS-TTS multilingual/code-switch capability
- Add **hardware preflight check** at synthesis startup: CUDA availability, GPU name, VRAM, warn/block if below minimum
- Document **Debian 12** install steps: NVIDIA driver, CUDA-compatible PyTorch wheel, ffmpeg, MOSS-TTS optional extra
- Update `moss-tts-synthesis` specs with code-mix scenarios and T4-safe defaults

## Capabilities

### New Capabilities

- `tts-hardware-preflight`: GPU/VRAM detection and model compatibility gating before TTS jobs

### Modified Capabilities

- `moss-tts-synthesis`: Default model changed to 1.7B Local-Transformer; add zh-en code-mix requirements; T4 16 GB constraints

## Impact

- **Model default change**: `OpenMOSS-Team/MOSS-TTS-Local-Transformer` replaces `MOSS-TTS-v1.5` as default
- **VRAM**: 1.7B bf16 ≈ 4–6 GB peak on T4; 4B optional ≈ 8–12 GB; 8B not recommended
- **Attention backend**: T4 (sm_75) uses SDPA, not FlashAttention 2 (requires sm_80+)
- **OS**: Debian 12 install guide with `apt` ffmpeg, NVIDIA driver notes
- **Depends on**: `moss-tts-segment-synthesis` (TTS pipeline); supersedes its 8B default when both are applied
