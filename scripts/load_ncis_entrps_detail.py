"""NCIS PRTR 사업장별 상세 정보 — 실제 배출·이동량(kg/년)까지 확보.

scripts/load_ncis_prtr.py는 "이 사업장이 이 물질을 취급한다"는 사실만 준다.
이 스크립트는 한 단계 더 들어가 사업장별 상세 페이지에서 물질별 대기/수계/토양배출량,
폐수이동량, **폐기물이동량**을 가져온다. 폐기물이동량 > 0이면 그 물질을 실제로 폐기물로
내보내고 있다는 뜻이라, "취급만 함"과 "진짜 폐기물을 배출함"을 구분할 수 있다.

출처: https://icis.mcee.go.kr /prtr/prtrInfo/entrpsSearch.do (대전 사업장 목록) +
      /prtr/prtrInfo/entrpsDetailPopup.do (사업장별 상세)

실행: python -m scripts.load_ncis_entrps_detail  (공공 서버에 순차 요청, 1분 내외)
"""
import json
import re
import time
from pathlib import Path

from scripts.load_ncis_prtr import AREA_DAEJEON, YEAR, post_form

OUT_PATH = Path(__file__).parent.parent / "data" / "ncis_entrps_detail_daejeon_2024.json"
REQUEST_DELAY_SEC = 0.3

ENTRPS_LINK_RE = re.compile(r"<a[^>]*onclick=\"fnEntrpsDetail\(.(\d+).\);[^>]*>([^<]+)</a>")
INFO_RE = re.compile(
    r'주 소</th>\s*<td class="left bdnone">([^<]*)</td>.*?'
    r'연락처</th>\s*<td class="left bdnone">([^<]*)</td>.*?'
    r'업 종</th>\s*<td class="left bdnone">([^<]*)</td>.*?'
    r'종업원 수</th>\s*<td class="left bdnone">([^<]*)</td>',
    re.S,
)
SUBSTANCE_ROW_RE = re.compile(
    r'<td class="" rowspan="2">\d{4}</td>\s*<td class="" rowspan="2">([^<]+)</td>\s*'
    r'<td class="left" rowspan="2" >([^<]+)[\s\S]*?</tr>\s*<tr>\s*'
    r'<td class="right">\s*([\d,]+)\s*</td>\s*<td class="right">\s*([\d,]+)\s*</td>\s*'
    r'<td class="right">\s*([\d,]+)\s*</td>\s*<td class="right">\s*([\d,]+)\s*</td>\s*'
    r'<td class="right bdnone">\s*([\d,]+)\s*</td>'
)


def _num(s: str) -> float:
    return float(s.replace(",", "") or 0)


def fetch_entrps_list(area1: str, year: str) -> list[dict]:
    html = post_form("/prtr/prtrInfo/entrpsSearch.do", {
        "pageIndex": "1", "sortColumn": "", "sortOrder": "", "searchIndutyCode": "",
        "searchIndutyCode2": "", "searchIndutyCode3": "", "searchIndutyCode4": "",
        "searchIndutyConditonCount": "", "searchYearCheck": year, "searchIndutyNm": "",
        "searchIndutyFullNm": "", "searchAreaNm1": "", "searchAreaNm2": "", "searchMttrNm": "",
        "clCode": "2", "queryName": "", "entrpsId": "", "induty": "", "indutyTxt": "",
        "mttr": "", "nwdSe": "", "searchYear": year, "searchArea1": area1, "searchArea2": "",
        "searchMttr": "", "searchEntrpsNm": "", "searchInduty": "", "searchInduty2": "",
        "searchInduty3": "", "searchInduty4": "", "pageUnit": "100",
    })
    return [{"entrps_id": eid, "name": name.strip()} for eid, name in ENTRPS_LINK_RE.findall(html)]


def fetch_entrps_detail(entrps_id: str, year: str) -> dict:
    html = post_form("/prtr/prtrInfo/entrpsDetailPopup.do", {
        "entrpsId": entrps_id, "reportYear": year, "searchYear": year,
    })
    info = INFO_RE.search(html)
    address, phone, industry, employees = (g.strip() for g in info.groups()) if info else ("", "", "", "")
    substances = [
        {
            "cas_no": cas.strip(), "substance": name.strip(),
            "air_kg": _num(air), "water_kg": _num(water), "soil_kg": _num(soil),
            "pyesoo_kg": _num(pyesoo), "pyegi_kg": _num(pyegi),
        }
        for cas, name, air, water, soil, pyesoo, pyegi in SUBSTANCE_ROW_RE.findall(html)
    ]
    return {"address": address, "phone": phone, "industry": industry, "employees": employees, "substances": substances}


def main():
    companies = fetch_entrps_list(AREA_DAEJEON, YEAR)
    print(f"대전 PRTR 등록 사업장: {len(companies)}곳")

    records = []
    for c in companies:
        detail = fetch_entrps_detail(c["entrps_id"], YEAR)
        records.append({**c, **detail})
        waste_flags = sum(1 for s in detail["substances"] if s["pyegi_kg"] > 0)
        print(f"  {c['name']}: 취급 {len(detail['substances'])}종, 폐기물이동량>0 {waste_flags}종")
        time.sleep(REQUEST_DELAY_SEC)

    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    confirmed_waste_pairs = sum(1 for r in records for s in r["substances"] if s["pyegi_kg"] > 0)
    print(f"완료: {len(records)}개 사업장 -> {OUT_PATH}")
    print(f"실제 폐기물이동량이 확인된 (사업장,물질) 쌍: {confirmed_waste_pairs}건")


if __name__ == "__main__":
    main()
