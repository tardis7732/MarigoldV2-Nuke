# Marigold V2 영상 예제

- 원본: [Airam Dato-on / Pexels 35958383](https://www.pexels.com/video/urban-street-life-with-people-walking-by-historic-building-35958383/)
- 사용 조건: [Pexels License](https://www.pexels.com/license/)
- 원본 영상의 첫 4초를 12fps, 432×768로 변환한 48프레임입니다. 무음 예제입니다.
- 실제 Nuke OFX로 각 프레임을 계산합니다. 추론 긴 변 512, seed 2025, sRGB 입력.
- 모델은 프레임별 독립 추론입니다. 시간축 안정화나 보간은 적용하지 않았습니다.

## 파일

- `comparison.mp4`: 왼쪽 원본, 오른쪽 Normal 미리보기.
- `normals_preview.mp4`: Normal 미리보기만 재생.
- `Normals_Video.nk`: Viewer 1 저장된 Normal, 2 원본, 3 실시간 재계산.
- `source/source.0001.png`–`0048.png`: 입력 프레임.
- `normals/normals.0001.exr`–`0048.exr`: signed XYZ RGBA, raw 32-bit float EXR.

표시용 Normal은 XYZ × 0.5 + 0.5로 변환합니다. 원래 XYZ 데이터는 EXR에 보존됩니다.
Nuke 예제를 옮길 때는 이 폴더 전체를 함께 옮기세요.
