# 반도체 폐기물 순환경제 매칭 AI — MVP

DSC 공유대학×KT AI 활용 지역문제 해결 캠프 제출용 프로토타입. 전체 스펙은 [CLAUDE.md](CLAUDE.md) 참고.

**진행 현황 한 페이지 요약**: [docs/report.html](docs/report.html) — 브라우저로 열면 전체 파이프라인 진행도, 황산 매칭 사례, 19종 물질 요약표, 데이터 출처, 한계를 한 번에 볼 수 있다(`python -m scripts.generate_report`로 만든 `data/full_matching_report.json` 기반, 발표자료 초안으로 바로 써도 됨).

## 데모 실행

```bash
python -m scripts.demo                    # 기본값: 황산(007664-93-9)
python -m scripts.demo --cas 001310-73-2  # 수산화나트륨 등 다른 물질도 가능
```

`data/matching_candidates_ncis.json`에 있는 물질(19종) 중 하나를 골라 1~5단계를
실제로 이어서 보여준다: 확인된 폐기물 공급 후보 → 화학·법적 검증(규칙 3개, 아래
참고) → 근접도(같은 구 여부)·사업장 규모(종업원 수) 기준 TOPSIS 순위. 황산 기준
1위 추천은 한솔제지(주) 대전공장(공급처와 같은 대덕구, 종업원 360명) — 단, 3단계
검증에서는 "미상"이라 법적 적합 여부는 별도 확인이 필요.

## 현재 범위

- `src/schema.py` — 3.1단계(정보구조화) 출력 형식인 `WasteRecord`
- `src/match.py` — 3.2단계(AI 후보탐색): CAS No. 완전일치 우선, 없으면 word-overlap 텍스트 유사도로 Top-K 후보 반환
- `src/legal_rules.py` — 3단계(화학·법적 검증) 규칙 딱 3개만 인코딩 (아래 "3단계 법적 규칙" 참고)
- `scripts/demo.py` — 1~5단계를 실데이터로 잇는 End-to-End 데모 (아래 "데모 실행" 참고)
- `data/sample_waste.json` — 로직 검증용 합성 샘플 데이터 (실제 기업 데이터 아님)

4~5단계(경제성·TOPSIS)는 지오코딩 없는 근접도 프록시 + 종업원수 2개 기준짜리 간이
버전이다. 데모 코드의 주석에 한계와 교체 지점을 명시해 뒀다.

### 3단계 법적 규칙 (`src/legal_rules.py`) — 딱 3개만, 확인된 범위 안에서

전체 별표를 구현한 게 아니라 검증 가능한 조각 3개만 인코딩했다. 여기 안 걸리면
"적법"이 아니라 "미상"이다 — 없는 근거로 통과/불합격시키지 않는다.

1. **폐기물관리법 시행규칙 [별표5의3] R-4-9** (폐산·폐알칼리를 수처리제로 재활용): 대상 물질이 폐산·폐알칼리(황산·질산·수산화나트륨·수산화칼륨 4종만 등재)이고 받는 쪽 업종에 "하수/폐수/분뇨/폐기물" 키워드가 있으면 "가능성있음". 세부 배출허용기준 충족 여부는 코드로 못 봄.
2. **폐기물관리법 시행규칙 [별표5의3] R-4-6** (폐유기용제→재생유기용제, 폐이소프로필알콜→정제 아이소프로필알콜): 중금속(납·비소·수은·카드뮴·크롬 각 1.0mg/L 이하)·증발찌꺼기(0.1중량% 이하) 기준, 이소프로필알콜은 순도(70중량% 이상)·수분(10중량% 이하)도 추가. **실측 성분분석 데이터가 있어야 판단 가능** — 우리 PRTR 데이터엔 배출량만 있고 성분분석값이 없어서, 이 함수는 시험성적서 값을 안 넘기면 항상 "미상"을 반환한다. 즉 지금 데모에서는 이 규칙이 실제로 통과/불합격을 가려주진 못하고, 어떤 값이 필요한지만 보여준다.
3. **위험물안전관리법 시행규칙 [별표19] 혼재기준**(6x6): 위험물 유별을 확실히 아는 8개 물질만 판단. **황산·수산화나트륨은 국가위험물정보시스템(hazmat.nfa.go.kr, 소방청) 제1~6류 전체 품명 목록을 직접 대조해서 "위험물 자체가 아님"을 확인했다** — 제6류(산화성액체)엔 과염소산·과산화수소·질산·할로겐간화합물만 명시돼 있고 황산은 없으며, 수산화나트륨은 1~6류 어디에도 없다. 그래서 이 둘은 "미상"이 아니라 "미적용"(확인된 미해당)으로 나온다. 그 외 유별 미분류 물질은 여전히 "미상".

`tests/test_legal_rules.py`(12개 케이스)에서 실제 사례(황산 → 대전그린에너지센터/㈜동양환경만 "가능성있음", 나머지는 "미상")와 R-4-6의 합격/불합격/데이터없음 3가지 경로 모두 확인.

## 실제 데이터

### GHG 배출권거래제 대상 사업장 (경제성 검증용 앵커)
- `data/raw/대전_대표사업장_폐기물발생량(GHG배출권대상)_2024.xlsx` — 73개 사업장의 2024년 실측 폐기물 발생량(원본)
- `scripts/load_ghg_waste.py` → `data/ghg_waste_2024.json` (`python -m scripts.load_ghg_waste`)
- 사업장 단위 카테고리별 총량(톤/년)만 있고 CAS No./성분 정보가 없어 물질 단위 매칭에는 바로 못 씀. 4단계(경제성) 검증 및 실측 규모 확인용 앵커 데이터로 사용.
- 확인된 지정폐기물 합계는 73건 전체 기준 약 12,154톤/년으로, CLAUDE.md에 적힌 "약 3,600톤/년"과 다름. **다음 조합을 다 시도해봤지만 3,600톤에 맞는 게 없었다**: 대표사업장 16곳만(224톤), 사업장명에 "대전" 포함(11,689톤), 전략산업 태그 있는 13곳만(2,196톤), PDF에 언급된 4개 기업(ROHM·LG에너지솔루션·SK온·한화에어로스페이스, 지정폐기물 1,301톤/총폐기물 2,854톤), 특성(배출권할당대상업체 등)별 그룹. **3,600톤이 어떻게 나온 숫자인지 이 파일만으로는 재현이 안 됨** — 원 작성자가 다른 자료를 봤거나 단위/시점이 다른 걸로 보임. 팀 내부 확인 필요.

### 유성구 사업장폐기물배출자 (1~2단계 매칭용 실데이터)
- `data/raw/대전광역시 유성구_사업장폐기물배출자_20260721.csv` — 130개 사업장(업소명·소재지·배출종류·폐기물 종류)
- `data/raw/화학물질취급정보_20260909.xls` — 물질명 15종 → CAS No. 매핑(취급업체수 통계, 회사명 없음)
- `scripts/load_yuseong_waste.py` → `data/waste_registry_yuseong.json` (`python -m scripts.load_yuseong_waste`)
- **확인된 사실**: 이 130개 사업장의 "폐기물 종류"는 전부 오니·분진·폐합성수지·생활계폐기물 같은 일반 법정 폐기물 분류명이고, 화학물질취급정보의 15종(황산 등 산·알칼리류)과 하나도 겹치지 않음 → **CAS No. 자동 매핑 0/130건**. 즉 이 공개 데이터만으로는 "반도체 폐기물(폐산·폐알칼리·폐유기용제) 순환경제 매칭"이라는 원래 시나리오를 실증하기 어렵고, 회사명·주소·일반폐기물종류 정도만 확보됨. `src/match.py`는 이 경우 CAS No. 경로가 아니라 word-overlap 텍스트 유사도로 동작 (`tests/test_load_yuseong.py`로 확인).
- 화학물질·성분 단위로 실증하려면 개별 기업 MSDS나 화학물질안전원(NCIS) 등 별도 출처가 필요.

### 대덕구 사업장폐기물배출자 신고현황 (유성구와 동급의 실데이터, 자동 다운로드)
- `data/raw/대전광역시 대덕구_사업장폐기물배출자 신고현황_20250812.csv` — 공공데이터포털(data.go.kr, 데이터셋 15060392)에서 자동으로 찾아 다운로드함. 988행(사업장×폐기물종류×처리업소 조합)
- `scripts/load_daedeok_waste.py` → `data/waste_registry_daedeok.json` (`python -m scripts.load_daedeok_waste`) — 상호+주소 기준으로 묶어 177개 사업장, 각 사업장의 폐기물 종류 목록 + 실제 처리업소명·처리방법(4단계 참고용) 포함
- 유성구와 마찬가지로 **CAS No. 자동 매핑 0/177건** — 이 데이터도 법정 폐기물 분류명뿐이라 화학물질취급정보 15종과 안 겹침. 두 지자체 데이터셋 모두 같은 한계를 보이는 걸로 봐서, 공공 배출신고 데이터 자체가 물질명이 아니라 법정 분류명 단위로 되어 있다는 구조적 문제로 보임.

### 동구 사업장폐기물배출자 신고현황 (5개 구 중 3번째, 자동 다운로드)
- `data/raw/대전광역시 동구_사업장폐기물배출자 신고현황.csv` — 공공데이터포털(data.go.kr, 데이터셋 15081140)에서 자동으로 찾아 다운로드함. 138행(사업장×폐기물종류)
- `scripts/load_donggu_waste.py` → `data/waste_registry_donggu.json` — 36개 사업장. 유성구·대덕구와 달리 이 데이터는 **행마다 배출량(톤) 숫자가 있어** 사업장별로 실제 톤수를 합산함
- 역시 **CAS No. 자동 매핑 0/36건** — 3개 지자체 데이터셋 전부 같은 한계(법정 분류명뿐)를 보임
- 서구·중구는 "사업장폐기물배출자" 유형 데이터셋 자체가 data.go.kr에 없음(대형폐기물·음식물류 다량배출 등 다른 유형만 있음) — 대전 5개 구 중 유성·대덕·동구 3곳만 이 유형 데이터를 공개하고 있는 것으로 확인됨

### 화학물질안전원(NCIS) PRTR — 진짜 CAS No. 단위 매칭 데이터 ⭐
- 출처: [icis.mcee.go.kr](https://icis.mcee.go.kr) 화학물질 배출·이동량 정보공개시스템(로그인/API 키 불필요, 공개 조회). 지자체 배출신고 데이터와 달리 **법정 분류명이 아니라 실제 CAS No.로 사업장을 조회**할 수 있음
- `scripts/load_ncis_prtr.py` → `data/ncis_prtr_daejeon_2024.json` — 대전 지역 2024년 조사대상 물질 39종과 각 물질을 취급하는 사업장(이름·주소·업종) 전부 조회
- `scripts/load_ncis_entrps_detail.py` → `data/ncis_entrps_detail_daejeon_2024.json` — 사업장별 상세 페이지까지 들어가 물질별 **대기/수계/토양배출량, 폐수이동량, 폐기물이동량(kg/년)**을 추가로 확보 (52개 사업장 × 132개 물질취급 레코드)
- `scripts/build_ncis_waste_registry.py` → `data/waste_registry_ncis.json` — WasteRecord 형식으로 변환, `amount_ton_per_year`에 실제 폐기물이동량(톤/년)을 채움
- **결과: 진짜 CAS No. 매칭 + 배출 방향 구분까지 나옴.** 132개 (물질,사업장) 레코드 중 **57건은 폐기물이동량 > 0**(실제로 그 물질을 폐기물로 내보낸 증거 있음), 75건은 취급만 확인되고 배출 증거는 없음(생산·원료사용 등으로 추정). `tests/test_load_ncis.py`에서 CAS No. 완전일치(score=1.0) 매칭까지 확인.
- `scripts/find_matching_candidates.py` → `data/matching_candidates_ncis.json` — 물질별로 "확인된 폐기물 공급 후보"(polygon 폐기물이동량>0)와 "기타 취급 후보"(수요 검토 대상)를 나눔. **19종 물질에서 매칭 후보 발견.** 예시:
  - **황산(CAS 7664-93-9)**: 확인된 공급 후보 **한국앤컴퍼니(주) 대전공장 1곳**(폐기물이동량 45.1톤/년) ↔ 기타 취급 후보 7곳((주)선양소주, (주)알루코 제2공장, 대전그린에너지센터, 비비씨, 한솔제지 대전·신탄진공장, 한일제관 대전공장)
  - **수산화나트륨(CAS 1310-73-2)**: 공급 후보 1곳 ↔ 기타 취급 후보 19곳
- **한계 (솔직히)**: 폐기물이동량 0인 "기타 취급 후보"가 실제로 이 물질을 원료로 더 필요로 한다는 뜻은 아니다 — PRTR은 원료 부족량/구매 의향을 조사하지 않는다. 그리고 대상 물질이 배출량조사 지정 39종(대전 기준)뿐이라 모든 화학물질을 다루진 않는다. 즉 이 리스트는 "검토해볼 후보"이지 확정된 매칭이 아니며, 3단계(화학·법적 검증)·4단계(경제성)에서 개별 기업에 직접 확인이 필요하다.

### 기업 DB 통합 (대덕구 대기배출업소·제조업공장등록·폐기물배출자 + 유성구·동구 폐기물배출자 + NCIS PRTR)
- `data/raw/대전광역시 대덕구_대기배출업소현황_20250904.csv` (178개 사업장, 업종명 포함)
- `data/raw/대전광역시 대덕구_제조업공장등록현황_20260623.csv` (1,739개 사업장, 주생산품 포함)
- `scripts/build_company_db.py` → `data/company_db.json` (`python -m scripts.build_company_db`) — 위 파일들 + 유성구/대덕구/동구 폐기물배출자 + NCIS PRTR을 회사명 기준(법인 표기 ㈜/(주)/(유) 등만 제거하고 병합, 지점명이 다르면 별개로 취급)으로 합침
- 결과: **2,059개 기업**(중복 제거 후) — PDF 목표(300개 이상)를 크게 상회. 2개 이상 출처에 겹치는 기업 146건. 이 중 52곳은 `chemicals` 필드에 NCIS로 확인된 실제 CAS No.가 채워져 있음.
- `scripts/find_chemical_companies.py` → `data/chemical_candidate_companies.json` — (보조 수단) 기업 DB의 product/industry 텍스트를 화학물질취급정보(15종)와 문자열 대조. 결과 2건(보림산업, (주)동양이앤씨) — NCIS PRTR 쪽이 훨씬 신뢰도 높은 1차 출처이고, 이건 참고용으로만 남겨둠.
- `scripts/find_recycling_companies.py` → `data/recycling_companies_daejeon.json` — `matching_candidates_ncis.json` 안에서 업종이 "폐기물 수집,운반,처리 및 원료재생업"인 기업만 추출. **재활용업체 대상 리드매칭(피벗 방향) 수요자 후보 2곳 확인**: (주)동양환경(대덕구, 6개 물질 취급), 대전그린에너지센터(주)(유성구, 2개 물질 취급). 이 둘은 배출기업이 아니라 이미 폐기물을 처리·재생하는 게 본업인 회사임.
- `scripts/find_semiconductor_companies.py` → `data/semiconductor_companies_daejeon.json` — `company_db.json`에서 업종/주생산품에 "반도체·전자부품·웨이퍼·소자"가 들어간 기업만 추출(43곳). 이 중 NCIS로 실제 화학물질까지 확인된 곳은 4곳(주식회사 켐옵틱스, (주)로옴코리아, (주)래트론, 이엘케이㈜) — 나머지 39곳은 업종상 후보일 뿐 폐기물 데이터는 아직 없음. 대전 반도체 배출기업 컨택 대상 풀을 넓히는 용도.

### 아직 안 쓰는 것
- `한국환경산업기술원_... 상세정보_20241231.csv`(전국 4,355건) — `data/ghg_waste_2024.json`이 이 파일의 대전 부분집합(73건)과 일치함을 확인, 별도 보관 안 함
- `전국폐기물배출업체표준데이터.csv`(전국 4,242건) — 대전 언급 1건뿐이라 CLAUDE.md의 기존 결론("대전 커버리지 없음")대로 사용 안 함

## 실행

```bash
pip install -r requirements.txt
python -m scripts.load_ghg_waste
python -m scripts.load_yuseong_waste
python -m scripts.load_daedeok_waste
python -m scripts.load_donggu_waste
python -m scripts.load_ncis_prtr          # 공공 서버에 순차 요청, 수십 초 소요
python -m scripts.load_ncis_entrps_detail # 공공 서버에 순차 요청, 1분 내외
python -m scripts.build_ncis_waste_registry
python -m scripts.find_matching_candidates
python -m scripts.find_recycling_companies
python -m scripts.build_company_db
python -m scripts.find_semiconductor_companies
python -m scripts.find_chemical_companies
python -m scripts.generate_report   # data/full_matching_report.json -> docs/report.html가 참조
python -m tests.test_match
python -m tests.test_load_yuseong
python -m tests.test_load_daedeok
python -m tests.test_load_donggu
python -m tests.test_load_ncis
python -m tests.test_company_db
python -m tests.test_demo
python -m tests.test_legal_rules
python -m tests.test_generate_report
python -m tests.test_find_recycling_companies
python -m tests.test_find_semiconductor_companies
python -m scripts.demo   # End-to-End 데모 실행
```

## 다음에 할 일

- `src/legal_rules.py`의 R-4-6(재생유기용제)은 실측 성분분석값(중금속·증발찌꺼기 등)이 있어야 실제로 통과/불합격을 가릴 수 있음 — 기업이 시험성적서를 입력하는 경로 필요
- R-4-9 외 다른 재활용 유형(금속회수·중화제 등) 추가 — 황산·수산화나트륨의 위험물 해당 여부는 확인 완료(둘 다 위험물 아님)
- 데모의 4단계 근접도 프록시를 실제 지오코딩(카카오맵/네이버 API) 기반 거리로 교체
- `data/company_db.json`의 2,059개 기업 중 폐기물/화학물질 정보가 있는 건 391건(유성구 126 + 대덕구 177 + 동구 36 + NCIS 52)뿐 — 나머지는 업종/생산품만 있음. 서구·중구는 이 유형 데이터 자체가 공개돼 있지 않음
- `src/match.py`의 word-overlap 유사도가 부족해지면 한국어 문장임베딩(`ko-sroberta` 등)으로 교체
- GHG 지정폐기물 합계 불일치(12,154톤 vs 3,600톤) — 여러 부분집합 다 확인해봤지만 재현 안 됨(위 "GHG" 섹션 참고), 원 작성자에게 직접 확인 필요
