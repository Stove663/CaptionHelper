## 1. Project scaffolding

- [x] 1.1 Create `pyproject.toml` with package metadata, `caption-helper` CLI entry point, and dependencies (`funasr`, `torch`, `soundfile`)
- [x] 1.2 Scaffold `src/caption_helper/` package with `__init__.py` and module stubs (`cli.py`, `extract.py`, `transcribe.py`, `srt.py`, `split.py`, `pipeline.py`)
- [x] 1.3 Add `README.md` with prerequisites (ffmpeg, optional CUDA), install steps (`uv sync`), and usage example

## 2. Audio extraction

- [x] 2.1 Implement `extract.py`: `check_ffmpeg()` to verify ffmpeg is on PATH
- [x] 2.2 Implement `extract_audio(video_path, output_wav)` using ffmpeg (`-vn -ac 1 -ar 16000`)
- [x] 2.3 Add unit test for ffmpeg check (mock subprocess) and integration test with a short sample video

## 3. FunASR transcription

- [x] 3.1 Implement `transcribe.py`: `Transcriber` class wrapping `AutoModel` with Fun-ASR-Nano-2512, fsmn-vad, cam++
- [x] 3.2 Configure `vad_kwargs`, `trust_remote_code`, device auto-detection, and `--hub` / `--language` options
- [x] 3.3 Return typed `Sentence` dataclass list from `sentence_info` (`text`, `spk`, `start`, `end`)
- [x] 3.4 Add test with mocked `AutoModel.generate` returning sample `sentence_info`

## 4. SRT generation

- [x] 4.1 Implement `srt.py`: `ms_to_srt_timestamp(ms)` converter
- [x] 4.2 Implement `write_srt(sentences, output_path)` with `[说话人 {spk}] {text}` format
- [x] 4.3 Add unit tests for timestamp conversion edge cases (0 ms, hour rollover) and SRT output format

## 5. Audio segment splitting

- [x] 5.1 Implement `split.py`: `split_segments(full_wav, sentences, segments_dir)` using ffmpeg per segment
- [x] 5.2 Generate filenames `{index:04d}_spk{spk}_{start}-{end}.wav`
- [x] 5.3 Add unit test verifying filename generation and segment count matches sentence list

## 6. Pipeline orchestration

- [x] 6.1 Implement `pipeline.py`: `process(video_path, output_dir, **options)` wiring extract → transcribe → srt → split
- [x] 6.2 Default output directory to `<video_stem>_output/`; create `segments/` subdirectory
- [x] 6.3 Add progress logging for each pipeline stage

## 7. CLI

- [x] 7.1 Implement `cli.py` with `process` subcommand: positional `video`, optional `--output-dir`, `--device`, `--language`, `--hub`
- [x] 7.2 Wire `caption-helper` entry point in `pyproject.toml`
- [x] 7.3 Handle errors gracefully (missing file, ffmpeg absent, model failure) with clear messages

## 8. Verification

- [x] 8.1 Run full pipeline on a short test video and verify `subtitles.srt`, `audio.wav`, and `segments/` output
- [x] 8.2 Validate SRT timestamps and speaker labels match FunASR `sentence_info`
- [x] 8.3 Confirm segment WAV count equals SRT cue count
