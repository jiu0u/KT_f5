"""국가기술은행(NTB, 한국산업기술진흥원) Open API에서 대전 소재로 추정되는
이전 가능 기술을 뽑아낸다 -- "기술사업화 매칭"(대덕특구 출연연 기술 <-> 지역기업) 피벗의
데이터 소스 후보.

API의 orgName(기관명) 검색 파라미터는 못 믿을 값이다(실제로 "한국기계연구원" 같은
정확한 기관명으로 검색해도 0건이 나오는데, 검색 없이 최근 데이터를 뽑아보면 그 안에
"한국기계연구원"이 orgName 값으로 버젓이 들어있다 -- 필터링이 응답 필드를 제대로
못 걸러주는 버그성 동작). 기관명/지역 필드(mngtrsInsttNm, areaSeNm 등)도 대부분 비어있다.
유일하게 신뢰할 수 있는 건 devPhone(담당자 전화번호)이며, 여기엔 실제 042(대전) 지역번호가
들어있는 걸 샘플로 확인했다. 그래서 서버 필터 대신 최근 데이터를 통째로 받아
devPhone이 042로 시작하는 것만 클라이언트에서 걸러낸다.

API 신청: https://www.data.go.kr/data/15158994/openapi.do (개발계정 자동승인, 일 1,000건)
환경변수 NTB_SERVICE_KEY 에 발급받은 인증키(디코딩 전/후 상관없이 원문)를 넣고 실행.

실행: NTB_SERVICE_KEY=... python -m scripts.find_daedeok_tech_transfer
"""
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

import defusedxml.ElementTree as ET

BASE_URL = "https://apis.data.go.kr/B552536/tech_4/techall"
OUT_PATH = Path(__file__).parent.parent / "data" / "daedeok_tech_transfer_candidates.json"
NUM_OF_ROWS = 100
STA_REG_DATE = "20230101"
END_REG_DATE = "20261231"
MAX_CALLS = 550  # ponytail: 일일 무료 호출 1,000건 중 여유 두고 상한
REQUEST_DELAY_SEC = 0.2
DAEJEON_AREA_CODE = "042"

FIELDS = [
    "stechNum", "techName", "orgName", "summary", "appFld", "devPhone",
    "transCond", "transMoney", "transMoneyName", "saleType", "saleTypeName",
    "tcateNamem", "tcateNamep", "regDate",
]


def fetch_page(service_key: str, page_no: int) -> ET.Element:
    params = {
        "serviceKey": service_key,
        "numOfRows": str(NUM_OF_ROWS),
        "pageNo": str(page_no),
        "staRegDate": STA_REG_DATE,
        "endRegDate": END_REG_DATE,
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return ET.fromstring(res.read())


def find_daedeok_tech_transfer(service_key: str) -> list[dict]:
    root = fetch_page(service_key, 1)
    total_count = int(root.findtext(".//totalCount", "0"))
    total_pages = min(-(-total_count // NUM_OF_ROWS), MAX_CALLS)
    print(f"조회 대상 {total_count}건, {total_pages}페이지 순회 (상한 {MAX_CALLS})")

    matches = []
    skipped_pages = []
    for page_no in range(1, total_pages + 1):
        try:
            page_root = fetch_page(service_key, page_no) if page_no > 1 else root
        except ET.ParseError:
            # ponytail: 정부 API가 이따금 통제문자 섞인 깨진 XML을 주는 페이지가 있음, 그 페이지만 건너뜀
            skipped_pages.append(page_no)
            continue
        for item in page_root.findall(".//item"):
            dev_phone = (item.findtext("devPhone") or "").strip()
            if not dev_phone.startswith(DAEJEON_AREA_CODE):
                continue
            matches.append({f: (item.findtext(f) or "").strip() for f in FIELDS})
        if page_no % 50 == 0:
            print(f"  {page_no}/{total_pages} 페이지, 현재 {len(matches)}건 발견")
        time.sleep(REQUEST_DELAY_SEC)

    if skipped_pages:
        print(f"경고: 깨진 XML로 건너뛴 페이지 {len(skipped_pages)}개 {skipped_pages[:10]}{'...' if len(skipped_pages) > 10 else ''}")

    return matches


def build() -> list[dict]:
    service_key = os.environ["NTB_SERVICE_KEY"]
    result = find_daedeok_tech_transfer(service_key)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    print(f"완료 - 대전(042) 추정 이전가능기술 {len(result)}건 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
