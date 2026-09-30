"""대전 5개 구의 인구·1인가구 신호를 실데이터로 채운다 -- vacant_house_match.py의
9개 판단기준 중 `1인가구비율`/`청년인구비율`/`고령인구비율`용.

⚠ 정직하게 밝히는 한계:
- `청년인구비율`/`고령인구비율`이라고 이름 붙였지만 실제로는 **1인세대 중** 연령대별
  비중이다(stdgSexdAgeOneHh API가 1인세대만 연령별로 줌 -- 전체 인구의 연령 구조가
  아니다). 1인가구가 아닌 다가구 청년/고령 인구는 이 신호에 안 잡힌다.
- 구 단위(lv=2) 집계다. vacant_house_candidates.json은 동 단위인데, 동별 인구
  데이터를 따로 못 붙여서 지금은 "같은 구면 같은 값"으로 근사한다 -- 동구 안에서도
  16개 행정동 간 인구구조 차이는 전혀 구분을 못 한다.
- 두 API 모두 행정안전부 소속이라 서비스키가 같이 통했다(같은 기관 안에서는 계정
  단위로 넘어가는 듯) -- 다른 기관 API는 또 따로 활용신청이 필요할 수 있다
  (find_daedeok_tech_transfer.py의 NTB 때도 같은 패턴이었음).

환경변수 DATA_GO_KR_SERVICE_KEY 필요 (data.go.kr 개인 계정 인증키).
실행: DATA_GO_KR_SERVICE_KEY=... python -m scripts.build_daejeon_population_signals
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

import defusedxml.ElementTree as ET

OUT_PATH = Path(__file__).parent.parent / "data" / "daejeon_population_signals.json"
STATS_YM = "202607"  # 최신 통계 지연 감안, 넉넉히 최근 달로 고정

# 행정표준코드(대전 5개 구, 10자리 = 5자리 시군구코드 + 0 패딩)
DISTRICT_CODES = {
    "동구": "3011000000", "중구": "3014000000", "서구": "3017000000",
    "유성구": "3020000000", "대덕구": "3023000000",
}

YOUTH_AGE_BANDS = ["20", "30"]   # 청년 1인가구 근사: 20~30대
ELDERLY_AGE_BANDS = ["60", "70", "80", "90", "100"]  # 고령 1인가구 근사: 60대 이상


def _call(base_path: str, service_key: str, code_param: str, code: str) -> ET.Element:
    params = {
        "serviceKey": service_key, code_param: code,
        "srchFrYm": STATS_YM, "srchToYm": STATS_YM,
        "lv": "2", "pageNo": "1", "numOfRows": "5",
    }
    url = f"https://apis.data.go.kr/1741000/{base_path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return ET.fromstring(res.read())


def _find_row(root: ET.Element, district: str) -> dict:
    for item in root.findall(".//item"):
        if item.findtext("sggNm") == district:
            return {child.tag: child.text for child in item}
    raise ValueError(f"{district} 응답에 없음 -- API 코드/기간 확인 필요")


def build_district_signals(service_key: str, district: str) -> dict:
    code = DISTRICT_CODES[district]
    hh_row = _find_row(_call("admmPpltnHhStus/selectAdmmPpltnHhStus", service_key, "admmCd", code), district)
    one_hh_row = _find_row(_call("stdgSexdAgeOneHh/selectStdgSexdAgeOneHh", service_key, "stdgCd", code), district)

    total_household = int(hh_row["hhCnt"])
    total_one_person_household = int(one_hh_row["totHhCnt"])
    youth_one_hh = sum(int(one_hh_row[f"{g}{a}AgeHhCnt"]) for g in ("male", "feml") for a in YOUTH_AGE_BANDS)
    elderly_one_hh = sum(int(one_hh_row[f"{g}{a}AgeHhCnt"]) for g in ("male", "feml") for a in ELDERLY_AGE_BANDS)

    return {
        "district": district,
        "total_population": int(hh_row["totNmprCnt"]),
        "total_household": total_household,
        "total_one_person_household": total_one_person_household,
        "one_person_household_ratio": round(total_one_person_household / total_household, 4),
        "youth_one_person_household_ratio": round(youth_one_hh / total_one_person_household, 4),
        "elderly_one_person_household_ratio": round(elderly_one_hh / total_one_person_household, 4),
        "stats_ym": STATS_YM,
    }


def build() -> list[dict]:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    result = [build_district_signals(service_key, d) for d in DISTRICT_CODES]
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    for r in result:
        print(f"{r['district']}: 1인가구비율 {r['one_person_household_ratio']:.1%}, "
              f"청년1인가구비중 {r['youth_one_person_household_ratio']:.1%}, "
              f"고령1인가구비중 {r['elderly_one_person_household_ratio']:.1%}")
    print(f"완료 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
