# Marigold V2 for Nuke

이미지와 영상 시퀀스의 **표면 법선과 상대 Depth**를 계산하는 Nuke 노드입니다. MoGe-nuke처럼 한 노드의 **output에서 Normals / Depth**를 선택합니다. 선택한 작업만 외부 Python 데몬에서 GPU로 실행합니다.

| Output | 출력 | 활용 |
|---|---|---|
| Normals | RGB에 signed XYZ | 리라이팅, 방향별 마스크 |
| Depth | RGB와 `depth.Z`에 원본 상대 log-depth | 깊이 마스크, 값을 조정한 뎁스 효과 |

Depth 값은 클수록 멀지만 **미터 단위 거리가 아닙니다**. 이미지마다 스케일과 오프셋이 달라질 수 있습니다. 원본 데이터는 그대로 저장하고, 보기 위한 0~1 변환은 별도 브랜치에서 합니다. [Depth 비교·사용법](DEPTH_COMPARISON.md).

![실제 Nuke Depth 화면과 선택한 Marigold 노드의 Properties](media/nuke-depth.png)

[메인 README](../README.md) · [다운로드](https://github.com/tardis7732/MarigoldV2-Nuke/releases/latest) · [노드 설명](NODES.md)

![실제 Nuke 화면](media/nuke-normals.png)

## MoGe-3와 같은 이미지 비교

![원본 / MoGe-3 / Marigold V2](media/model-comparison.png)

참고한 MoGe-nuke README의 케이크 사진 한 장을 H200에서 두 모델로 처리했습니다. 이 예제에서 Marigold는 눈·입과 딸기 표면을 더 또렷하게 표현하고, MoGe는 큰 곡면을 더 매끈하게 표현합니다. 정답 노멀이 없는 단일 이미지의 시각적 비교입니다.

[확대 비교·설정·측정 결과](MODEL_COMPARISON.md) · [Nuke 비교 예제와 EXR 다운로드](https://github.com/tardis7732/MarigoldV2-Nuke/releases/download/v0.1.0/MarigoldV2-Nuke-model-comparison.zip)

## 설치

Windows x64, CUDA GPU, Git, uv, 외부 Python이 필요합니다. RTX 5070 Ti 16GB에서 긴 변 512를 검증했습니다.

```powershell
git clone https://github.com/tardis7732/MarigoldV2-Nuke.git
cd MarigoldV2-Nuke
powershell -ExecutionPolicy Bypass -File tools/setup_windows.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

모델 두 종류의 다운로드는 약 45GB입니다. 소스 빌드에는 Visual Studio C++ Build Tools가 필요합니다. 빌드 대신 Release의 `MarigoldV2-Nuke-Windows-x64.zip`을 프로젝트 폴더에 풀고 `install.ps1 -SkipBuild`를 실행할 수 있습니다.

설치 후 Nuke를 재시작하면 **Nodes → ML → Marigold V2 → Marigold V2** 메뉴가 생깁니다. main 탭에서 output·해상도·seed를, Setup 탭에서 실행 환경을 설정합니다.

기존 사용자는 코드와 바이너리를 업데이트하고 아래 명령으로 Depth 가중치를 추가한 뒤 엔진과 Nuke를 재시작하세요. assets 경로가 다르면 실제 설정에 맞춰 변경합니다.

```powershell
.venv-engine/Scripts/python.exe tools/download_normals.py --assets assets --task depth
```

기존 OFX 노드는 기본 Normals 동작을 유지합니다. `depth.Z` 자동 출력을 사용하려면 메뉴에서 새 노드를 만드세요. Depth는 **EXR / all channels / 32-bit float / raw**로 저장합니다. ZDefocus 같은 거리 기반 효과에는 작업에 맞는 값 변환이 필요합니다.

## 예제

v0.1.0의 `MarigoldV2-Nuke-examples.zip` 또는 v0.2.0의 `MarigoldV2-Nuke-depth-comparison.zip`을 프로젝트 폴더에 풀어 주세요.

- `examples/Normals_Still.nk`: 교회 이미지와 실제 계산된 Normal.
- `examples/video_demo/Normals_Video.nk`: 4초·12fps·48프레임 영상 예제.
- `examples/depth_comparison/Depth_Comparison.nk`: 같은 케이크 이미지의 두 모델 Depth, 원본 EXR, 표시용 변환, 새 통합 노드.
- Viewer **1: 저장된 결과 / 2: 원본 / 3: 실시간 재계산**.
- 저장된 결과는 모델을 로딩하지 않고 볼 수 있습니다. 라이브 노드를 인식하려면 OFX 설치는 필요합니다.

![왼쪽 원본, 오른쪽 Normal](media/video-comparison.gif)

[비교 MP4](media/video-comparison.mp4). 영상 출처: [Airam Dato-on / Pexels](https://www.pexels.com/video/urban-street-life-with-people-walking-by-historic-building-35958383/).

## 사용법

1. `INPUT_IMAGE`에 sRGB JPG/PNG를 연결합니다. ACEScg나 HDR 이미지는 앞에서 적절히 변환합니다.
2. `MARIGOLD_NORMALS`의 긴 변을 512로 두고 Viewer 3으로 확인합니다.
3. 첫 로딩은 약 1분, 이후 프레임은 측정 환경에서 약 9~15초 걸렸습니다.
4. `WRITE_LIVE_NORMALS`에서 raw / 32-bit float EXR을 저장합니다.

`LIVE_PREVIEW`는 표시용 변환입니다. XYZ의 −1~+1 값을 `값 × 0.5 + 0.5`로 0~1 RGB로 바꿉니다. 법선 데이터 저장은 변환 전 OFX 출력에 연결합니다.

영상 48프레임은 실제 Nuke에서 약 **10분 49초**에 계산했습니다. 모든 EXR과 MP4 프레임을 검증했습니다. 프레임별 독립 추론이므로 영상에서 흔들림이 생길 수 있으며, 시간축 안정화는 적용하지 않았습니다. 전체 화면 법선 추정만 수행하고 바닥 선택이나 평면 추정은 포함하지 않습니다.

데몬 오류는 `output/daemon.log`를 확인합니다. 캐시가 남으면 **Clear selected node cache**를 실행하거나 `cacheRevision`을 올리세요. 바이너리 업데이트 후에는 Nuke를 완전히 재시작해야 합니다.

출처와 라이선스: [Third-party notices](../THIRD_PARTY_NOTICES.md).

## 참고 GitHub

**[Sumit Chatterjee / MoGe-nuke](https://github.com/sumitchatterjee13/MoGe-nuke)**: 이번 통합에서 참고한 저장소입니다. OFX 프런트엔드와 미니 호스트의 기반이며, 모델 비교에 사용한 케이크 예제의 출처입니다. 원본 MIT 저작권 고지를 보존했습니다.
