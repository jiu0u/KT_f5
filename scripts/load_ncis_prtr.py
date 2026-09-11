"""화학물질안전원 PRTR(화학물질 배출·이동량) 공개시스템에서 대전 지역 실측
물질별×사업장 데이터를 가져온다 — 유성구/대덕구 배출신고 데이터의 "법정 분류명뿐"
한계를 넘어서는 진짜 CAS No. 단위 화학물질 취급 사업장 데이터.

출처: https://icis.mcee.go.kr (환경부 화학물질안전원, 로그인/API 키 불필요, 공개 조회)
- /prtr/prtrInfo/unitySearch.do : 지역(대전=25) 내 조사대상 물질 목록 + 배출업체수
- /prtr/prtrInfo/entrpsSearchPopup.do : 특정 물질을 취급하는 업체 목록(사업장명·주소·업종)

주의: 이 시스템은 배출량 조사대상 물질(1톤/년 이상 취급, 총 400여종 중 지정된 항목)만
다루므로 모든 화학물질을 포괄하진 않지만, 실제 CAS No.와 사업장이 1:1로 연결된
데이터라는 점에서 지자체 폐기물배출신고 데이터보다 매칭에 훨씬 유용하다.

실행: python -m scripts.load_ncis_prtr  (공공 서버에 순차 요청, 수십 초 소요)
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://icis.mcee.go.kr"
OUT_PATH = Path(__file__).parent.parent / "data" / "ncis_prtr_daejeon_2024.json"
YEAR = "2024"
AREA_DAEJEON = "25"
REQUEST_DELAY_SEC = 0.3  # 공공서버 배려용 (ponytail: 순차 호출, 병렬화 안 함)

SUBSTANCE_ROW_RE = re.compile(
    r'<td class="">([^<]*)</td>\s*<td class="left">([^<]*)</td>\s*'
    r'<td class=""><a[^>]*onclick="fnEntrpsList\(.(\d+).,[^>]*>\s*([\d,]+)\s*</a>'
)
COMPANY_ROW_RE = re.compile(
    r'<tr>\s*<td[^>]*>(\d+)</td>\s*<td[^>]*>([^<]*)</td>\s*'
    r'<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>'
)


def post_form(path: str, data: dict) -> str:
    body = "&".join(f"{k}={urllib.parse.quote_plus(v)}" for k, v in data.items())
    req = urllib.request.Request(
        BASE + path, data=body.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def fetch_substance_list(area1: str, year: str) -> list[dict]:
    html = post_form("/prtr/prtrInfo/unitySearch.do", {
        "pageIndex": "1", "sortColumn": "", "sortOrder": "", "searchYearCheck": year,
        "searchIndutyNm": "", "searchIndutyFullNm": "", "searchAreaNm1": "",
        "searchAreaNm2": "", "searchMttrNm": "", "entrpsId": "", "clCode": "2",
        "queryName": "", "induty": "", "indutyTxt": "", "mttr": "", "nwdSe": "",
        "searchYear": year, "searchArea1": area1, "searchArea2": "", "searchMttr": "",
        "searchInduty": "", "searchEntrpsNm": "", "pageUnit": "100",
    })
    return [
        {"cas_no": cas.strip(), "substance": name.strip(), "mttr_sn": sn, "company_count": int(count.replace(",", ""))}
        for cas, name, sn, count in SUBSTANCE_ROW_RE.findall(html)
    ]


def fetch_companies_for_substance(mttr_sn: str, substance_label: str, area1: str, year: str, total: int) -> list[dict]:
    companies = []
    pages = max(1, -(-total // 10))  # ceil(total / 10)
    for page in range(1, pages + 1):
        html = post_form("/prtr/prtrInfo/entrpsSearchPopup.do", {
            "mttr": mttr_sn, "searchYear": year, "reportYear": year, "searchMttr": "mttr",
            "searchMttrNm": substance_label, "pageIndex": str(page), "sortColumn": "",
            "sortOrder": "", "searchYearCheck": year, "searchIndutyNm": "",
            "searchIndutyFullNm": "", "searchAreaNm1": "", "searchAreaNm2": "",
            "entrpsId": "", "queryName": "", "searchArea1": area1, "searchArea2": "",
            "searchInduty": "", "induty": "", "indutyTxt": "",
        })
        for _, name, address, postal, industry in COMPANY_ROW_RE.findall(html):
            companies.append({
                "name": name.strip(), "address": address.strip(),
                "postal_code": postal.strip(), "industry": industry.strip(),
            })
        time.sleep(REQUEST_DELAY_SEC)
    return companies


def main():
    substances = fetch_substance_list(AREA_DAEJEON, YEAR)
    print(f"대전 조사대상 물질: {len(substances)}종")

    records = []
    for s in substances:
        label = f"{s['substance']}({s['cas_no']})"
        companies = fetch_companies_for_substance(s["mttr_sn"], label, AREA_DAEJEON, YEAR, s["company_count"])
        records.append({**s, "companies": companies})
        print(f"  {s['cas_no']} {s['substance']}: {len(companies)}개 사업장")
        time.sleep(REQUEST_DELAY_SEC)

    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    total_companies = len({c["name"] for r in records for c in r["companies"]})
    print(f"완료: {len(records)}개 물질, 중복제거 후 {total_companies}개 사업장 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
