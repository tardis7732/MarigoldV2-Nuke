"""Shared resident Qwen backbone with Marigold normals and log-depth trainables.

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
        self.active_task = None
        self.task_states = {}
        self.task_graphs = {}

    def load(self, task="normals"):
        import torch
        from accelerate import Accelerator
        from marigoldv2.core.builder import build_transforms
        from marigoldv2.core.registry import REGISTRY
        from marigoldv2.network.change_network_mode import set_to_eval
        from omegaconf import OmegaConf
        from safetensors.torch import load_file

        if task not in ("normals", "depth"):
            raise ValueError("Task must be normals or depth")
        if self.active_task == task:
            return

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable. Use the configured CUDA Python environment.")
        torch.cuda.reset_peak_memory_stats()
        logging.info("Loading Marigold V2 %s on %s", task, torch.cuda.get_device_name())
        package = importlib.import_module("marigoldv2.util.config_resolvers")
        installed_root = Path(package.__file__).resolve().parents[2]
        if installed_root != self.repo:
            raise RuntimeError(
                f"Installed Marigold package is {installed_root}, expected {self.repo}"
            )
        checkpoint = self.assets / "checkpoints/Marigold-V2" / (
            "normals" if task == "normals" else "depth/Log-stage2"
        )
        qwen = self.assets / "checkpoints/Qwen-Image-Edit-2509"
        embeddings = self.assets / "checkpoints/Marigold-V2/qwen_text_embeddings"
        prefix = (
            "qwen_edit_2509_qwen_normals_dummy512" if task == "normals"
            else "qwen_edit_2509_qwen_depth_realimg512"
        )
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
        if task not in self.task_states:
            weights = load_file(str(required[0]), device="cpu")
            if not all(any(k.startswith(name + ".") for k in weights) for name in ("VAE", "Diffuser")):
                raise ValueError("Checkpoint must contain both VAE and Diffuser trainables")
            if self.task_states:
                previous = next(iter(self.task_states.values()))
                if weights.keys() != previous.keys() or any(
                    weights[k].shape != previous[k].shape for k in weights
                ):
                    raise ValueError("Task checkpoints have incompatible trainables; refusing partial swap")
            self.task_states[task] = weights

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
        adapter = "FolderNormalizeSurfaceNormals" if task == "normals" else "FolderDepthPrediction"
        output_key = "normal_pred" if task == "normals" else "depth_pred"
        cfg.network_graph[adapter] = {
            "kwargs": {"input_key": "out/pixel_pred", "output_key": "out/" + output_key}
        }
        if self.graph is None:
            build_transforms(cfg.network_components, "network_components")({})
        if task not in self.task_graphs:
            self.task_graphs[task] = build_transforms(cfg.network_graph, "network_graph")
        graph = self.task_graphs[task]
        REGISTRY["built_network_graphs"] = {"train": graph}
        # One quantized backbone stays on the GPU. CPU-cached task weights replace
        # the complete matching LoRA + VAE decoder set, never a second full model.
        self.active_task = None
        weights = self.task_states[task]
        for name in ("VAE", "Diffuser"):
            state = {k[len(name) + 1:]: v for k, v in weights.items() if k.startswith(name + ".")}
            module = REGISTRY["network_components"][name]
            _, unexpected = module.load_state_dict(state, strict=False)
            if unexpected:
                raise ValueError(f"Unexpected {name} task weights: {unexpected[:5]}")
        for model in REGISTRY["network_components"].values():
            if isinstance(model, torch.nn.Module):
                model.requires_grad_(False)
        set_to_eval()
        self.graph = graph
        self.torch = torch
        self.active_task = task
        self.prediction_key = output_key
        torch.cuda.empty_cache()
        logging.info("%s task ready on the shared resident backbone", task)

    def predict(self, rgb, size, seed, task="normals"):
        import cv2

        if self.active_task != task:
            if self.load_error:
                raise RuntimeError(
                    "Previous model load failed. Restart the engine: " + self.load_error
                )
            try:
                self.load(task)
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
            normal = batch["out"][self.prediction_key].float()
            if normal.shape[-2:] != (original_h, original_w):
                normal = torch.nn.functional.interpolate(
                    normal, size=(original_h, original_w), mode="bilinear", align_corners=False
                )
            result = normal[0].cpu().numpy()
            self.metrics = {
                "gpu": torch.cuda.get_device_name(),
                "active_task": task,
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            }
            return result
