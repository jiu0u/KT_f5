"""데모 파이프라인의 근접도·TOPSIS 로직 자체 점검. 실행: python -m tests.test_demo"""
from scripts.demo import infer_proximity, topsis


def test_proximity_same_district_scores_higher():
    same = infer_proximity("대전광역시 대덕구 A", "대전광역시 대덕구 B")
    diff = infer_proximity("대전광역시 대덕구 A", "대전광역시 유성구 B")
    assert same == 1.0
    assert diff == 0.5
    assert same > diff


def test_topsis_ranks_better_alternative_first():
    alternatives = [
        {"name": "가까이+큰회사", "proximity": 1.0, "scale": 500.0},
        {"name": "멀리+작은회사", "proximity": 0.5, "scale": 10.0},
    ]
    ranked = topsis(alternatives, ["proximity", "scale"], [0.5, 0.5])
    assert ranked[0][0]["name"] == "가까이+큰회사"
    assert ranked[0][1] > ranked[1][1]


def test_topsis_single_alternative_gets_full_score():
    # 후보가 하나뿐이면 best==worst라 0/0 나올 수 있음 — 1.0으로 처리해야 함 (버그였음)
    ranked = topsis([{"name": "유일후보", "proximity": 1.0, "scale": 100.0}], ["proximity", "scale"], [0.5, 0.5])
    assert ranked[0][1] == 1.0


def demo():
    test_proximity_same_district_scores_higher()
    test_topsis_ranks_better_alternative_first()
    test_topsis_single_alternative_gets_full_score()
    print("OK - 데모 파이프라인(근접도/TOPSIS) 자체 점검 통과")


if __name__ == "__main__":
    demo()
