# 반도체 폐기물 순환경제 매칭 AI — MVP

DSC 공유대학×KT AI 활용 지역문제 해결 캠프 제출용 프로토타입. 전체 스펙은 [CLAUDE.md](CLAUDE.md) 참고.

## 현재 범위 (1~2단계만 구현)

- `src/schema.py` — 3.1단계(정보구조화) 출력 형식인 `WasteRecord`
- `src/match.py` — 3.2단계(AI 후보탐색): CAS No. 완전일치 우선, 없으면 word-overlap 텍스트 유사도로 Top-K 후보 반환
- `data/sample_waste.json` — 로직 검증용 합성 샘플 데이터 (실제 기업 데이터 아님)

3단계(화학·법적 검증), 4단계(경제성·물류), 5단계(TOPSIS)는 아직 구현하지 않음.

## 실제 데이터

### GHG 배출권거래제 대상 사업장 (경제성 검증용 앵커)
- `data/raw/대전_대표사업장_폐기물발생량(GHG배출권대상)_2024.xlsx` — 73개 사업장의 2024년 실측 폐기물 발생량(원본)
- `scripts/load_ghg_waste.py` → `data/ghg_waste_2024.json` (`python -m scripts.load_ghg_waste`)
- 사업장 단위 카테고리별 총량(톤/년)만 있고 CAS No./성분 정보가 없어 물질 단위 매칭에는 바로 못 씀. 4단계(경제성) 검증 및 실측 규모 확인용 앵커 데이터로 사용.
- 확인된 지정폐기물 합계는 73건 전체 기준 약 12,154톤/년으로, CLAUDE.md에 적힌 "약 3,600톤/년"과 다름 — 어떤 부분집합으로 3,600톤이 나온 건지 확인 필요.

### 유성구 사업장폐기물배출자 (1~2단계 매칭용 실데이터)
- `data/raw/대전광역시 유성구_사업장폐기물배출자_20260721.csv` — 130개 사업장(업소명·소재지·배출종류·폐기물 종류)
- `data/raw/화학물질취급정보_20260909.xls` — 물질명 15종 → CAS No. 매핑(취급업체수 통계, 회사명 없음)
- `scripts/load_yuseong_waste.py` → `data/waste_registry_yuseong.json` (`python -m scripts.load_yuseong_waste`)
- **확인된 사실**: 이 130개 사업장의 "폐기물 종류"는 전부 오니·분진·폐합성수지·생활계폐기물 같은 일반 법정 폐기물 분류명이고, 화학물질취급정보의 15종(황산 등 산·알칼리류)과 하나도 겹치지 않음 → **CAS No. 자동 매핑 0/130건**. 즉 이 공개 데이터만으로는 "반도체 폐기물(폐산·폐알칼리·폐유기용제) 순환경제 매칭"이라는 원래 시나리오를 실증하기 어렵고, 회사명·주소·일반폐기물종류 정도만 확보됨. `src/match.py`는 이 경우 CAS No. 경로가 아니라 word-overlap 텍스트 유사도로 동작 (`tests/test_load_yuseong.py`로 확인).
- 화학물질·성분 단위로 실증하려면 개별 기업 MSDS나 화학물질안전원(NCIS) 등 별도 출처가 필요.

### 기업 DB 통합 (대덕구 대기배출업소·제조업공장등록 + 유성구)
- `data/raw/대전광역시 대덕구_대기배출업소현황_20250904.csv` (178개 사업장, 업종명 포함)
- `data/raw/대전광역시 대덕구_제조업공장등록현황_20260623.csv` (1,739개 사업장, 주생산품 포함)
- `scripts/build_company_db.py` → `data/company_db.json` (`python -m scripts.build_company_db`) — 위 두 파일 + 유성구 폐기물배출자(130건)를 회사명 기준(법인 표기 ㈜/(주)/(유) 등만 제거하고 병합, 지점명이 다르면 별개로 취급)으로 합침
- 결과: **1,920개 기업**(중복 제거 후) — PDF 목표(300개 이상)를 크게 상회. 대기배출업소 178건은 그대로, 제조업공장등록 1,739건 중 1,664건, 유성구 130건 중 126건이 남고 나머지는 다른 출처와 중복 병합됨. 2개 이상 출처에 겹치는 기업 48건.
- `scripts/find_chemical_companies.py` → `data/chemical_candidate_companies.json` — 기업 DB의 product/industry 텍스트를 화학물질취급정보(CAS No. 15종)와 대조. **결과: 2건** — 보림산업(가성소다·인산·황산·희염산·PAC 생산, CAS 7664-93-9), (주)동양이앤씨(황산제2철 생산). 이 두 회사는 황산 계열 화학물질을 실제로 생산·취급하는 것으로 확인되어, 인근 사업장의 폐황산 재활용 수요처 후보로 유의미함. 다만 전체 기업 DB 대비로는 여전히 극소수라, 화학물질 기반 매칭을 본격적으로 하려면 더 많은 화학 관련 원천데이터가 필요.

### 아직 안 쓰는 것
- `한국환경산업기술원_... 상세정보_20241231.csv`(전국 4,355건) — `data/ghg_waste_2024.json`이 이 파일의 대전 부분집합(73건)과 일치함을 확인, 별도 보관 안 함
- `전국폐기물배출업체표준데이터.csv`(전국 4,242건) — 대전 언급 1건뿐이라 CLAUDE.md의 기존 결론("대전 커버리지 없음")대로 사용 안 함

## 실행

```bash
pip install -r requirements.txt
python -m scripts.load_ghg_waste
python -m scripts.load_yuseong_waste
python -m scripts.build_company_db
python -m scripts.find_chemical_companies
python -m tests.test_match
python -m tests.test_load_yuseong
python -m tests.test_company_db
```

## 다음에 할 일

- **CAS No./성분까지 있는 진짜 화학 폐기물 데이터**(MSDS, NCIS 등)를 확보해 실질적인 반도체 소부장 매칭 데모 만들기 — 현재 데이터만으론 화학물질 후보가 2건뿐이라 시나리오 실증에 부족
- `data/company_db.json`의 1,920개 기업 중 폐기물 정보가 있는 건 126건(유성구)뿐 — 나머지 1,794개 기업(대덕구)도 폐기물 배출자 현황을 구해서 waste_types를 채우면 매칭 대상이 크게 늘어남
- `src/match.py`의 word-overlap 유사도가 부족해지면 한국어 문장임베딩(`ko-sroberta` 등)으로 교체
- 3단계 룰베이스(폐기물관리법 별표5의3, 위험물안전관리법 별표19) 모듈 추가
- GHG 지정폐기물 합계 불일치(12,154톤 vs 3,600톤) 확인
