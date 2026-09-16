# Nodes and controls / 노드 설명

```text
INPUT_IMAGE → MARIGOLD_NORMALS ┬→ LIVE_PREVIEW → Viewer 3
                              └→ WRITE_LIVE_NORMALS
     └───────────────────────────────────────→ Viewer 2
SAVED_NORMALS → SAVED_PREVIEW ────────────────→ Viewer 1
```

| Node | Role / 역할 |
|---|---|
| `INPUT_IMAGE` / `INPUT_VIDEO` | Read of the image/sequence. 분석할 입력. |
| `MARIGOLD_NORMALS` | OFX inference through the Python daemon. 실제 AI 계산. |
| `LIVE_PREVIEW` | Expression maps XYZ to display RGB. 표시용 변환. Viewing it evaluates the upstream model. |
| `WRITE_LIVE_NORMALS` | Raw float32 EXR from the OFX. signed XYZ 데이터 저장. |
| `SAVED_NORMALS` | Previously rendered EXR/sequence. 입력을 바꿔도 그대로인 저장된 결과. |
| `SAVED_PREVIEW` | Display mapping for the saved EXR. 저장된 결과의 표시용 변환. |
| `VIEW_NORMALS` / `VIEW_VIDEO` | Viewer 1 saved / 2 source / 3 live. Viewer process `None`. |
| Backdrops | Labels and organization only. 계산에 영향 없음. |

## LIVE_PREVIEW

RGB stores the XYZ direction of the surface normal, in −1…+1. The Expression evaluates `r*0.5+0.5`, `g*0.5+0.5`, `b*0.5+0.5`, and `a`. It maps **−1 → 0, 0 → 0.5, +1 → 1** for viewing; it does not run another model.

법선은 표면이 바라보는 방향입니다. R=X, G=Y, B=Z이며 음수도 있습니다. `LIVE_PREVIEW`는 이 값을 보기 좋은 색으로 바꿉니다. 실제 법선 데이터가 필요하면 변환 전 OFX 출력에 연결하세요.

## OFX controls

The menu creates one **Marigold V2** node with **output = Normals / Depth** and a separate **Setup** tab, following MoGe-nuke's layout. Only the selected task runs. Old standalone OFX examples remain valid and default to Normals.

메뉴에서는 노드 하나를 만들고 `output`에서 **Normals / Depth**를 선택합니다. 동시에 두 모델을 계산하지 않습니다. Depth 모드의 RGB와 `depth.Z`는 같은 원본 상대 log-depth 값입니다. 값이 클수록 멀지만 미터 단위는 아닙니다. Normal 축 반전은 Depth에 적용되지 않습니다.

| Internal node | Role |
|---|---|
| `Source` | Group input |
| `INFERENCE` | Native OFX; runs the selected task and caches the result |
| `DEPTH_CHANNEL` | Copies raw red to `depth.Z` in Depth mode; bypassed for Normals |
| `Output` | Group output |

Save Depth using **EXR / all channels / 32-bit float / raw**. Put a Grade/Expression on a separate viewing branch to map near/far to 0–1. Export from the raw branch. [Depth example and interpretation](DEPTH_COMPARISON.md).

### Controls

| Control | Default | Meaning |
|---|---|---|
| `outputMode` | Normals | Normals: signed XYZ RGB. Depth: raw relative Log-stage2 depth RGB; menu node also supplies `depth.Z`. |
| `resolution` | 512 | Inference long edge; 0 native. Sizes snap to multiples of 16. Output returns to input dimensions. |
| `seed` | 2025 | Random seed reset per inference; does not guarantee temporal stability. |
| `inputColorspace` | sRGB encoded | Encoded sRGB input, or linear RGB with Rec.709 primaries and an sRGB transfer conversion. |
| `flipX/Y/Z` | Off | Negate a normal axis; ignored in Depth mode. |
| `cacheRevision` | 0 | Increment to invalidate cached inference. |
| `pythonExe` | Installer-generated | External Python for the launcher. |
| `daemonScript` | Installer-generated | Project `daemon/launcher.py`. |
| `port` | 47822 | Loopback communication endpoint. |
| `autoStart` | On | Start the daemon if none is listening. |
| `exitWithHost` | On | Tie a newly launched daemon to its Nuke host. |

EXR Write: RGBA, 32-bit float, raw. Normals preserve Marigold camera-space axes, resize bilinearly to source size and renormalize. Alpha is 1. Input is clamped to 0…1; convert/tone-map other image spaces upstream. Temporal smoothing is not implemented.
