"""중간처분업체 추출 자체 점검. 실행: python -m tests.test_find_intermediate_treatment_companies"""
from scripts.find_intermediate_treatment_companies import find_intermediate_treatment_companies


def test_top_result_is_known_incinerator():
    result = find_intermediate_treatment_companies()
    assert result[0]["company"] == "(주)동양환경"
    assert len(result[0]["handled_waste"]) >= 10


def test_all_methods_are_intermediate_treatment():
    result = find_intermediate_treatment_companies()
    for c in result:
        for w in c["handled_waste"]:
            assert w["method"].startswith("중간처분")


def demo():
    test_top_result_is_known_incinerator()
    test_all_methods_are_intermediate_treatment()
    print("OK - 중간처분업체 추출 자체 점검 통과")


if __name__ == "__main__":
    demo()
