"""Resident adapter around the pinned official Marigold V2 graph.

The checkpoint and graph are loaded once. No image files or subprocesses are
created per frame. The upstream repository must be installed with pip -e.
"""

import importlib
import logging
from pathlib import Path

import numpy as np


class MarigoldBackend:
    def __init__(self, repo, assets):
        self.repo = Path(repo).resolve()
        self.assets = Path(assets).resolve()
        self.graph = None
        self.load_error = None
        self.metrics = {}

    def load(self):
        import torch
        from accelerate import Accelerator
        from marigoldv2.core.builder import build_transforms
        from marigoldv2.core.registry import REGISTRY
        from marigoldv2.network.change_network_mode import set_to_eval
        from marigoldv2.script.train.util import make_load_trainables_hook
        from omegaconf import OmegaConf
        from safetensors import safe_open

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable. Use the configured CUDA Python environment.")
        torch.cuda.reset_peak_memory_stats()
        logging.info("Loading Marigold V2 normals on %s", torch.cuda.get_device_name())
        package = importlib.import_module("marigoldv2.util.config_resolvers")
        installed_root = Path(package.__file__).resolve().parents[2]
        if installed_root != self.repo:
            raise RuntimeError(
                f"Installed Marigold package is {installed_root}, expected {self.repo}"
            )
        checkpoint = self.assets / "checkpoints/Marigold-V2/normals"
        qwen = self.assets / "checkpoints/Qwen-Image-Edit-2509"
        embeddings = self.assets / "checkpoints/Marigold-V2/qwen_text_embeddings"
        prefix = "qwen_edit_2509_qwen_normals_dummy512"
        required = [
            checkpoint / "trainables.safetensors",
            qwen / "transformer/config.json",
            qwen / "vae/config.json",
            embeddings / f"{prefix}_prompt_embeds.pt",
            embeddings / f"{prefix}_prompt_mask.pt",
        ]
        for path in required:
            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing model asset: {path}; run tools/download_normals.py"
                )
        with safe_open(str(required[0]), framework="pt", device="cpu") as weights:
            keys = list(weights.keys())
            if not all(any(k.startswith(name + ".") for k in keys) for name in ("VAE", "Diffuser")):
                raise ValueError("Normals checkpoint must contain both VAE and Diffuser trainables")

        cfg = OmegaConf.load(self.repo / "evaluation/config/inference_depth.yaml")
        cfg.pop("base_config", None)
        cfg.paths = {"ckpt_qwen_image_edit": str(qwen), "embed_dir": str(embeddings)}
        cfg.device = "cuda:0"
        accelerator = Accelerator(mixed_precision="bf16")
        REGISTRY["cfg"] = cfg
        REGISTRY["accelerator"] = accelerator
        for name in (
            "marigoldv2.experiments.20260316_qwen_depth.component_loader",
            "marigoldv2.experiments.20260316_qwen_depth.network_graph",
            "marigoldv2.validation.folder_steps",
        ):
            importlib.import_module(name)
        cfg.network_graph.pop("SelectChannel", None)
        cfg.network_graph.QwenImageEdit2509Step.kwargs.prefix = prefix
        cfg.network_graph.FolderNormalizeSurfaceNormals = {
            "kwargs": {"input_key": "out/pixel_pred", "output_key": "out/normal_pred"}
        }
        build_transforms(cfg.network_components, "network_components")({})
        graph = build_transforms(cfg.network_graph, "network_graph")
        REGISTRY["built_network_graphs"] = {"train": graph}
        make_load_trainables_hook(REGISTRY, accelerator, exclude_components=[])([], str(checkpoint))
        for model in REGISTRY["network_components"].values():
            if isinstance(model, torch.nn.Module):
                model.requires_grad_(False)
        set_to_eval()
        self.graph = graph
        self.torch = torch
        torch.cuda.empty_cache()
        logging.info("Normals model loaded and resident")

    def predict(self, rgb, size, seed):
        import cv2

        if self.graph is None:
            if self.load_error:
                raise RuntimeError(
                    "Previous model load failed. Restart the engine: " + self.load_error
                )
            try:
                self.load()
            except Exception as exc:
                self.load_error = str(exc)
                raise
        torch = self.torch
        original_h, original_w = rgb.shape[:2]
        if size != (original_w, original_h):
            rgb = np.clip(cv2.resize(rgb, size, interpolation=cv2.INTER_LANCZOS4), 0, 1)
        image = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1)[None]
        batch = {"rgb_norm": image * 2 - 1, "out": {}}
        # Official VAE samples a latent. Reset per request for stable cache semantics.
        with (
            torch.random.fork_rng(devices=[torch.cuda.current_device()]),
            torch.inference_mode(),
            torch.amp.autocast("cuda", dtype=torch.bfloat16),
        ):
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            self.graph(batch)
            normal = batch["out"]["normal_pred"].float()
            if normal.shape[-2:] != (original_h, original_w):
                normal = torch.nn.functional.interpolate(
                    normal, size=(original_h, original_w), mode="bilinear", align_corners=False
                )
            result = normal[0].cpu().numpy()
            self.metrics = {
                "gpu": torch.cuda.get_device_name(),
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            }
            return result
