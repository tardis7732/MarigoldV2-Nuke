# Depth comparison

Extract the v0.2.0 Depth comparison release ZIP into the project folder, then open `Depth_Comparison.nk`.

Viewer: **1 source / 2 MoGe-3 / 3 Marigold V2 / 4 live Marigold**. Select Viewer 3 for the saved Marigold result. Saved EXRs need no model; install the current OFX to recognize the live node.

Raw EXRs contain RGB and `depth.Z`. MoGe stores metric depth estimates; Marigold stores relative log-depth, **not metres**. Both display branches use log-depth with separate 2–98 percentile ranges, far=white. This is a qualitative comparison without ground truth.

The live node selects one task with `output`. Write raw data with all channels / float32 / raw. Adjust display ranges for new inputs.

Input: [MoGe-nuke sample](https://github.com/sumitchatterjee13/MoGe-nuke), original MIT attribution retained. [Settings and explanation](../../docs/DEPTH_COMPARISON.md).
