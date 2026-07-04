import argparse
import json
import logging
import sys
from pathlib import Path

from caption_helper.extract import FFmpegNotFoundError
from caption_helper.pipeline import process


def _add_process_parser(subparsers: argparse._SubParsersAction) -> None:
    process_parser = subparsers.add_parser(
        "process", help="Process a video file into subtitles and audio segments"
    )
    process_parser.add_argument("video", type=Path, help="Input video file path")
    process_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: <video_stem>_output/)",
    )
    process_parser.add_argument(
        "--device",
        default=None,
        help="Torch device for ASR (default: cuda:0 if available else cpu)",
    )
    process_parser.add_argument(
        "--language",
        default="中文",
        help="ASR language hint for Fun-ASR-Nano (default: 中文)",
    )
    process_parser.add_argument(
        "--hub",
        default=None,
        help='Model hub: "hf" for HuggingFace, omit for ModelScope',
    )
    process_parser.add_argument(
        "--max-segment-s",
        type=int,
        default=30,
        help="VAD max single segment time in seconds (default: 30)",
    )
    process_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )


def _add_web_parser(subparsers: argparse._SubParsersAction) -> None:
    web_parser = subparsers.add_parser("web", help="Start the CaptionHelper Web UI")
    web_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    web_parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    web_parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path.home() / ".caption-helper",
        help="Data directory for projects (default: ~/.caption-helper)",
    )
    web_parser.add_argument(
        "--frontend-dist",
        type=Path,
        default=None,
        help="Path to frontend dist (default: frontend/dist)",
    )
    web_parser.add_argument(
        "--device",
        default=None,
        help="Torch device for ASR jobs",
    )
    web_parser.add_argument("--language", default="中文", help="ASR language hint")
    web_parser.add_argument("--hub", default=None, help='Model hub ("hf" or omit)')
    web_parser.add_argument(
        "--tts-model",
        default="local-1.7b",
        choices=["local-1.7b", "local-v1.5-4b"],
        help="TTS model preset (default: local-1.7b = MOSS-TTS-Local-Transformer 1.7B)",
    )
    web_parser.add_argument(
        "--tts-device",
        default=None,
        help="Torch device for TTS (default: cuda:0 if available else cpu)",
    )
    web_parser.add_argument(
        "--tokens-per-second",
        type=float,
        default=25.0,
        help="MOSS-TTS tokens per second for duration mapping (default: 25)",
    )
    web_parser.add_argument(
        "--min-ref-duration-ms",
        type=int,
        default=1500,
        help="Minimum reference audio duration in ms (default: 1500)",
    )
    web_parser.add_argument(
        "--min-quality-score",
        type=float,
        default=0.5,
        help="Minimum reference quality score 0-1 (default: 0.5)",
    )
    web_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )


def _add_remux_parser(subparsers: argparse._SubParsersAction) -> None:
    remux_parser = subparsers.add_parser(
        "remux", help="Assemble output audio and remux final video for a project directory"
    )
    remux_parser.add_argument("project_dir", type=Path, help="Project or output directory")
    remux_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )


def _add_build_refs_parser(subparsers: argparse._SubParsersAction) -> None:
    refs_parser = subparsers.add_parser(
        "build-refs", help="Rebuild speaker reference bank for a project directory"
    )
    refs_parser.add_argument("project_dir", type=Path, help="Project or output directory")
    refs_parser.add_argument(
        "--min-ref-duration-ms",
        type=int,
        default=1500,
        help="Minimum reference audio duration in ms (default: 1500)",
    )
    refs_parser.add_argument(
        "--min-quality-score",
        type=float,
        default=0.5,
        help="Minimum reference quality score 0-1 (default: 0.5)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="caption-helper",
        description="Extract audio, transcribe, and split video into subtitled segments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_process_parser(subparsers)
    _add_web_parser(subparsers)
    _add_build_refs_parser(subparsers)
    _add_remux_parser(subparsers)
    return parser


def _run_web(args: argparse.Namespace) -> int:
    import uvicorn

    from caption_helper.web.app import create_app

    app = create_app(args.data_dir, args.frontend_dist, tts_model=args.tts_model)
    app.state.jobs.set_pipeline_options(
        device=args.device,
        language=args.language,
        hub=args.hub,
    )
    app.state.jobs.set_tts_options(
        model=args.tts_model,
        device=args.tts_device,
        tokens_per_second=args.tokens_per_second,
    )
    app.state.jobs.set_ref_options(
        min_ref_duration_ms=args.min_ref_duration_ms,
        min_quality_score=args.min_quality_score,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    verbose = getattr(args, "verbose", False)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "process":
        try:
            output = process(
                args.video,
                args.output_dir,
                device=args.device,
                language=args.language,
                hub=args.hub,
                max_single_segment_time=args.max_segment_s * 1000,
            )
        except FFmpegNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(output)
        return 0

    if args.command == "web":
        return _run_web(args)

    if args.command == "build-refs":
        from caption_helper.tts.reference import ReferenceConfig, build_speaker_reference_bank

        cfg = ReferenceConfig(
            min_ref_duration_ms=args.min_ref_duration_ms,
            min_quality_score=args.min_quality_score,
        )
        result = build_speaker_reference_bank(args.project_dir, config=cfg)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "remux":
        from caption_helper.remux.pipeline import remux_pipeline

        try:
            manifest = remux_pipeline(args.project_dir)
        except FFmpegNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
