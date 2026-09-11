"""NCIS PRTR 사업장 상세(폐기물이동량 포함)를 WasteRecord 스키마로 변환.

data/ncis_entrps_detail_daejeon_2024.json은 (사업장, 물질)마다 실제 폐기물이동량(kg/년)을
포함한다. WasteRecord.cas_no는 문자열 하나뿐이라 회사 단위로 합치지 않고, 이전과
동일하게 (물질, 사업장) 쌍 하나당 레코드 하나를 만든다 — 다만 이번엔 amount_ton_per_year에
실제 폐기물이동량(폐기물로 실제 이동한 양)을 채운다.

폐기물이동량 > 0 이면 그 물질을 실제로 폐기물로 내보내고 있다는 확인된 증거이고,
0이면 취급(생산·원료사용 등)만 확인됐을 뿐 폐기물 배출 증거는 없다 — 이 구분은
description에 표시해 둔다.

실행: python -m scripts.build_ncis_waste_registry
"""
import json
from pathlib import Path

SRC_PATH = Path(__file__).parent.parent / "data" / "ncis_entrps_detail_daejeon_2024.json"
OUT_PATH = Path(__file__).parent.parent / "data" / "waste_registry_ncis.json"


def main():
    companies = json.loads(SRC_PATH.read_text(encoding="utf-8"))

    records = []
    for c in companies:
        for s in c["substances"]:
            confirmed = s["pyegi_kg"] > 0
            records.append({
                "id": f"ncis-{len(records) + 1}",
                "company": c["name"],
                "address": c["address"],
                "industry": c["industry"],
                "waste_type": "",
                "cas_no": s["cas_no"],
                "components": [s["substance"]],
                "state": "",
                "amount_ton_per_year": round(s["pyegi_kg"] / 1000, 3),
                "description": (
                    f"PRTR 2024: {s['substance']} 폐기물이동량 {s['pyegi_kg']:.0f}kg/년 (실제 폐기물 배출 확인)"
                    if confirmed else
                    f"PRTR 2024: {s['substance']} 취급 확인, 폐기물이동량 0 (배출 증거 없음, 원료사용 등으로 추정)"
                ),
                "confirmed_waste": confirmed,
            })

    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    confirmed = sum(1 for r in records if r["confirmed_waste"])
    print(f"(물질,사업장) 레코드: {len(records)}건 -> {OUT_PATH}")
    print(f"실제 폐기물이동량 확인(confirmed_waste): {confirmed}건 / 취급만 확인: {len(records) - confirmed}건")


if __name__ == "__main__":
    main()
