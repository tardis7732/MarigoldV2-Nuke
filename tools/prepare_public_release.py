"""Prepare portable examples, documentation media and explicit release archives."""

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def portable(source, destination):
    content = source.read_text(encoding="utf-8")
    lines = []
    for line in content.splitlines():
        if line.startswith(("#!", "#write_info")):
            continue
        if re.match(r"^ (pythonExe|daemonScript|name [A-Za-z]:[/\\])", line):
            continue
        lines.append(line)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for source, name in files:
            bundle.write(source, name)
    print(path.name, path.stat().st_size)


def main():
    import imageio_ffmpeg

    media = ROOT / "docs/media"
    media.mkdir(parents=True, exist_ok=True)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    examples = ROOT / "examples"
    video = examples / "video_demo"
    portable(examples / "MarigoldV2_Normals_Ready.nk", examples / "Normals_Still.nk")
    portable(video / "MarigoldV2_Video_Example.nk", video / "Normals_Video.nk")
    for src, name in [
        (video / "comparison.mp4", "video-comparison.mp4"),
        (video / "comparison_poster.png", "video-comparison.png"),
        (examples / "renders/normals_preview.png", "still-normals.png"),
    ]:
        shutil.copy2(src, media / name)
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-v",
            "error",
            "-y",
            "-i",
            str(video / "comparison.mp4"),
            "-filter_complex",
            "fps=12,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
            "-loop",
            "0",
            str(media / "video-comparison.gif"),
        ],
        check=True,
    )
    shutil.copy2(video / "validation.json", ROOT / "docs/video-validation.json")
    example_files = [
        examples / "Normals_Still.nk",
        video / "Normals_Video.nk",
        examples / "README.md",
        video / "README.md",
        examples / "assets/church.jpg",
        examples / "renders/normals.0001.exr",
        examples / "renders/normals_preview.png",
    ]
    example_files += sorted((video / "source").glob("source.*.png"))
    example_files += sorted((video / "normals").glob("normals.*.exr"))
    example_files += [
        video / name for name in ("comparison.mp4", "source_clip.mp4", "normals_preview.mp4")
    ]
    example_files += [ROOT / "THIRD_PARTY_NOTICES.md", ROOT / "LICENSE"]
    example_files += sorted((ROOT / "licenses").glob("*.txt"))
    archive(
        dist / "MarigoldV2-Nuke-examples.zip",
        [(path, path.relative_to(ROOT).as_posix()) for path in example_files],
    )
    binary = ROOT / "ofx/build/MarigoldV2Normals.ofx.bundle/Contents/Win64/MarigoldV2Normals.ofx"
    files = [(binary, binary.relative_to(ROOT).as_posix())]
    files += [
        (ROOT / "LICENSE", "LICENSE"),
        (ROOT / "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
    ]
    files += [
        (path, path.relative_to(ROOT).as_posix()) for path in (ROOT / "licenses").glob("*.txt")
    ]
    files += [(ROOT / "ofx/include/openfx/LICENSE.md", "licenses/OpenFX-BSD-3-Clause.md")]
    archive(dist / "MarigoldV2-Nuke-Windows-x64.zip", files)
    checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dist.glob("*.zip"))
    }
    (dist / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in checksums.items()), encoding="utf-8"
    )
    print(json.dumps(checksums, indent=2))


if __name__ == "__main__":
    main()
