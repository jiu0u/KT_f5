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
- `scripts/find_intermediate_treatment_companies.py` → `data/intermediate_treatment_companies_daedeok.json` — `waste_registry_daedeok.json`의 `handlers`/`methods`(수탁업체별 실제 처리방법: 재활용/중간처분/매립)를 이용해 처리방법이 "중간처분"(소각·중화 등)으로 시작하는 수탁업체만 추출(대덕구 66곳). **동양환경 인터뷰로 "재활용업체는 원료가 필요하다"는 가정이 깨진 뒤, 타겟을 중간처분업체로 넓히기 위해 만듦**. `find_recycling_companies.py`가 쓰는 NCIS 업종명("폐기물 수집,운반,처리 및 원료재생업")은 재활용/중간처분/수집운반을 구분 못 하는 단일 KSIC 코드라 못 씀 — 처리방법이 구분된 원본 데이터는 대덕구 정보공개 자료에만 있어 범위가 대덕구로 한정됨(동구/유성구/NCIS 소스는 처리방법 컬럼 자체가 없음). 검증: 결과 1위가 (주)동양환경(32건)으로, 실제 인터뷰에서 확인된 소각전문업체와 일치.

### 기술사업화 매칭 피벗 후보 데이터 (대덕특구 출연연 ↔ 지역기업)

재활용업체 리드매칭의 핵심 가정이 동양환경 인터뷰로 깨진 뒤 검토한 대안 주제. 대전은
정부출연연구기관이 전국에서 가장 밀집한 지역(대덕특구)인데, 이 출연연들이 보유한
이전 가능 기술이 지역 중소기업으로 잘 안 넘어간다는 문제 — 지금까지 만든 매칭 엔진
(공급자/수요자 구조, TOPSIS 랭킹)을 물질이 아니라 기술로 바꿔서 그대로 재사용 가능.

- `scripts/find_daedeok_tech_transfer.py` → `data/daedeok_tech_transfer_candidates.json` — 국가기술은행(NTB, 한국산업기술진흥원) Open API에서 2023~2026년 등록된 이전가능기술 49,553건을 훑어 대전 지역 후보를 추출. **API의 기관명(`orgName`) 검색 파라미터는 못 믿을 값**(정확한 기관명으로 검색해도 0건 — 필터링 버그) 이라 서버 필터를 안 쓰고, 유일하게 실제 값이 들어있는 `devPhone`(담당자 전화번호)이 "042"(대전 지역번호)로 시작하는 것만 클라이언트에서 걸러내는 방식으로 우회.
- 결과: **15,080건** 확인. 기관명 집계 상위: 한국화학연구원(5,045건), 한국전자통신연구원(4,823건), 한국에너지기술연구원(1,130건), 한국항공우주연구원(1,110건), 한국기계연구원(711건), 한국원자력연구원(447건) 등 — **대덕특구 정부출연연 명단과 정확히 일치**해서 devPhone 필터링 방식이 유효함을 확인.
- API 키는 `NTB_SERVICE_KEY` 환경변수로 주입(레포에 커밋 안 함). data.go.kr 개인 계정 발급, 개발계정 자동승인·일 1,000건 무료. 이번 수집에 496페이지(~500회) 호출 사용, 상한(`MAX_CALLS=550`)으로 일일 한도 초과 방지.
- 아직 안 한 것: 기업 쪽 "수요기술" 데이터(NTB `기술은행 수요기술 조회 서비스`, 미확인) 매칭, 15,080건 중 실제로 유효한(만료 안 된) 기술만 골라내는 필터.
- `data/daedeok_tech_transfer_candidates.json`(22MB, 전문 요약문 포함)은 용량 때문에 레포에 안 올림(`.gitignore` 등록) — 다른 큰 원본 공공데이터와 같은 방침, 스크립트로 재생성 가능.

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
python -m scripts.find_intermediate_treatment_companies
NTB_SERVICE_KEY=... python -m scripts.find_daedeok_tech_transfer  # 별도 API 키 필요, ~500회 호출·몇 분 소요
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
python -m tests.test_find_intermediate_treatment_companies
python -m tests.test_find_daedeok_tech_transfer
python -m scripts.build_vacant_house_candidates
python -m tests.test_build_vacant_house_candidates
python -m tests.test_vacant_house_match
python -m scripts.demo   # End-to-End 데모 실행
python -m scripts.demo_vacant_house   # 빈집 활용 추천 데모 실행
```

## 빈집 활용 최적화 피벗 (진행 중) — 추천 로직 뼈대 + 한계점

재활용업체 리드매칭 → 기술사업화 매칭에 이어 검토 중인 세 번째 피벗. 대전 5개 구의
빈집을 행정동·등급까지는 실측/실제 사례로, 개별 건물 속성(면적·층수·노후연수)은
합성으로 채운 뒤(`src/vacant_house.py`, `scripts/build_vacant_house_candidates.py`),
기존 TOPSIS 매칭 구조를 "물질→처리업체 순위"에서 "빈집 하나→활용 용도 순위"로
뒤집어 추천 로직 뼈대를 만들었다(`src/vacant_house_match.py`, `scripts/demo_vacant_house.py`).

```bash
python -m scripts.build_vacant_house_candidates
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_population_signals
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_commercial_density
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_parking_supply
python -m scripts.demo_vacant_house                    # 기본값: 대덕구 읍내동 실제 사례
python -m scripts.demo_vacant_house --house-id donggu-중앙동-1-1
python -m tests.test_build_vacant_house_candidates
python -m tests.test_build_daejeon_population_signals
python -m tests.test_build_daejeon_commercial_density
python -m tests.test_build_daejeon_parking_supply
python -m tests.test_vacant_house_match
```

### 개발자 입장에서 실제로 만들다 찾은 한계점

**신호 9개 중 지금 실 데이터는 6개**: `전략산업인접도`(`semiconductor_companies_daejeon.json` 구별 집계), `1인가구비율`/`청년인구비율`/`고령인구비율`(행안부 주민등록 API 2개), `상권밀도`(소상공인시장진흥공단 상가업소 수), `주차장부족도`(전국주차장정보 표준데이터, 공급량의 역수로 근사). 나머지 3개(유동인구·생활SOC·교통)는 API 소스는 찾아뒀지만(통계청 SGIS 등) 아직 안 붙였다. 신호가 늘면서 5개 용도 중 4개(청년창업공간·고령자커뮤니티시설·전략산업연계공간·공유주차장)가 이제 coverage 50% 이상으로 추천에 나온다 — 문화학습공간만 아직 1인가구비율(20%)뿐이라 막혀있다.

실제로 하나씩 만들면서 찾은 문제들:

1. **같은 기관 API인데도 파라미터 이름이 다름**: 행안부 인구 API 둘 다 "행정동/법정동 코드"를 받는 게 똑같은데 하나는 `admmCd`, 하나는 `stdgCd`다 — 처음엔 동일한 `admmCd`로 두 번째 API를 호출해서 `NO_MANDATORY_REQUEST_PARAMETERS_ERROR`를 계속 받았다. Swagger 문서가 UI 클릭으로는 잘 안 열려서 결국 페이지 HTML을 직접 curl로 받아 파라미터명을 grep으로 확인해야 했다.
2. **API 신청은 기관 단위지 계정 전체가 아니다**: NTB(한국산업기술진흥원) 때는 techall 하나만 신청했는데 같은 기관의 다른 API(기술시장정보)가 같은 키로 바로 됐지만, 행안부·소상공인시장진흥공단·국토교통부 표준데이터는 전부 새로 등록해야 했다(`SERVICE_KEY_IS_NOT_REGISTERED_ERROR`) — "한 번 뚫으면 다 된다"가 아니라 기관마다 다시 확인해야 한다는 뜻.
3. **"청년/고령인구비율"이라는 이름이 사실은 부정확하다**: 실제로 얻은 데이터는 "전체 인구 중 청년/고령 비율"이 아니라 "1인가구 중 청년/고령 1인가구 비율"이다(행안부 API 자체가 1인세대만 연령별로 제공). 다가구·다세대에 거주하는 청년/고령 인구는 이 신호에 전혀 안 잡힌다.
4. **"상권밀도"·"주차장부족도"도 이름과 실제 의미가 다르다**: 상권밀도는 면적/인구로 나눈 진짜 밀도가 아니라 구별 상가업소 총 개수이고, 주차장부족도는 실제 수요 대비 부족량이 아니라 공급량(주차구획수)의 역수일 뿐이다 — 상권이 큰 구가 주차장도 많이 지어놨을 수 있어서 "부족도"라는 이름이 무색해질 수 있다. 이런 이름-실제 불일치가 신호를 늘릴 때마다 반복해서 나왔다(패턴화됨).
5. **전국주차장 API는 지역 필터가 아예 없다**: `divId`/`adongCd` 같은 지역 파라미터가 있는 상가업소 API와 달리, 이 API는 전국 18,883건을 numOfRows=1000으로 19번 페이지네이션해서 전부 받은 뒤 주소 문자열에 "대전"이 들어간 것만 클라이언트에서 걸러야 했다 — API마다 지역 필터 유무가 달라서 매번 확인이 필요했다.
6. **구 단위 집계라 동 단위 차이를 전혀 구분 못 함**: 인구·상권·주차장 신호 전부 구(시군구) 단위로만 집계했다 — 빈집 후보 하나하나의 정확한 법정동코드를 아직 안 붙여서(지금은 동 이름만 있음), 동구 안 16개 행정동은 전부 같은 신호값을 공유한다. 상가업소 API는 `divId=adongCd`로 동 단위 조회도 되니 가장 먼저 풀 수 있는 한계다.
7. **신호가 적을 때 renormalize가 점수를 왜곡하는 걸 실제로 확인하고 코드로 막음**: 신호 1개뿐일 때 그 값이 최댓값이면 무조건 만점이 나와서 서로 다른 용도가 동점 처리되는 걸 데모로 확인했다(대덕구 읍내동, 청년창업공간·전략산업연계공간 둘 다 1.000). `MIN_COVERAGE=0.5` 미만이면 아예 점수를 안 내도록 고쳐서, 신호가 늘어날 때마다 어떤 용도가 문턱을 넘는지 테스트로 추적하고 있다(`tests/test_vacant_house_match.py`) — 예를 들어 공유주차장은 신호 4개일 땐 coverage 35%로 막혀있다가 주차장부족도가 붙으면서 80%로 넘었다.
8. **용도별 가중치(`USE_TYPE_WEIGHTS`)는 도메인 전문가 검증 없이 상식선에서 잡은 추정치**다 — `legal_rules.py`의 "미상" 처리와 같은 취지로 정직하게 표시는 해뒀지만, 실제 도시계획·부동산 전문가 자문 없이는 이 숫자 자체의 타당성을 주장할 수 없다.
9. **빈집 위치·등급 실측치는 각 구 data.go.kr 페이지의 미리보기 표에서 가져온 것**이다 — 동구는 공식 전체 CSV 다운로드 메커니즘을 못 찾아서(다운로드 버튼을 눌러도 무관한 이미지 파일만 받아짐) 원본 파일 전체를 검증하지 못했다. 미리보기에 나온 16개 행정동 값(합계 385건)은 실측이 맞지만, "전체 행 35"라는 메타데이터와 정확히 안 맞아 빠진 행이 있을 가능성은 남아있다.
10. **대전 5개 구 중 3개 구는 실측 census, 1개 구(중구)는 census 자체가 없음, 1개 구(유성구)는 오래된 데이터뿐**: 동구(385건)·서구(310건)·대덕구(464건)는 각 구의 행정동×등급 표를 그대로 옮겨서 1,164건(+실제 사례 5건). 중구는 애초에 이런 census를 공개 안 하고 "빈집정비사업 추진현황"(2016~2023년 연도별 철거·활용실적)만 있어서 부사동 실제 사례 1곳으로만 대표된다. 유성구는 921건 개별기록이 있지만 2021년 1회성 스냅샷이라 등급 정보가 없어 아직 못 넣었다. 대덕구 원본 CSV는 12개 행정동 중 4곳(신탄진동·석봉동·덕암동·목상동)에서 "합계" 컬럼이 등급별 합과 안 맞는 오류가 있어(예: 신탄진동 합계 0인데 1~3등급 합 56) 등급별 컬럼만 신뢰해서 썼다.

## 교통사고 위험지점 예측 피벗 (검토 중) — 대전 저밀도 지역 특화

네 번째로 검토한 피벗. 과거 사고를 지도에 찍는 건 이미 다들 하는 방식이고, 도로교통공단이
TAAS 안에 "위험도로예보시스템"(국내 최초 AI 기반 교통사고 위험 예측시스템)까지 이미
운영 중이라 "AI 예측" 자체도 선례가 있음을 확인했다. 그래서 차별점을 **대전 저밀도
지역 특화**로 좁히기로 함 — 고밀도 지역(사고 표본 충분)에서 배운 "위험 조건↔사고"
관계를 저밀도 지역(표본 부족이라 과거 데이터만 보면 안전해 보이는 착시)에 적용해
아직 안 걸린 위험지점을 찾는 것.

- `scripts/build_daejeon_density_tiers.py` → `data/daejeon_district_density.json` — 대전 5개 구 인구밀도 계산(위키백과 공식 면적 수치 + 이미 있는 인구 데이터 재사용, 새 API 불필요). 결과: **동구가 구 전체로는 밀도 최하위**(1,596명/km²) — 산내동 등 산간지역을 포함해서 원도심인데도 그렇다. 서구가 최고(4,864명/km²).
- 한계: 구 단위 밀도라 동구 안에서도 중앙동(원도심, 실제로는 고밀도일 것)과 산내동(실제 저밀도)이 뭉뚱그려진다 — 동 단위 면적 데이터를 구하면 바로 교체 대상.

### 핵심 데이터 4개 전부 수집 완료

| 데이터 | 스크립트 → 결과 | 건수(대전) |
|---|---|---|
| 전국교통사고다발지역표준데이터(도로교통공단) | `scripts/build_daejeon_accident_hotspots.py` → `data/daejeon_accident_hotspots.json` | 360건 — 서구 104·동구 96·중구 80·유성구 43·대덕구 37 |
| 전국신호등표준데이터 | `scripts/build_daejeon_traffic_lights.py` → `data/daejeon_traffic_lights.json` | 20,149개 — 유성구 최다 |
| 전국횡단보도표준데이터 | `scripts/build_daejeon_crosswalks.py` → `data/daejeon_crosswalks.json` | 9,393개 — 유성구 최다 |
| 전국도로안전표지표준데이터(도로폭) | `scripts/build_daejeon_road_signs.py` → `data/daejeon_road_signs.json` | 7,221건 — ⚠ 도로폭(roadBt) 값이 전부 "0"(플레이스홀더)이라 실질적으로 못 씀, 아래 참고 |

```bash
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_accident_hotspots
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_traffic_lights   # 전국 99페이지, 몇 분 소요
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_crosswalks      # 전국 59페이지
DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_road_signs      # 전국 114페이지, 가장 오래 걸림
python -m scripts.predict_accident_risk_candidates   # 매칭+위험도 추정, 위 4개 결과 파일 필요
python -m tests.test_build_daejeon_accident_hotspots
python -m tests.test_build_daejeon_traffic_lights
python -m tests.test_build_daejeon_crosswalks
python -m tests.test_build_daejeon_road_signs
python -m tests.test_predict_accident_risk_candidates
```

**핵심 실증 — 산내동 사례**: 동구 사고다발지역 96건을 동별로 쪼개보면 전부 가양동·용전동·삼성동 같은 원도심 동에 몰려있고, **빈집이 가장 많았던(44채) 산내동엔 사고다발지역이 0건**이다. "저밀도 지역은 사고가 안 나서 안전한 게 아니라 기록 자체가 없을 뿐"이라는 피벗의 핵심 전제를 실데이터 교차검증으로 확인했다(`tests/test_build_daejeon_accident_hotspots.py`).

### 수집 과정에서 겪은 문제들

1. **부분 페이지네이션으로 "데이터가 없다"고 잘못 결론 낼 뻔함**: 전국신호등표준데이터를 처음 14페이지(14,000건)만 보고 대전이 안 보여서 "대전은 신호등 데이터 미참여"라고 결론 냈었다. 지역이 제출 순서대로 쌓이는 구조라 앞쪽 페이지만 보면 특정 시도가 통째로 안 보일 수 있다 — 전국 99페이지를 끝까지 다 돌고 나서야 대전이 있다는 걸 확인했다. **부분 샘플로 "없다"를 단정하면 안 된다**는 걸 직접 겪었다.
2. **지역 필터 파라미터(`CTPRVN_SIGNGU_NM`, `signguNm`)가 전부 안 먹는다**: 문서에 분명히 있는 요청변수인데 어떤 값을 넣어도 `NODATA_ERROR`만 났다(사고다발지역·신호등·횡단보도 전부 동일 증상). 원인은 못 찾았다 — 응답 필드와 요청 파라미터의 대소문자/네이밍이 다르거나(응답은 camelCase, 문서는 UPPER_SNAKE), 실제 저장값 포맷이 다른 것으로 추정. 결국 4개 API 전부 **전국 데이터를 numOfRows=1000으로 끝까지 받은 뒤 클라이언트에서 "대전"/구 이름으로 필터링**하는 방식으로 우회했다 — 느리지만 확실하다.
3. **사고다발지역 데이터의 "시군구명"에 알 수 없는 일련번호가 붙어있다**: "대전광역시 동구1", "대전광역시 동구2"처럼 구 이름 뒤에 숫자가 붙는다(연도별 순위로 추정, 확인 안 됨) — 그래서 정확한 문자열 일치 대신 "대전"과 구 이름이 둘 다 포함되는지로 느슨하게 매칭했다.
4. **큰 결과 파일 3개(합계 ~17MB)를 그대로 커밋**: NTB 기술이전 데이터(22MB) 때와 달리 이번엔 커밋했다 — 전국 원본이 아니라 이미 대전으로 필터링된 결과물이고 개별 파일이 10MB 미만이라 저장소 부담이 상대적으로 적다고 판단.
5. **"도로폭 값 7221/7221 확보"라고 잘못 보고했었다**: 빈 문자열만 아니면 통과하는 테스트였는데, 실제로 열어보니 대전에서 매칭된 모든 행의 roadBt가 "0"(플레이스홀더)이었다 — 전국 샘플엔 6~15m대 실제 값도 섞여 있으니 대전 쪽 제출 데이터 자체의 품질 문제다. **지표가 수상하게 완벽하면(100%) 측정 방법을 의심해야 한다**는, 이번 세션 다른 프로젝트에서도 겪은 것과 같은 함정.

### 매칭 로직 — 공간 조인 + 간이 위험도 추정

`src/accident_risk.py`(격자 기반 최근접 탐색) + `scripts/predict_accident_risk_candidates.py`로
① 모든 신호등 지점에 사고다발지역까지 거리·150m 내 횡단보도 수·가까운 도로폭을 공간조인하고,
② 고밀도 구(서구·중구)에서 (도로폭구간, 횡단보도수구간) 조합별 실제 사고다발 근접 비율을 집계한 뒤,
③ 저밀도 구(동구·유성구·대덕구)에서 **아직 사고 기록이 없는** 신호등 지점에 그 비율을 적용해 추정 위험도로 정렬한다.

```bash
python -m scripts.predict_accident_risk_candidates
python -m tests.test_predict_accident_risk_candidates
```

- 결과: 저밀도 구 신호등 10,554개 중 사고 기록 없는 지점에 추정 위험률을 매김(상위는 28%, `data/accident_risk_candidates.json`).
- **도로폭이 전부 "0"이라 못 써서, 지금 위험도는 사실상 "횡단보도 밀집도" 한 가지 차원으로만 갈린다** — `width_bucket()`에서 0 이하는 "6m미만(좁음)"이 아니라 "정보없음"으로 고쳐서, 데이터 없는 지점이 "도로가 좁아서 위험"으로 잘못 집계되는 걸 막았다.
- 애초에 구상했던 6개 신호(신호등 유무·도로폭·조명·시간대·인구밀도·대중교통접근성) 중 지금 실제로 쓰는 건 **인구밀도(저밀도 판정)와 횡단보도뿐**이다 — 조명은 전국 표준데이터를 못 찾았고, 시간대는 이 데이터셋에 발생시각 필드가 없고, 대중교통접근성은 아직 안 붙였다.
- 150m 기준은 도로교통공단이 사고다발지역을 묶을 때 쓰는 반경을 그대로 가져온 것뿐 — 신호등-사고 간 실제 인과 반경을 검증한 게 아니다.
- 고밀도 구 표본(서구 104건·중구 80건)도 크지 않아서, 버킷을 더 쪼갤수록(조명·시간대 등을 추가하면) 추정이 더 불안정해질 수 있다.

### 방향 전환 — "예측"에서 "활용"으로

도로교통공단이 이미 전국 단위로 AI 기반 위험도로예보시스템을 운영 중이라는 걸 확인한 뒤,
"우리가 더 잘 예측할 수 있는가"로 경쟁하는 대신 **"그 예측(혹은 우리 예측)을 보행자가
실제로 받아볼 수 있게 만드는 마지막 단계가 비어 있다"**는 쪽으로 방향을 틀었다.
위험도로예보시스템의 출력은 도로관리기관(B2G)용이고, 일반 보행자가 경로를 짤 때 보는
형태(길찾기 앱의 "이 경로는 위험하다" 알림 같은 것)로는 안 내려온다.

`scripts/build_route_demo.py`가 그 "활용 레이어"의 아주 작은 개념증명이다 — 새 예측을
만드는 게 아니라, 이미 만든 `accident_risk_candidates.json`을 보행 경로 위에 얹는다.

```bash
python -m scripts.build_route_demo
python -m tests.test_build_route_demo
```

- 경로: 동구 가양동의 실제 교차로 두 곳(서쪽 끝 ↔ 동쪽 끝, 약 1.7km)을 직선으로 이음.
- 결과: 그 경로 150m 반경 안에 추정위험률 28%(신뢰 가능한 버킷) 후보 **42건** — 기존
  사고다발지역 지도나 일반 길찾기 앱에는 안 뜨는 지점들이다.
- **한계**: 실제 도로를 따라가는 경로가 아니라 두 점을 이은 직선 근사다(`src/accident_risk.py`의
  `point_to_segment_distance_m`/`candidates_along_route`). 카카오모빌리티·네이버 길찾기 같은
  실제 보행 경로 API를 쓰면 직선이 아니라 실제 도로를 따라가는 경로로 바로 교체할 수 있지만,
  이번엔 API 키 등록 없이 개념만 보여주는 쪽을 택했다.
- 이 방향을 그대로 밀면, 다음 단계는 "학부모가 통학로를 입력하면 몇 곳을 지나가는지" 같은
  구체적 사용자 시나리오로 좁히는 것 — 아직 실제 길찾기 API도, 학교 위치 데이터도 안 붙였다.

## 다음에 할 일

- `src/legal_rules.py`의 R-4-6(재생유기용제)은 실측 성분분석값(중금속·증발찌꺼기 등)이 있어야 실제로 통과/불합격을 가릴 수 있음 — 기업이 시험성적서를 입력하는 경로 필요
- R-4-9 외 다른 재활용 유형(금속회수·중화제 등) 추가 — 황산·수산화나트륨의 위험물 해당 여부는 확인 완료(둘 다 위험물 아님)
- 데모의 4단계 근접도 프록시를 실제 지오코딩(카카오맵/네이버 API) 기반 거리로 교체
- `data/company_db.json`의 2,059개 기업 중 폐기물/화학물질 정보가 있는 건 391건(유성구 126 + 대덕구 177 + 동구 36 + NCIS 52)뿐 — 나머지는 업종/생산품만 있음. 서구·중구는 이 유형 데이터 자체가 공개돼 있지 않음
- `src/match.py`의 word-overlap 유사도가 부족해지면 한국어 문장임베딩(`ko-sroberta` 등)으로 교체
- GHG 지정폐기물 합계 불일치(12,154톤 vs 3,600톤) — 여러 부분집합 다 확인해봤지만 재현 안 됨(위 "GHG" 섹션 참고), 원 작성자에게 직접 확인 필요
