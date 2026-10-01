"""전국보안등정보표준데이터에서 대전 소재 보안등(가로등)만 걸러온다
-- 처음 구상했던 6개 신호(신호등·도로폭·조명·시간대·인구밀도·대중교통접근성) 중
"조명"에 해당하는 전국 표준데이터를 못 찾았다고 결론 냈었는데, 실제로는 존재
했다(`tn_pubr_public_scrty_lmp_api`) -- 안 찾아본 것과 없는 것을 착각했었다.

이 API엔 ctprvnNm/signguNm 필드가 아예 없다(build_daejeon_road_signs.py와
같은 증상) -- institutionNm(관리기관명, 예: "대전광역시 동구 OOO과")과
주소(rdnmadr/lnmadr)에서 "대전"+구이름 문자열로만 걸러낼 수 있다.

전국 총량이 약 186만 건(1,858페이지, numOfRows 최대 1000 -- 1000 초과는
INVALID_REQUEST_PARAMETER_ERROR)이라 기존 스크립트들보다 한 자릿수 더 크다.
순차 요청으로는 너무 오래 걸려서 ThreadPoolExecutor로 동시에 여러 페이지를
가져온다 -- 기존 "일부만 보고 없다고 결론내리지 말 것" 원칙은 그대로 지키되,
전수 스캔을 현실적인 시간 안에 끝내기 위한 변경이다.

실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_street_lights
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_street_lights.json"
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_scrty_lmp_api"
NUM_OF_ROWS = 1000  # 이 API는 1000 초과 시 INVALID_REQUEST_PARAMETER_ERROR
MAX_PAGES = 2000  # 전국 약 186만건 -> 1858페이지, 여유만 둠
WORKERS = 8  # 16으로 돌렸다가 WinError 10060(연결 타임아웃)으로 중간에 죽었음 -- 동시 연결 수를 줄임
RETRIES = 4

DISTRICTS = ["동구", "중구", "서구", "유성구", "대덕구"]
# 다른 4개 데이터셋과 달리 필드를 latitude/longitude/district/address로만 줄인다 --
# 전국 총량(186만건) 자체가 커서, 원본 필드(설치연도·형태·관리기관명 등)를 다 들고 가면
# 결과 파일이 20MB를 넘어 저장소에 부담이 된다(다른 4개는 전부 10MB 미만).
# 모델이 실제로 쓰는 건 좌표·구뿐이라 손실은 없다.


def _fetch_page(service_key: str, page_no: int) -> list[dict]:
    params = {"serviceKey": service_key, "pageNo": str(page_no), "numOfRows": str(NUM_OF_ROWS), "type": "json"}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    last_err = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                body = json.loads(res.read())["body"]
            return body["items"]["item"] if body and body.get("items") else []
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"페이지 {page_no} 재시도 {RETRIES}회 실패: {last_err}")


def _district_of(item: dict) -> str | None:
    text = (item.get("institutionNm") or "") + (item.get("rdnmadr") or "") + (item.get("lnmadr") or "")
    if "대전" not in text:
        return None
    for d in DISTRICTS:
        if d in text:
            return d
    return None


def build() -> list[dict]:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    params = {"serviceKey": service_key, "pageNo": "1", "numOfRows": str(NUM_OF_ROWS), "type": "json"}
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        first_body = json.loads(res.read())["body"]
    total_count = int(first_body["totalCount"])
    total_pages = min(-(-total_count // NUM_OF_ROWS), MAX_PAGES)

    daejeon = []
    failed_pages = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_fetch_page, service_key, p): p for p in range(1, total_pages + 1)}
        done = 0
        for fut in as_completed(futures):
            page_no = futures[fut]
            try:
                items = fut.result()
            except Exception as e:
                failed_pages.append(page_no)
                print(f"  페이지 {page_no} 실패(건너뜀): {e}")
                continue
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{total_pages} 페이지 처리, 지금까지 대전 {len(daejeon)}건")
            for item in items:
                district = _district_of(item)
                if district is None:
                    continue
                daejeon.append({
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "district": district,
                    "address": item.get("lnmadr") or item.get("rdnmadr"),
                })

    if failed_pages:
        print(f"⚠ {len(failed_pages)}개 페이지 끝까지 실패(전체 {total_pages}페이지 중): {failed_pages[:20]}...")
    OUT_PATH.write_text(json.dumps(daejeon, ensure_ascii=False, indent=2), encoding="utf-8")
    return daejeon


def main():
    result = build()
    from collections import Counter
    counts = Counter(r["district"] for r in result)
    for d, n in counts.most_common():
        print(f"{d}: {n}개")
    print(f"완료 - 대전 보안등 {len(result)}개 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
