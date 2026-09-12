# 반도체 폐기물 순환경제 매칭 AI — MVP

DSC 공유대학×KT AI 활용 지역문제 해결 캠프 제출용 프로토타입. 전체 스펙은 [CLAUDE.md](CLAUDE.md) 참고.

## 데모 실행

```bash
python -m scripts.demo                    # 기본값: 황산(007664-93-9)
python -m scripts.demo --cas 001310-73-2  # 수산화나트륨 등 다른 물질도 가능
```

`data/matching_candidates_ncis.json`에 있는 물질(19종) 중 하나를 골라 1~5단계를
실제로 이어서 보여준다: 확인된 폐기물 공급 후보 → 화학·법적 검증(현재는 "수동 확인
필요" 표시) → 근접도(같은 구 여부)·사업장 규모(종업원 수) 기준 TOPSIS 순위. 황산
기준 1위 추천은 한솔제지(주) 대전공장(공급처와 같은 대덕구, 종업원 360명).

## 현재 범위

- `src/schema.py` — 3.1단계(정보구조화) 출력 형식인 `WasteRecord`
- `src/match.py` — 3.2단계(AI 후보탐색): CAS No. 완전일치 우선, 없으면 word-overlap 텍스트 유사도로 Top-K 후보 반환
- `scripts/demo.py` — 1~5단계를 실데이터로 잇는 End-to-End 데모 (아래 "데모 실행" 참고)
- `data/sample_waste.json` — 로직 검증용 합성 샘플 데이터 (실제 기업 데이터 아님)

3단계(화학·법적 검증)는 실제 룰 엔진 없이 "검토 필요" 표시만 하고, 4~5단계(경제성·TOPSIS)는
지오코딩 없는 근접도 프록시 + 종업원수 2개 기준짜리 간이 버전이다. 데모 코드의 주석에
한계와 교체 지점을 명시해 뒀다.

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

### 대덕구 사업장폐기물배출자 신고현황 (유성구와 동급의 실데이터, 자동 다운로드)
- `data/raw/대전광역시 대덕구_사업장폐기물배출자 신고현황_20250812.csv` — 공공데이터포털(data.go.kr, 데이터셋 15060392)에서 자동으로 찾아 다운로드함. 988행(사업장×폐기물종류×처리업소 조합)
- `scripts/load_daedeok_waste.py` → `data/waste_registry_daedeok.json` (`python -m scripts.load_daedeok_waste`) — 상호+주소 기준으로 묶어 177개 사업장, 각 사업장의 폐기물 종류 목록 + 실제 처리업소명·처리방법(4단계 참고용) 포함
- 유성구와 마찬가지로 **CAS No. 자동 매핑 0/177건** — 이 데이터도 법정 폐기물 분류명뿐이라 화학물질취급정보 15종과 안 겹침. 두 지자체 데이터셋 모두 같은 한계를 보이는 걸로 봐서, 공공 배출신고 데이터 자체가 물질명이 아니라 법정 분류명 단위로 되어 있다는 구조적 문제로 보임.

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

### 기업 DB 통합 (대덕구 대기배출업소·제조업공장등록·폐기물배출자 + 유성구 + NCIS PRTR)
- `data/raw/대전광역시 대덕구_대기배출업소현황_20250904.csv` (178개 사업장, 업종명 포함)
- `data/raw/대전광역시 대덕구_제조업공장등록현황_20260623.csv` (1,739개 사업장, 주생산품 포함)
- `scripts/build_company_db.py` → `data/company_db.json` (`python -m scripts.build_company_db`) — 위 파일들 + 유성구/대덕구 폐기물배출자 + NCIS PRTR을 회사명 기준(법인 표기 ㈜/(주)/(유) 등만 제거하고 병합, 지점명이 다르면 별개로 취급)으로 합침
- 결과: **2,023개 기업**(중복 제거 후) — PDF 목표(300개 이상)를 크게 상회. 2개 이상 출처에 겹치는 기업 146건. 이 중 52곳은 `chemicals` 필드에 NCIS로 확인된 실제 CAS No.가 채워져 있음.
- `scripts/find_chemical_companies.py` → `data/chemical_candidate_companies.json` — (보조 수단) 기업 DB의 product/industry 텍스트를 화학물질취급정보(15종)와 문자열 대조. 결과 2건(보림산업, (주)동양이앤씨) — NCIS PRTR 쪽이 훨씬 신뢰도 높은 1차 출처이고, 이건 참고용으로만 남겨둠.

### 아직 안 쓰는 것
- `한국환경산업기술원_... 상세정보_20241231.csv`(전국 4,355건) — `data/ghg_waste_2024.json`이 이 파일의 대전 부분집합(73건)과 일치함을 확인, 별도 보관 안 함
- `전국폐기물배출업체표준데이터.csv`(전국 4,242건) — 대전 언급 1건뿐이라 CLAUDE.md의 기존 결론("대전 커버리지 없음")대로 사용 안 함

## 실행

```bash
pip install -r requirements.txt
python -m scripts.load_ghg_waste
python -m scripts.load_yuseong_waste
python -m scripts.load_daedeok_waste
python -m scripts.load_ncis_prtr          # 공공 서버에 순차 요청, 수십 초 소요
python -m scripts.load_ncis_entrps_detail # 공공 서버에 순차 요청, 1분 내외
python -m scripts.build_ncis_waste_registry
python -m scripts.find_matching_candidates
python -m scripts.build_company_db
python -m scripts.find_chemical_companies
python -m tests.test_match
python -m tests.test_load_yuseong
python -m tests.test_load_daedeok
python -m tests.test_load_ncis
python -m tests.test_company_db
python -m tests.test_demo
python -m scripts.demo   # End-to-End 데모 실행
```

## 다음에 할 일

- 데모의 3단계(화학·법적 검증)를 실제 룰 엔진으로 교체 — 지금은 전부 "검토 필요"
- 데모의 4단계 근접도 프록시를 실제 지오코딩(카카오맵/네이버 API) 기반 거리로 교체
- `data/matching_candidates_ncis.json`의 19종 물질(황산·수산화나트륨 등) 후보쌍 중 1~2개를 골라 3단계(화학·법적 검증: 폐기물관리법 별표5의3, 위험물안전관리법 별표19)와 4단계(경제성: 거리·처리단가 비교)까지 실제로 이어붙여 End-to-End 데모 완성하기 — 지금은 후보를 좁히는 데까지만 왔음
- `data/company_db.json`의 2,023개 기업 중 폐기물/화학물질 정보가 있는 건 355건(유성구 126 + 대덕구 177 + NCIS 52)뿐 — 나머지는 업종/생산품만 있음
- `src/match.py`의 word-overlap 유사도가 부족해지면 한국어 문장임베딩(`ko-sroberta` 등)으로 교체
- GHG 지정폐기물 합계 불일치(12,154톤 vs 3,600톤) 확인
