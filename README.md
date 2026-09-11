# 반도체 폐기물 순환경제 매칭 AI — MVP

DSC 공유대학×KT AI 활용 지역문제 해결 캠프 제출용 프로토타입. 전체 스펙은 [CLAUDE.md](CLAUDE.md) 참고.

## 현재 범위 (1~2단계만 구현)

- `src/schema.py` — 3.1단계(정보구조화) 출력 형식인 `WasteRecord`
- `src/match.py` — 3.2단계(AI 후보탐색): CAS No. 완전일치 우선, 없으면 word-overlap 텍스트 유사도로 Top-K 후보 반환
- `data/sample_waste.json` — 로직 검증용 합성 샘플 데이터 (실제 기업 데이터 아님)

3단계(화학·법적 검증), 4단계(경제성·물류), 5단계(TOPSIS)는 아직 구현하지 않음.

## 실제 데이터

- `data/raw/대전_대표사업장_폐기물발생량(GHG배출권대상)_2024.xlsx` — GHG 배출권거래제 대상 73개 사업장의 2024년 실측 폐기물 발생량(원본)
- `scripts/load_ghg_waste.py` → `data/ghg_waste_2024.json`으로 변환 (`python -m scripts.load_ghg_waste`)
- **주의**: 이 데이터는 사업장 단위 폐기물 카테고리별 총량(톤/년)만 있고 CAS No./성분 정보가 없어 `src/match.py`(물질 단위 매칭)에는 바로 못 씀. 4단계(경제성) 검증 및 실측 규모 확인용 앵커 데이터로 사용.
- 변환 후 확인된 지정폐기물 합계는 73건 전체 기준 약 12,154톤/년으로, CLAUDE.md에 적힌 "약 3,600톤/년"과 다름 — 원 작성자가 어떤 부분집합(예: 대표사업장 행만 등)으로 3,600톤을 계산했는지 확인 필요.

## 실행

```bash
pip install -r requirements.txt
python -m scripts.load_ghg_waste
python -m tests.test_match
```

## 다음에 할 일

- **CAS No./성분까지 있는 300개+ 기업 폐기물 DB**(PDF 제안서 언급분)를 확보해 `WasteRecord` 스키마로 변환하는 스크립트 추가 — `data/sample_waste.json`은 그 전까지의 매칭 로직 검증용 합성 자리표시자
- `src/match.py`의 word-overlap 유사도가 실제 비정형 설명 텍스트에서 부족하면 한국어 문장임베딩(`ko-sroberta` 등)으로 교체
- 3단계 룰베이스(폐기물관리법 별표5의3, 위험물안전관리법 별표19) 모듈 추가
- 위 지정폐기물 합계 불일치 확인
