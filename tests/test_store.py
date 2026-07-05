from caption_helper.models import Sentence
from caption_helper.subtitles_json import initialize_subtitle_files
from caption_helper.web.store import ProjectStore


def test_clear_downstream_artifacts_asr(tmp_path) -> None:
    store = ProjectStore(tmp_path)
    meta = store.create_project("clip.mp4")
    project_dir = store.project_path(meta.id)
    (project_dir / "source.mp4").write_bytes(b"video")

    sentences = [Sentence("hello", 0, 0, 1000)]
    initialize_subtitle_files(project_dir, sentences)
    (project_dir / "audio.wav").write_bytes(b"wav")
    (project_dir / "segments" / "0001_spk0_0-1000.wav").write_bytes(b"seg")
    (project_dir / "speaker_refs").mkdir(exist_ok=True)
    (project_dir / "speaker_refs" / "spk0.wav").write_bytes(b"ref")
    (project_dir / "tts_segments").mkdir(exist_ok=True)
    (project_dir / "tts_segments" / "0001.wav").write_bytes(b"tts")
    (project_dir / "synthesis_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "output_video.mp4").write_bytes(b"mp4")

    store.clear_downstream_artifacts(meta.id, through="asr")

    assert (project_dir / "source.mp4").is_file()
    assert not (project_dir / "audio.wav").is_file()
    assert not (project_dir / "subtitles.json").is_file()
    assert not list((project_dir / "segments").glob("*.wav"))
    assert not list((project_dir / "speaker_refs").glob("*.wav"))
    assert not list((project_dir / "tts_segments").glob("*.wav"))
    assert not (project_dir / "output_video.mp4").is_file()


def test_clear_downstream_artifacts_tts(tmp_path) -> None:
    store = ProjectStore(tmp_path)
    meta = store.create_project("clip.mp4")
    project_dir = store.project_path(meta.id)
    sentences = [Sentence("hello", 0, 0, 1000)]
    initialize_subtitle_files(project_dir, sentences)
    (project_dir / "tts_segments").mkdir(exist_ok=True)
    (project_dir / "tts_segments" / "0001.wav").write_bytes(b"tts")
    (project_dir / "synthesis_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "output_video.mp4").write_bytes(b"mp4")

    store.clear_downstream_artifacts(meta.id, through="tts")

    assert (project_dir / "subtitles.json").is_file()
    assert not list((project_dir / "tts_segments").glob("*.wav"))
    assert not (project_dir / "output_video.mp4").is_file()


def test_clear_downstream_artifacts_remux(tmp_path) -> None:
    store = ProjectStore(tmp_path)
    meta = store.create_project("clip.mp4")
    project_dir = store.project_path(meta.id)
    (project_dir / "output_audio.wav").write_bytes(b"wav")
    (project_dir / "output_video.mp4").write_bytes(b"mp4")
    (project_dir / "remux_manifest.json").write_text("{}", encoding="utf-8")

    store.clear_downstream_artifacts(meta.id, through="remux")

    assert not (project_dir / "output_audio.wav").is_file()
    assert not (project_dir / "output_video.mp4").is_file()
    assert not (project_dir / "remux_manifest.json").is_file()
