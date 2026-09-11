"""GHG 배출권 대상 사업장 2024년 실측 폐기물 발생량(대전) → data/ghg_waste_2024.json 변환.

원본: data/raw/대전_대표사업장_폐기물발생량(GHG배출권대상)_2024.xlsx

주의: 이 데이터셋은 사업장 단위 폐기물 "총량(톤/년, 카테고리별)"만 제공하며
CAS No./성분 정보가 없다. 따라서 src/match.py의 물질 단위 매칭(1~2단계) 입력으로
직접 쓸 수 없고, CLAUDE.md 4단계(경제성) 검증 및 실측 규모 확인용 앵커 데이터로 쓴다.

실행: python -m scripts.load_ghg_waste
"""
import json
from pathlib import Path

import openpyxl

RAW_PATH = Path(__file__).parent.parent / "data" / "raw" / "대전_대표사업장_폐기물발생량(GHG배출권대상)_2024.xlsx"
OUT_PATH = Path(__file__).parent.parent / "data" / "ghg_waste_2024.json"

# 원본 헤더(한글) → 필드명
FIELDS = [
    "rep_site_code", "rep_site_name", "site_name", "site_category",
    "type", "feature", "industry", "sub_industry", "year",
    "waste_general_ton", "waste_designated_ton", "waste_construction_ton",
    "waste_household_ton", "waste_other_ton", "waste_total_ton",
    "strategic_industry_candidate",
]
NUMERIC_FIELDS = {
    "waste_general_ton", "waste_designated_ton", "waste_construction_ton",
    "waste_household_ton", "waste_other_ton", "waste_total_ton",
}


def load_records() -> list[dict]:
    wb = openpyxl.load_workbook(RAW_PATH, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))[1:]  # 헤더 제외
    records = []
    for row in rows:
        record = dict(zip(FIELDS, row))
        for field in NUMERIC_FIELDS:
            record[field] = float(record[field] or 0)
        records.append(record)
    return records


def main():
    records = load_records()
    OUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    semiconductor = [r for r in records if r["strategic_industry_candidate"] == "반도체"]
    total_designated = sum(r["waste_designated_ton"] for r in records)
    print(f"전체 사업장: {len(records)}건 -> {OUT_PATH}")
    print(f"지정폐기물 합계(전체 {len(records)}건 기준): {total_designated:.1f}톤/년")
    print(f"반도체 전략산업 후보: {len(semiconductor)}건")
    # 참고: CLAUDE.md에는 "지정폐기물 약 3,600톤/년"으로 적혀 있으나, 이 원본 73건 전체
    # 기준으로는 {total_designated:.1f}톤으로 계산됨 — 어떤 부분집합/필터로 3,600톤이
    # 나온 것인지는 원 작성자 확인 필요 (사업장구분 필터 등 후보 있음).


if __name__ == "__main__":
    main()
