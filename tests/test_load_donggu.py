"""동구 실데이터 로더 자체 점검. 실행: python -m tests.test_load_donggu"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "waste_registry_donggu.json"


def test_138_rows_grouped_into_companies():
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert len(records) == 36, "138개 배출 신고 행이 사업장 단위로 묶여야 함"
    assert all(r["company"] and r["address"] for r in records)
    assert all(r["components"] for r in records)


def test_amount_ton_actually_summed():
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert any(r["amount_ton_per_year"] > 0 for r in records), "실제 배출량(톤) 합산값이 있어야 함"


def demo():
    test_138_rows_grouped_into_companies()
    test_amount_ton_actually_summed()
    print("OK - 동구 실데이터 로더 자체 점검 통과")


if __name__ == "__main__":
    demo()
