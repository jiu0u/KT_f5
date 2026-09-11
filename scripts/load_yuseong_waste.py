"""유성구 사업장폐기물배출자 데이터 → WasteRecord JSON 변환 (실데이터, CAS No. 자동 보강).

원본:
- data/raw/대전광역시 유성구_사업장폐기물배출자_20260721.csv (130개 사업장, 폐기물 종류 자유텍스트)
- data/raw/화학물질취급정보_20260909.xls (물질명 → CAS No. 매핑 15종)

CAS No.는 폐기물 종류 텍스트에 물질명이 부분 문자열로 나오면 매핑한다 (예: "폐황산" ⊃ "황산").
매핑 안 되는 폐기물 종류는 CAS No. 없이 description/components 텍스트로만 남아
src/match.py의 word-overlap 유사도 경로를 탄다.

실행: python -m scripts.load_yuseong_waste
"""
import csv
import io
import json
from pathlib import Path

import xlrd

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
WASTE_CSV = RAW_DIR / "대전광역시 유성구_사업장폐기물배출자_20260721.csv"
CHEM_XLS = RAW_DIR / "화학물질취급정보_20260909.xls"
OUT_PATH = Path(__file__).parent.parent / "data" / "waste_registry_yuseong.json"


def load_cas_lookup() -> dict[str, str]:
    """물질명 -> CAS No."""
    wb = xlrd.open_workbook(str(CHEM_XLS))
    ws = wb.sheet_by_index(0)
    lookup = {}
    for i in range(1, ws.nrows):
        name, cas_no = ws.cell_value(i, 1), ws.cell_value(i, 2)
        if name and cas_no:
            lookup[str(name).strip()] = str(cas_no).strip()
    return lookup


def _match_cas(component: str, cas_lookup: dict[str, str]) -> str:
    for substance, cas_no in cas_lookup.items():
        if substance in component:
            return cas_no
    return ""


def load_records() -> list[dict]:
    cas_lookup = load_cas_lookup()
    text = WASTE_CSV.read_bytes().decode("cp949")
    rows = list(csv.DictReader(io.StringIO(text)))

    records = []
    for i, row in enumerate(rows):
        components = [c.strip() for c in row["폐기물 종류"].split(",") if c.strip()]
        cas_by_component = {c: _match_cas(c, cas_lookup) for c in components}
        records.append({
            "id": f"yuseong-{i + 1}",
            "company": row["업소명"].strip(),
            "address": row["소재지"].strip(),
            "industry": "",
            "waste_type": row["배출종류"].strip(),
            "cas_no": next((v for v in cas_by_component.values() if v), ""),
            "components": components,
            "state": "",
            "amount_ton_per_year": 0.0,
            "description": row["폐기물 종류"].strip(),
            "cas_by_component": cas_by_component,  # 참고용: 성분별 매핑 근거
        })
    return records


def main():
    records = load_records()
    OUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with_cas = [r for r in records if r["cas_no"]]
    print(f"사업장: {len(records)}건 -> {OUT_PATH}")
    print(f"CAS No. 매핑 성공: {len(with_cas)}건 / {len(records)}건")


if __name__ == "__main__":
    main()
