"""대전 도로안전표지(도로폭) 결과 자체 점검. 실행: python -m tests.test_build_daejeon_road_signs"""
import json
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "daejeon_road_signs.json"


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_all_five_districts_present():
    data = _load()
    assert {r["district"] for r in data} == {"동구", "중구", "서구", "유성구", "대덕구"}


def test_road_width_field_is_present_but_fake():
    # 처음엔 "도로폭 값 있는 건: 7221/7221"로 보고했는데, 그건 문자열이 비어있지만
    # 않으면 통과하는 테스트였다 -- 실제로 열어보니 전부 "0"이라는 플레이스홀더였다.
    # 아이SHADOW 프로젝트에서 "커버리지 지표가 항상 1.000"이었던 것과 같은 함정:
    # 지표가 수상할 정도로 완벽하면(100%) 측정 방법 자체를 의심해야 한다.
    data = _load()
    assert all((r.get("roadBt") or "").strip() for r in data), "최소한 빈 문자열은 아니어야 함"
    real_widths = {r["roadBt"] for r in data}
    assert real_widths == {"0"}, (
        "지금은 전부 '0'(의미 없는 플레이스홀더)이어야 정상 -- 실제 도로폭 데이터가 들어오면 "
        "이 테스트가 깨질 것이고, 그때 predict_accident_risk_candidates.py의 width_bucket도 고쳐야 함"
    )


def test_yuseong_has_most_signs():
    data = _load()
    counts = Counter(r["district"] for r in data)
    assert max(counts, key=counts.get) == "유성구"


def demo():
    test_all_five_districts_present()
    test_road_width_field_is_present_but_fake()
    test_yuseong_has_most_signs()
    print("OK - 대전 도로안전표지 자체 점검 통과 (도로폭은 전부 '0' 플레이스홀더 -- 실질적으로 미확보)")


if __name__ == "__main__":
    demo()
