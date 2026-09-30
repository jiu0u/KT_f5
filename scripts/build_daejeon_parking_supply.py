"""전국주차장정보표준데이터에서 대전 소재 주차장만 걸러 구별로 집계
-- vacant_house_match.py `주차장부족도` 신호의 재료(공급량 측면).

⚠ 정직하게 밝히는 한계:
- 이 API엔 지역 필터 파라미터가 아예 없다. 전국 18,883건(2026-04-20 기준)을
  numOfRows=1000으로 페이지네이션해서 전부 받은 뒤 주소 문자열에 "대전"이
  들어간 것만 클라이언트에서 걸러낸다.
- `rdnmadr`(도로명주소)가 비어있는 행이 많아 `lnmadr`(지번주소)도 같이 검사한다.
- "부족도"가 아니라 "공급량"(주차장 수 · 주차구획수 합)만 나온다. 실제 부족
  여부는 수요(유동인구·상권)와 비교해야 하는데 유동인구를 아직 못 붙여서,
  지금은 공급량의 역수(적을수록 부족하다고 가정)로만 근사한다 -- 이것도 상권이
  큰 구가 주차장도 많이 지어놨을 수 있어서 신뢰도가 낮은 근사다.

환경변수 DATA_GO_KR_SERVICE_KEY 필요.
실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_parking_supply
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_parking_supply.json"
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_prkplce_info_api"
NUM_OF_ROWS = 1000
MAX_PAGES = 25  # 전국 18,883건(2026-04-20 기준) 기준 19페이지면 충분, 여유만 둠

DAEJEON_DISTRICTS = ["동구", "중구", "서구", "유성구", "대덕구"]


def _fetch_page(service_key: str, page_no: int) -> dict:
    params = {"serviceKey": service_key, "pageNo": str(page_no), "numOfRows": str(NUM_OF_ROWS), "type": "json"}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read())


def _district_of(address: str) -> str | None:
    for d in DAEJEON_DISTRICTS:
        if "대전" in address and d in address:
            return d
    return None


def build() -> list[dict]:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    first = _fetch_page(service_key, 1)
    total_count = int(first["body"]["totalCount"])
    total_pages = min(-(-total_count // NUM_OF_ROWS), MAX_PAGES)

    counts: dict[str, dict] = {d: {"lot_count": 0, "capacity": 0} for d in DAEJEON_DISTRICTS}
    for page_no in range(1, total_pages + 1):
        body = first["body"] if page_no == 1 else _fetch_page(service_key, page_no)["body"]
        for item in body["items"]["item"]:
            address = (item.get("rdnmadr") or "") + (item.get("lnmadr") or "")
            district = _district_of(address)
            if district is None:
                continue
            counts[district]["lot_count"] += 1
            try:
                counts[district]["capacity"] += int(item.get("prkcmprt") or 0)
            except ValueError:
                pass

    result = [{"district": d, **c} for d, c in counts.items()]
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    for r in sorted(result, key=lambda r: -r["capacity"]):
        print(f"{r['district']}: 주차장 {r['lot_count']}개소, 주차면수 {r['capacity']:,}면")
    print(f"완료 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
