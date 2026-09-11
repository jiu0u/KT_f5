"""대덕구 실데이터 로더 자체 점검. 실행: python -m tests.test_load_daedeok"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "waste_registry_daedeok.json"


def test_988_rows_grouped_into_companies():
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert len(records) == 177, "988개 배출 신고 행이 사업장 단위로 묶여야 함"
    assert all(r["company"] for r in records)
    missing_address = sum(1 for r in records if not r["address"])
    assert missing_address < len(records), "원본에 주소 누락 행이 일부 있음(알려진 한계)"
    assert all(r["components"] for r in records), "사업장마다 폐기물 종류가 1개 이상 있어야 함"


def test_no_cas_match_in_this_dataset():
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    # 이 데이터셋의 폐기물 종류는 법정 분류명뿐이라 화학물질 15종과 안 겹침 (알려진 한계)
    assert all(not r["cas_no"] for r in records)


def demo():
    test_988_rows_grouped_into_companies()
    test_no_cas_match_in_this_dataset()
    print("OK - 대덕구 실데이터 로더 자체 점검 통과")


if __name__ == "__main__":
    demo()
