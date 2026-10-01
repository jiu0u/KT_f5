"""전국신호등표준데이터에서 대전 소재 신호등만 걸러온다
-- 교통사고 위험지점 예측 특징(feature) 데이터 중 하나.

⚠ 처음엔 14페이지만 보고 "대전 데이터가 아예 없다"고 잘못 결론 냈었다 --
지역이 제출 순서대로 쌓이는 구조라 앞쪽만 보면 특정 시도가 통째로 빠진 것처럼
보일 수 있다. 전국 98,899건(기준일 다양) 끝까지(99페이지) 다 뒤지고 나서야
대전이 있다는 걸 확인했다. `signguNm` 요청 파라미터로 "유성구"를 넣으면
NODATA_ERROR가 나는데(build_daejeon_crosswalks.py와 같은 증상), 실제로는
데이터가 있으므로 이 파라미터 자체를 못 믿고 전수 페이지네이션 + 클라이언트
필터로 간다.

실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_traffic_lights
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_traffic_lights.json"
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_traffic_light_api"
NUM_OF_ROWS = 1000
MAX_PAGES = 110  # 전국 98,899건 기준 99페이지, 여유만 둠

FIELDS = [
    "ctprvnNm", "signguNm", "roadKnd", "roadRouteNm", "rdnmadr", "lnmadr",
    "latitude", "longitude", "roadType", "priorRoadYn", "tfclghtSe",
    "fnctngSgngnrYn", "remndrIdctYn", "sondSgngnrYn", "institutionNm",
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
            if item.get("ctprvnNm") != "대전광역시":
                continue
            daejeon.append({f: item.get(f) for f in FIELDS})

    OUT_PATH.write_text(json.dumps(daejeon, ensure_ascii=False, indent=2), encoding="utf-8")
    return daejeon


def main():
    result = build()
    from collections import Counter
    counts = Counter(r["signguNm"] for r in result)
    for d, n in counts.most_common():
        print(f"{d}: {n}개")
    print(f"완료 - 대전 신호등 {len(result)}개 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
