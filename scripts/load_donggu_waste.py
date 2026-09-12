"""동구 사업장폐기물배출자 신고현황 → WasteRecord JSON 변환 (실데이터, CAS No. 자동 보강).

원본: data/raw/대전광역시 동구_사업장폐기물배출자 신고현황.csv (공공데이터포털 15081140, 138행)
유성구·대덕구와 달리 이 데이터는 폐기물 종류별 배출량(톤)이 행마다 있어, 사업장 단위로
묶을 때 실제 톤수를 합산할 수 있다.

실행: python -m scripts.load_donggu_waste
"""
import csv
import io
import json
from pathlib import Path

from scripts.load_yuseong_waste import load_cas_lookup, _match_cas

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
WASTE_CSV = RAW_DIR / "대전광역시 동구_사업장폐기물배출자 신고현황.csv"
OUT_PATH = Path(__file__).parent.parent / "data" / "waste_registry_donggu.json"


def load_records() -> list[dict]:
    cas_lookup = load_cas_lookup()
    text = WASTE_CSV.read_bytes().decode("cp949")
    rows = list(csv.DictReader(io.StringIO(text)))

    by_company: dict[str, dict] = {}
    for row in rows:
        company = row["상호"].strip()
        address = row["사업장도로명주소"].strip()
        waste_type = row["폐기물 종류"].strip()
        amount = float((row.get(" 배출량(톤) ") or row.get("배출량(톤)") or "0").strip() or 0)
        if company not in by_company:
            by_company[company] = {"company": company, "address": address, "components": [], "amount_ton": 0.0}
        entry = by_company[company]
        if waste_type not in entry["components"]:
            entry["components"].append(waste_type)
        entry["amount_ton"] += amount

    records = []
    for i, entry in enumerate(by_company.values()):
        cas_by_component = {c: _match_cas(c, cas_lookup) for c in entry["components"]}
        records.append({
            "id": f"donggu-{i + 1}",
            "company": entry["company"],
            "address": entry["address"],
            "industry": "",
            "waste_type": "",
            "cas_no": next((v for v in cas_by_component.values() if v), ""),
            "components": entry["components"],
            "state": "",
            "amount_ton_per_year": round(entry["amount_ton"], 3),
            "description": ", ".join(entry["components"]),
            "cas_by_component": cas_by_component,
        })
    return records


def main():
    records = load_records()
    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    with_cas = [r for r in records if r["cas_no"]]
    print(f"사업장(중복제거): {len(records)}건 -> {OUT_PATH}")
    print(f"CAS No. 매핑 성공: {len(with_cas)}건 / {len(records)}건")


if __name__ == "__main__":
    main()
