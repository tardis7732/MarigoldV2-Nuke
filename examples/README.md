# Nuke examples

Install the OFX, then download `MarigoldV2-Nuke-examples.zip` from
[Releases](https://github.com/tardis7732/MarigoldV2-Nuke/releases/latest) and extract it into the project folder.

- `Normals_Still.nk`: church image, saved normal EXR and live inference branch.
- `video_demo/Normals_Video.nk`: 48 frames at 12 fps with rendered normal EXRs.
- Viewer **1 = saved normal preview / 2 = source / 3 = live inference**.
- `LIVE_PREVIEW` maps signed XYZ to display RGB with `N * 0.5 + 0.5`.
- `WRITE_LIVE_NORMALS` exports the signed values directly as raw float32 EXR.

The scripts use relative image paths and installer-generated OFX defaults.
Move the entire examples directory together. The saved branches do not need
model loading; live inference needs the CUDA setup.

Source Reads preserve encoded sRGB values with `raw`. Convert other working
spaces upstream. Output EXRs also use `raw` to preserve vector data.

교회 예제는 `Normals_Still.nk`, 영상 예제는 `video_demo/Normals_Video.nk`를 여세요.
Release의 예제 ZIP에는 필요한 이미지와 EXR이 포함되어 있습니다.
Viewer 1은 저장된 결과, 2는 원본, 3은 새 계산입니다.

Church sample: [official Marigold assets](https://github.com/huawei-bayerlab/marigold-v2/tree/18466672fb8661152434a0efe1184939164cda19/assets/examples).
Video attribution and usage conditions: [video_demo/README.md](video_demo/README.md).
See [third-party notices](../THIRD_PARTY_NOTICES.md).
