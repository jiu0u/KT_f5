"""전국도로안전표지표준데이터에서 대전 소재 표지만 걸러온다
-- 교통사고 위험지점 예측 특징(feature) 데이터, 특히 도로폭(roadBt)이 핵심.

⚠ 한계:
- 이 API 응답엔 시도명 필드 자체가 없다(rdnmadr/lnmadr 주소 문자열뿐). 그래서
  주소에 "대전"이 들어간 것만 클라이언트에서 거른다 -- 다른 지역 "대전동"
  같은 지명과 섞일 가능성이 이론상 있지만 대전광역시 안에 "대전~"으로 시작하는
  동명이 없어 실제로는 안전하다(확인 필요시 구 이름까지 같이 대조할 것).
- **roadBt(도로폭) 필드가 전부 "0"이다 -- 사실상 미확보.** 처음엔 "빈 문자열만
  아니면 됨" 기준으로 "7221/7221 확보"라고 잘못 보고했다. 실제로 열어보니 대전에서
  매칭된 모든 행이 문자열 "0"(의미 없는 플레이스홀더)이었다 -- 전국 샘플에는
  6/8/10/12m 같은 실제 값도 섞여 있으니(일부 지자체는 제대로 제출) 대전 쪽
  제출 데이터 자체의 품질 문제로 보인다. "100% 확보"처럼 지표가 수상하게
  완벽하면 측정 방법 자체를 의심해야 한다는 교훈(tests/test_build_daejeon_road_signs.py 참고).

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
