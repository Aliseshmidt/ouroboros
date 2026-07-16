"""Build the narrated, subtitled hackathon MP4 from verified browser screenshots."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUBMISSION = REPO_ROOT / "submission"
TMP = REPO_ROOT / "tmp" / "video"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
SAY = shutil.which("say") or "/usr/bin/say"

SCREENSHOTS = (
    ("01_overview.png", 18),
    ("02_trace.png", 18),
    ("03_patterns.png", 24),
    ("04_generated_skill.png", 20),
    ("05_sandbox.png", 24),
    ("06_approval.png", 18),
    ("07_result.png", 24),
    ("08_value.png", 14),
    ("09_evolution.png", 12),
)


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _plain_voiceover() -> str:
    lines = []
    for raw in (SUBMISSION / "VOICEOVER_TEXT.md").read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("**Статус:"):
            lines.append("")
            continue
        stripped = re.sub(r"[`*_]", "", stripped)
        lines.append(stripped)
    paragraphs = [" ".join(block.split()) for block in "\n".join(lines).split("\n\n") if block.strip()]
    return "\n\n".join(paragraphs) + "\n"


def _duration(path: Path) -> float:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def _subtitles(text: str, duration: float) -> str:
    words = text.split()
    chunks = [words[index : index + 11] for index in range(0, len(words), 11)]
    usable = max(1.0, duration - 0.6)
    cursor = 0.2
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        share = usable * len(chunk) / len(words)
        end = min(duration - 0.15, cursor + share)
        blocks.append(f"{index}\n{_timestamp(cursor)} --> {_timestamp(end)}\n{' '.join(chunk)}\n")
        cursor = end
    return "\n".join(blocks)


def build() -> dict[str, object]:
    if not all(Path(tool).is_file() for tool in (FFMPEG, FFPROBE, SAY)):
        raise RuntimeError("ffmpeg, ffprobe, and macOS say are required")
    TMP.mkdir(parents=True, exist_ok=True)
    frames_dir = TMP / "verification_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    voice_text = _plain_voiceover()
    (TMP / "voice.txt").write_text(voice_text, encoding="utf-8")
    voice_path = TMP / "voice.aiff"
    voice_path.unlink(missing_ok=True)
    _run([SAY, "-v", "Milena", "-r", "182", "-f", str(TMP / "voice.txt"), "-o", str(voice_path)])
    audio_duration = _duration(voice_path)
    if not 150 <= audio_duration < 176:
        raise RuntimeError(f"narration duration {audio_duration:.2f}s is outside the 150–175s target")

    subtitle_path = SUBMISSION / "DEMO_VIDEO.srt"
    subtitle_path.write_text(_subtitles(voice_text, audio_duration), encoding="utf-8")
    weights_total = sum(weight for _, weight in SCREENSHOTS)
    concat_lines = []
    for filename, weight in SCREENSHOTS:
        image_path = SUBMISSION / "screenshots" / filename
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        concat_lines.extend((f"file '{image_path}'", f"duration {audio_duration * weight / weights_total:.6f}"))
    concat_lines.append(f"file '{SUBMISSION / 'screenshots' / SCREENSHOTS[-1][0]}'")
    concat_path = TMP / "screenshots.ffconcat"
    concat_path.write_text("ffconcat version 1.0\n" + "\n".join(concat_lines) + "\n", encoding="utf-8")

    video_path = SUBMISSION / "DEMO_VIDEO.mp4"
    video_filter = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,"
        "format=yuv420p"
    )
    _run(
        [
            FFMPEG,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-i",
            str(voice_path),
            "-i",
            str(subtitle_path),
            "-vf",
            video_filter,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map",
            "2:s:0",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=rus",
            "-disposition:s:0",
            "default",
            "-shortest",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    )
    final_duration = _duration(video_path)
    probe = subprocess.run(
        [FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    probe_payload = json.loads(probe.stdout)
    stream_types = {stream.get("codec_type") for stream in probe_payload.get("streams", [])}
    if not ({"audio", "video", "subtitle"} <= stream_types and final_duration < 180):
        raise RuntimeError("final MP4 is missing a stream or exceeds 180 seconds")
    _run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "fps=1/25,scale=960:-1",
            str(frames_dir / "frame_%02d.png"),
        ]
    )
    verification = {
        "ok": True,
        "path": "submission/DEMO_VIDEO.mp4",
        "duration_seconds": round(final_duration, 3),
        "target_duration_seconds": "150–175",
        "video_stream": "video" in stream_types,
        "audio_stream": "audio" in stream_types,
        "subtitle_stream": "subtitle" in stream_types,
        "subtitles": "default Russian mov_text track + submission/DEMO_VIDEO.srt",
        "source": "nine screenshots captured from the real localhost browser E2E",
        "synthetic_data_only": True,
        "paid_api_cost_usd": 0.0,
        "ffprobe": probe_payload,
    }
    artifacts = REPO_ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "video_verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return verification


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
