# Third-party notices

The OFX frontend, build scripts and mini host derive from
[MoGe-nuke](https://github.com/sumitchatterjee13/MoGe-nuke), revision
`4e9213e4a2a77d623daff5e301e80262e3d9d7fb`. Copyright (c) 2026 Sumit Chatterjee,
MIT. License text: `licenses/MoGe-nuke-MIT.txt`. Modifications implement a
normals-only protocol, seed and resolution, bounded packets, hidden launch and
cache invalidation. The MoGe model and its weights are not included.

OpenFX headers in `ofx/include/openfx` are BSD-3-Clause; their license is
preserved at `ofx/include/openfx/LICENSE.md`.

The runtime imports the official [Marigold V2](https://github.com/huawei-bayerlab/marigold-v2)
implementation, pinned to `18466672fb8661152434a0efe1184939164cda19`.
Its Apache 2.0 license and NOTICE are preserved in `licenses/`.
Marigold and Qwen weights are separate downloads governed by their published licenses.

The church image in `examples/assets/church.jpg` comes from the pinned official
Marigold V2 example assets. Associated derived normal maps are included in the
example download.

The street video and derived normal previews use the first four seconds of
[Airam Dato-on / Pexels 35958383](https://www.pexels.com/video/urban-street-life-with-people-walking-by-historic-building-35958383/),
under the [Pexels License](https://www.pexels.com/license/). The footage was resized
and sampled at 12 fps, then processed with Marigold. Pexels media are not covered
by this repository's MIT code license.

Nuke screenshots show this integration's graph and generated output in the
Foundry Nuke application. This is an independent community project and does not
claim endorsement by Foundry, Huawei, Qwen, or the source authors.
