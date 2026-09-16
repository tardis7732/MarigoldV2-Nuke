"""Download Qwen transformer/VAE and selected Marigold normals/depth assets."""

import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assets", required=True)
    p.add_argument("--task", choices=("normals", "depth", "all"), default="all")
    args = p.parse_args()
    from huggingface_hub import snapshot_download

    base = Path(args.assets).expanduser().resolve() / "checkpoints"
    snapshot_download(
        "Qwen/Qwen-Image-Edit-2509",
        revision="d3968ef930e841f4c73640fb8afa3b306a78167e",
        allow_patterns=["transformer/*", "vae/*"],
        local_dir=str(base / "Qwen-Image-Edit-2509"),
    )
    patterns = []
    if args.task in ("normals", "all"):
        patterns += ["normals/*", "qwen_text_embeddings/*normals*"]
    if args.task in ("depth", "all"):
        patterns += ["depth/Log-stage2/*", "qwen_text_embeddings/*depth_realimg512*"]
    snapshot_download(
        "huawei-bayerlab/marigold-v2-0",
        revision="cdf9810fb690886391a63aec012b5f501064fb0d",
        allow_patterns=patterns,
        local_dir=str(base / "Marigold-V2"),
    )
    print(args.task, "inference assets downloaded to", base)


if __name__ == "__main__":
    main()
