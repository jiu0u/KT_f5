"""대전 5개 구의 상가업소 수를 구별로 집계 -- vacant_house_match.py `상권밀도` 신호용.

⚠ 정직하게 밝히는 한계:
- "밀도"라고 부르지만 실제로는 구별 상가업소 "총 개수"를 정규화한 것이다.
  면적이나 인구로 나눈 진짜 밀도가 아니다 -- 서구가 1위인 것도 실제 상권이
  촘촘해서인지 단순히 인구/면적이 커서인지 이 신호만으로는 구분이 안 된다
  (`전략산업인접도`와 같은 방식의 단순화라 서로 일관성은 있다).
- 구 단위 집계다(동 단위 아님) -- API 자체는 행정동코드(divId=adongCd)로 동
  단위 조회도 되지만, 빈집 후보의 정확한 행정동코드를 아직 안 붙여서 구 단위로
  근사했다(인구 신호와 동일한 한계).

환경변수 DATA_GO_KR_SERVICE_KEY 필요.
실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_commercial_density
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_commercial_density.json"

# 행정표준코드(대전 5개 구, 5자리 시군구코드) -- build_daejeon_population_signals.py와 동일 코드 체계
DISTRICT_CODES = {
    "동구": "30110", "중구": "30140", "서구": "30170",
    "유성구": "30200", "대덕구": "30230",
}


def _store_count(service_key: str, sigungu_code: str) -> int:
    params = {
        "ServiceKey": service_key, "divId": "signguCd", "key": sigungu_code,
        "type": "json", "numOfRows": "1", "pageNo": "1",
    }
    url = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        body = res.read()
    # 이 API는 정상 응답도 XML 파서로 못 읽는 헤더 순서를 쓸 때가 있어 JSON으로만 파싱
    data = json.loads(body)
    return int(data["body"]["totalCount"])


def build() -> list[dict]:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    counts = {d: _store_count(service_key, code) for d, code in DISTRICT_CODES.items()}
    result = [{"district": d, "store_count": n} for d, n in counts.items()]
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    for r in sorted(result, key=lambda r: -r["store_count"]):
        print(f"{r['district']}: 상가업소 {r['store_count']:,}개")
    print(f"완료 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
