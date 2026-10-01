"""전국교통사고다발지역표준데이터에서 대전 소재 사고다발지역만 걸러온다
-- "저밀도 지역 특화" 교통사고 위험지점 예측의 라벨(정답) 데이터.

⚠ 정직하게 밝히는 한계:
- 이 API에도 깔끔한 지역 필터가 없다. 요청변수 문서엔 CTPRVN_SIGNGU_NM이
  있지만, 응답 필드는 실제로 "대전광역시 동구1", "대전광역시 동구2"처럼
  구 이름 뒤에 일련번호가 붙어있어(연도별 순위로 추정) 정확히 일치시키는
  파라미터값을 알아내기 어려웠다. 그래서 전국 12,780건을 numOfRows=1000으로
  13페이지 전부 받은 뒤 "대전" 문자열로 클라이언트에서 걸러낸다.
- "사고다발지역"은 이미 "3년간 반경 150m 내 사고 3건 이상" 같은 기준으로
  도로교통공단이 미리 뽑아놓은 지점이다 -- 즉 이 데이터 자체가 이미 "다발지역
  목록"이라, 우리가 하려는 "아직 안 걸린 위험지점 예측"의 재료(정답 있는 표본)로는
  맞지만, 그 자체가 최종 결과물이 되면 안 된다(이미 있는 걸 또 만드는 셈).

실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_accident_hotspots
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_accident_hotspots.json"
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_acdnt_area_api"
NUM_OF_ROWS = 1000
MAX_PAGES = 20  # 전국 12,780건(2025-09-24 기준) 기준 13페이지면 충분, 여유만 둠

FIELDS = [
    "acdntAreaManageNo", "acdntYear", "acdntTypeSe", "ctprvnSignguNm",
    "acdntAreaLcNm", "occrrncCo", "casltCo", "deathCo", "swpsnCo",
    "sinjpsnCo", "injpsnCo", "latitude", "longitude",
]


def _fetch_page(service_key: str, page_no: int) -> dict:
    params = {"serviceKey": service_key, "pageNo": str(page_no), "numOfRows": str(NUM_OF_ROWS), "type": "json"}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read())


def build() -> list[dict]:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    first = _fetch_page(service_key, 1)
    total_count = int(first["body"]["totalCount"])
    total_pages = min(-(-total_count // NUM_OF_ROWS), MAX_PAGES)

    daejeon = []
    for page_no in range(1, total_pages + 1):
        body = first["body"] if page_no == 1 else _fetch_page(service_key, page_no)["body"]
        for item in body["items"]["item"]:
            if "대전" not in item.get("ctprvnSignguNm", ""):
                continue
            row = {f: item.get(f) for f in FIELDS}
            # "대전광역시 동구1" -> district="동구" (뒤에 붙은 순위 일련번호 제거)
            name = row["ctprvnSignguNm"]
            for d in ["동구", "중구", "서구", "유성구", "대덕구"]:
                if d in name:
                    row["district"] = d
                    break
            daejeon.append(row)

    OUT_PATH.write_text(json.dumps(daejeon, ensure_ascii=False, indent=2), encoding="utf-8")
    return daejeon


def main():
    result = build()
    from collections import Counter
    counts = Counter(r["district"] for r in result)
    for d, n in counts.most_common():
        print(f"{d}: {n}건")
    print(f"완료 - 대전 사고다발지역 {len(result)}건 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
