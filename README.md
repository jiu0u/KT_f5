# 반도체 폐기물 순환경제 매칭 AI — MVP

DSC 공유대학×KT AI 활용 지역문제 해결 캠프 제출용 프로토타입. 전체 스펙은 [CLAUDE.md](CLAUDE.md) 참고.

## 현재 범위 (1~2단계만 구현)

- `src/schema.py` — 3.1단계(정보구조화) 출력 형식인 `WasteRecord`
- `src/match.py` — 3.2단계(AI 후보탐색): CAS No. 완전일치 우선, 없으면 word-overlap 텍스트 유사도로 Top-K 후보 반환
- `data/sample_waste.json` — 로직 검증용 합성 샘플 데이터 (실제 기업 데이터 아님)

3단계(화학·법적 검증), 4단계(경제성·물류), 5단계(TOPSIS)는 아직 구현하지 않음.

## 실행

```bash
python -m tests.test_match
```

## 다음에 할 일

- **실제 73개 대전 기업 데이터**를 `data/raw/`에 원본(csv/xlsx)으로 넣고 `WasteRecord` 스키마로 변환하는 스크립트 추가 (`data/sample_waste.json`은 그 전까지의 자리표시자)
- `src/match.py`의 word-overlap 유사도가 실제 비정형 설명 텍스트에서 부족하면 한국어 문장임베딩(`ko-sroberta` 등)으로 교체
- 3단계 룰베이스(폐기물관리법 별표5의3, 위험물안전관리법 별표19) 모듈 추가
