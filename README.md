# 대전 공공건물 지붕 태양광 적지분석 AI + 시민펀드

DSC 공유대학×KT AI 활용 지역문제 해결 공모전 프로토타입. 전체 스펙은 [CLAUDE.md](CLAUDE.md).

## 데모 · 발표자료

저장소를 받았으면 **[index.html](index.html)을 더블클릭**해서 열면 아래 세 개를 클릭으로 바로 볼 수 있다.
받지 않았으면 오른쪽 **바로 열기**를 누르면 된다. (GitHub에서 `.html`을 그냥 누르면 소스 코드가 보인다.)

| 내용 | 파일 | 바로 열기 |
|---|---|---|
| 건물 순위·수익·시민펀드 계산 | `docs/solar_demo.html` | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/solar_demo.html) |
| 3D 지도 + 구별 시민 참여 (인터넷 필요) | `docs/solar_map.html` | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/solar_map.html) |
| 발표자료 설계도 — 12장 구성 | `docs/ppt_blueprint.html` | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/ppt_blueprint.html) |

'바로 열기'는 외부 렌더링 서비스(htmlpreview)를 거치므로 몇 초 걸린다. 안 열리면 저장소를 받아 `index.html`로 연다.

## 지붕 AI 실행

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 학습 (AI Hub 71348 적지분석 Validation 폴더, CPU 약 17분)
python -I scripts/roof_seg_train.py "<AI Hub Validation 폴더>" data/raw/aihub_solar 10

# 대전 공공건물 적용 (.env에 VWORLD_KEY 필요)
python -I scripts/roof_seg_daejeon.py data/raw/aihub_solar/roof_seg.pt data/raw/aihub_solar/daejeon

# 점검
python -m tests.test_roof_panel_layout
```

결과: `data/raw/aihub_solar/daejeon/`의 건물별 이미지(원본 / AI / 패널 배치)와 `result.json`.

## 문서

- [docs/panel_params_review.md](docs/panel_params_review.md) — 패널·설치 변수 근거
- [docs/solar_research.md](docs/solar_research.md) — 자료조사
- [docs/info_request.md](docs/info_request.md) — 정보공개청구 문안
