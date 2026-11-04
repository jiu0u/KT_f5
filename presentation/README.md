# 발표 슬라이드

1920×1080 고정 화면을 브라우저 창 크기에 맞춰 비율 그대로 줄여 보여 줍니다.

## 여는 법

장 파일을 `fetch` 로 불러오기 때문에 `index.html` 을 더블클릭(file://)하면 열리지 않습니다. 아래 둘 중 하나로 여세요.

**내 컴퓨터에서**

```bash
cd presentation
python -m http.server 8000
```

브라우저에서 http://localhost:8000 을 엽니다.

**GitHub Pages 로**

저장소 Settings → Pages 에서 브랜치를 고르면 `https://<사용자>.github.io/<저장소>/presentation/` 에서 열립니다.

## 조작

- → ↓ PageDown Space : 다음 장
- ← ↑ PageUp : 이전 장
- 주소 끝 `#3` : 3장부터 보기 (새로고침해도 그 장 유지)

## 구조

- `theme.css` — 색·글꼴·글자 크기. 여기서만 바꿉니다.
- `slides/01.html` … — 한 장에 파일 하나. `.title`(제목)과 `.body`(본문) 자리만 있습니다.
- `index.html` — `SLIDES` 목록 순서대로 장을 불러옵니다. 장을 추가하면 파일을 만들고 이 목록에 이름을 넣으세요.
