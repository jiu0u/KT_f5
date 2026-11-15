# 발표 슬라이드 (1920×1080 HTML)

**8장 한 번에 보기:** [deck.html 열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/deck.html) — ← → 키(또는 스크롤)로 넘기고 F로 전체화면. 발표할 때도 이 파일 하나면 돼요.

아래는 한 장씩 여는 링크예요.

| 장 | 내용 | GitHub Pages | 미리보기 (Pages 켜기 전) |
|---|---|---|---|
| S01 | 표지 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s01.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s01.html) |
| S02 | 문제: 자립도 3.06%, 막힌 길 두 개 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s02.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s02.html) |
| S03 | 공공 옥상과 모르는 것 두 가지 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s03.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s03.html) |
| S04 | 지붕 AI: 항공사진에서 패널 세기 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s04.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s04.html) |
| S05 | 결과 20.6MW → 설치비 247억 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s05.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s05.html) |
| S06 | 재원 결정과 SPC 자금 구조 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s06.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s06.html) |
| S07 | 시민 투자 100만 원 + 시연영상 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s07.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s07.html) |
| S08 | 실행 계획과 확장 | [열기](https://jiu0u.github.io/KT_f5/docs/slides/s08.html) | [열기](https://htmlpreview.github.io/?https://github.com/jiu0u/KT_f5/blob/main/docs/slides/s08.html) |

- **GitHub Pages 링크**는 저장소 주인이 Settings → Pages에서 `main` 브랜치 `/ (root)`로 켜야 열려요.
- **미리보기 링크**는 htmlpreview.github.io(외부 서비스)를 거쳐서 지금 바로 열려요.
- 항공사진(`img/`)은 깃에 올리지 않아서 S4 사진 자리는 비어 보여요. 사진은 단톡방 PNG로 보세요.
- 고칠 때: 장마다 담당을 나누고, 시작 전 `git pull`, 끝나면 바로 커밋·푸시. 공통 디자인 `slide.css`는 한 사람만 고쳐요. 숫자는 루트 `CLAUDE.md` 기준.
- `deck.html`은 `s01~s08.html`을 합친 결과물이에요. 장을 고친 뒤에는 `python -X utf8 docs/slides/build_deck.py`로 다시 만들어서 같이 커밋하세요(deck.html을 직접 고치지 않기).
