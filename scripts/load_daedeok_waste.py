"""대덕구 사업장폐기물배출자 신고현황 → WasteRecord JSON 변환 (실데이터, CAS No. 자동 보강).

원본: data/raw/대전광역시 대덕구_사업장폐기물배출자 신고현황_20250812.csv
(공공데이터포털 15060392, 988행 = 사업장×폐기물종류×처리업소 조합 단위)

유성구 데이터(scripts/load_yuseong_waste.py)와 달리 이 데이터는 사업장별로 폐기물 종류마다
행이 나뉘어 있고, 실제 처리업소명·처리방법까지 있다. 사업장(상호+주소) 단위로 묶어
components에 폐기물 종류를 모으고, CAS No.는 동일하게 화학물질취급정보(15종)와 대조한다.
처리업소명/처리방법은 4단계(경제성·물류) 참고용으로 별도 필드에 남긴다.

실행: python -m scripts.load_daedeok_waste
"""
import csv
import io
import json
from pathlib import Path

from scripts.load_yuseong_waste import load_cas_lookup, _match_cas

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
WASTE_CSV = RAW_DIR / "대전광역시 대덕구_사업장폐기물배출자 신고현황_20250812.csv"
OUT_PATH = Path(__file__).parent.parent / "data" / "waste_registry_daedeok.json"


def load_records() -> list[dict]:
    cas_lookup = load_cas_lookup()
    text = WASTE_CSV.read_bytes().decode("cp949")
    rows = list(csv.DictReader(io.StringIO(text)))

    by_company: dict[tuple[str, str], dict] = {}
    for row in rows:
        company = row["상호"].strip()
        address = row["사업장도로명주소"].strip()
        key = (company, address)
        waste_type = row["폐기물 종류"].strip()
        if key not in by_company:
            by_company[key] = {
                "company": company,
                "address": address,
                "waste_discharge_type": row["배출구분"].strip(),
                "components": [],
                "handlers": [],   # 처리업소명 (참고용, 중복 허용 안 함)
                "methods": [],    # 처리방법 (참고용)
            }
        entry = by_company[key]
        if waste_type not in entry["components"]:
            entry["components"].append(waste_type)
        handler = row["처리업소명"].strip()
        if handler and handler not in entry["handlers"]:
            entry["handlers"].append(handler)
        method = row["처리방법"].strip()
        if method and method not in entry["methods"]:
            entry["methods"].append(method)

    records = []
    for i, entry in enumerate(by_company.values()):
        cas_by_component = {c: _match_cas(c, cas_lookup) for c in entry["components"]}
        records.append({
            "id": f"daedeok-{i + 1}",
            "company": entry["company"],
            "address": entry["address"],
            "industry": "",
            "waste_type": entry["waste_discharge_type"],
            "cas_no": next((v for v in cas_by_component.values() if v), ""),
            "components": entry["components"],
            "state": "",
            "amount_ton_per_year": 0.0,
            "description": ", ".join(entry["components"]),
            "cas_by_component": cas_by_component,
            "handlers": entry["handlers"],
            "methods": entry["methods"],
        })
    return records


def main():
    records = load_records()
    OUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with_cas = [r for r in records if r["cas_no"]]
    print(f"사업장(중복제거): {len(records)}건 -> {OUT_PATH}")
    print(f"CAS No. 매핑 성공: {len(with_cas)}건 / {len(records)}건")


if __name__ == "__main__":
    main()
