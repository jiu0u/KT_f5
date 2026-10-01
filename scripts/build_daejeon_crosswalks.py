"""전국횡단보도표준데이터에서 대전 소재 횡단보도만 걸러온다
-- 교통사고 위험지점 예측의 특징(feature) 데이터 중 하나.

⚠ 한계:
- `signguNm` 요청 파라미터로 "유성구"를 넣어도 NODATA_ERROR가 났다(이유 미확인 --
  값 포맷이 문서와 다르거나 파라미터가 실제로는 안 먹는 것으로 보임). 그래서
  신뢰할 수 있는 `ctprvnNm`(시도명) 없이는 지역 필터가 안 먹는다고 보고, 전국
  58,839건(2025-11-28 기준)을 numOfRows=1000으로 59페이지 전부 받은 뒤
  "대전광역시"로 클라이언트에서 걸러낸다.
- 처음에 전국신호등표준데이터를 14페이지만 보고 "대전 데이터가 없다"고
  잘못 결론 냈었다 -- 지역이 제출 순서대로 쌓이는 구조라 앞쪽 페이지만 보면
  특정 시도가 통째로 빠진 것처럼 보일 수 있다. 99페이지(전국) 끝까지 다
  뒤지고 나서야 대전이 있다는 걸 확인했다 -- **부분 샘플로 "없다"고 단정하면
  안 된다는 걸 직접 겪은 사례.**

실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_crosswalks
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_crosswalks.json"
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_crosswalk_api"
NUM_OF_ROWS = 1000
MAX_PAGES = 70  # 전국 58,839건(2025-11-28 기준) 기준 59페이지, 여유만 둠

FIELDS = [
    "ctprvnNm", "signguNm", "roadNm", "rdnmadr", "lnmadr", "crslkManageNo",
    "crslkKnd", "bcyclCrslkCmbnatYn", "highlandYn", "latitude", "longitude",
    "cartrkCo", "tfclghtYn", "fnctngSgngnrYn", "sondSgngnrYn", "tfcilndYn",
    "ftpthLowerYn", "brllBlckYn",
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
    print(f"완료 - 대전 횡단보도 {len(result)}개 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
