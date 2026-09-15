# One-image normal comparison

Open `Normals_Comparison.nk` in Nuke. The script reads baked float32 EXRs; it does not load either model.

Download `MarigoldV2-Nuke-model-comparison.zip` from the repository's Releases and extract it into the project root. The archive supplies the image and EXRs beside this script.

Viewer inputs:

1. Original `sample.jpg`, read as raw sRGB values.
2. MoGe-3, resolution level 9, refine steps 3, Nuke axes.
3. Marigold V2, native setting: 544 × 800 inference, seed 2025.

Use Viewer A/B inputs to wipe between results. Keep Viewer process `None`. EXR RGB stores signed XYZ; the Expression nodes map it to display RGB with `XYZ * 0.5 + 0.5`. The display nodes make invalid pixels black. The original signed data remains in each Read node.

All results have the original 547 × 800 dimensions. This is a qualitative comparison on one image without ground-truth normals. Both models ran on an NVIDIA H200 through their Python backends; the local Nuke file displays those saved outputs.

Source image: [`docs/sample.jpg` in MoGe-nuke](https://github.com/sumitchatterjee13/MoGe-nuke/blob/4e9213e4a2a77d623daff5e301e80262e3d9d7fb/docs/sample.jpg), the cake example used in its README. Source repository copyright (c) 2026 Sumit Chatterjee, MIT; see the included third-party notices. This repository does not claim authorship of the source image.

See [comparison report](../../docs/MODEL_COMPARISON.md) for settings, measurements and observations.
