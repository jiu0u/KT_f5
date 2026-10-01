"""전국도로안전표지표준데이터에서 대전 소재 표지만 걸러온다
-- 교통사고 위험지점 예측 특징(feature) 데이터, 특히 도로폭(roadBt)이 핵심.

⚠ 한계:
- 이 API 응답엔 시도명 필드 자체가 없다(rdnmadr/lnmadr 주소 문자열뿐). 그래서
  주소에 "대전"이 들어간 것만 클라이언트에서 거른다 -- 다른 지역 "대전동"
  같은 지명과 섞일 가능성이 이론상 있지만 대전광역시 안에 "대전~"으로 시작하는
  동명이 없어 실제로는 안전하다(확인 필요시 구 이름까지 같이 대조할 것).
- roadBt(도로폭) 필드가 비어있는 행이 많다 -- 표지 종류에 따라 도로폭을 안
  적는 경우가 있는 것으로 보임, 실제로 쓸 수 있는 비율은 데이터를 받아봐야 안다.

실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_road_signs
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_road_signs.json"
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_road_safety_mark_api"
NUM_OF_ROWS = 1000
MAX_PAGES = 130  # 전국 113,768건(2026-04-30 기준) 기준 114페이지, 여유만 둠

FIELDS = [
    "roadKnd", "roadRouteNm", "roadBt", "cartrkCo", "rdnmadr", "lnmadr",
    "latitude", "longitude", "sflblSe", "sflblDc", "lmttVe", "institutionNm",
]


def _fetch_page(service_key: str, page_no: int) -> dict:
    params = {"serviceKey": service_key, "pageNo": str(page_no), "numOfRows": str(NUM_OF_ROWS), "type": "json"}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read())


def _district_of(address: str) -> str | None:
    for d in ["동구", "중구", "서구", "유성구", "대덕구"]:
        if "대전" in address and d in address:
            return d
    return None


def build() -> list[dict]:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    first = _fetch_page(service_key, 1)
    total_count = int(first["body"]["totalCount"])
    total_pages = min(-(-total_count // NUM_OF_ROWS), MAX_PAGES)

    daejeon = []
    for page_no in range(1, total_pages + 1):
        body = first["body"] if page_no == 1 else _fetch_page(service_key, page_no)["body"]
        for item in body["items"]["item"]:
            address = (item.get("rdnmadr") or "") + (item.get("lnmadr") or "")
            district = _district_of(address)
            if district is None:
                continue
            row = {f: item.get(f) for f in FIELDS}
            row["district"] = district
            daejeon.append(row)

    OUT_PATH.write_text(json.dumps(daejeon, ensure_ascii=False, indent=2), encoding="utf-8")
    return daejeon


def main():
    result = build()
    from collections import Counter
    counts = Counter(r["district"] for r in result)
    with_width = sum(1 for r in result if (r.get("roadBt") or "").strip())
    for d, n in counts.most_common():
        print(f"{d}: {n}건")
    print(f"도로폭 값 있는 건: {with_width}/{len(result)}")
    print(f"완료 - 대전 도로안전표지 {len(result)}건 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
