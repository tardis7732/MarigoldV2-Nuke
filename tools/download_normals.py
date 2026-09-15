"""Download only the Qwen transformer/VAE and Marigold normals assets."""

import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assets", required=True)
    args = p.parse_args()
    from huggingface_hub import snapshot_download

    base = Path(args.assets).expanduser().resolve() / "checkpoints"
    snapshot_download(
        "Qwen/Qwen-Image-Edit-2509",
        revision="d3968ef930e841f4c73640fb8afa3b306a78167e",
        allow_patterns=["transformer/*", "vae/*"],
        local_dir=str(base / "Qwen-Image-Edit-2509"),
    )
    snapshot_download(
        "huawei-bayerlab/marigold-v2-0",
        revision="cdf9810fb690886391a63aec012b5f501064fb0d",
        allow_patterns=["normals/*", "qwen_text_embeddings/*normals*"],
        local_dir=str(base / "Marigold-V2"),
    )
    print("Normals inference assets downloaded to", base)


if __name__ == "__main__":
    main()
