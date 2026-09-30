"""빈집 후보 데이터 생성 -- 위치·등급은 실제 공개자료/보도 기준, 건물 속성(면적·층수·
노후연수)은 합성값이다. src/vacant_house.py의 설계 근거 참고.

1) 동구 385건: data.go.kr "대전광역시 동구_빈집현황_20260720" 미리보기 표(행정동×등급)
   그대로 사용 -- 행정동·등급별 개수는 실제, 개별 건물 속성만 합성.
2) 실제 사례 5곳: 2026년 대전형 빈집정비사업 확정 대상지(언론보도, 2026-04-23
   공유재산 심의 완료) -- 동구 용운동·용전동, 중구 부사동, 서구 도마동, 대덕구 읍내동.
   위치는 실제, 건물 속성은 뉴스에 없어 합성.

서구/유성구/대덕구/중구의 자체 행정동×등급 표는 아직 안 옮김(각 구 페이지 재조회
필요) -- 지금은 동구 실측 + 실제 사례 5곳만으로 데모를 구성한다.

실행: python -m scripts.build_vacant_house_candidates
"""
import json
import random
from pathlib import Path

from src.vacant_house import VacantHouse

OUT_PATH = Path(__file__).parent.parent / "data" / "vacant_house_candidates.json"
RANDOM_SEED = 42

# data.go.kr "대전광역시 동구_빈집현황_20260720" 미리보기 표: 행정동 -> (1등급,2등급,3등급,4등급) 개수
DONGGU_REAL_COUNTS = {
    "중앙동": (3, 12, 3, 0), "신인동": (12, 11, 3, 0), "효동": (10, 17, 3, 0),
    "판암1동": (8, 16, 3, 0), "판암2동": (0, 1, 2, 0), "용운동": (9, 11, 3, 0),
    "대동": (6, 16, 5, 0), "자양동": (19, 7, 1, 0), "가양1동": (12, 8, 1, 0),
    "가양2동": (18, 5, 0, 0), "용전동": (16, 12, 0, 0), "성남동": (5, 12, 2, 0),
    "홍도동": (12, 4, 0, 0), "삼성동": (9, 12, 1, 0), "대청동": (3, 20, 8, 0),
    "산내동": (17, 18, 9, 0),
}

# 2026년 대전형 빈집정비사업 확정 대상지 (언론보도, 2026-04-23 공유재산 심의 완료)
REAL_CASES = [
    ("동구", "용운동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("동구", "용전동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("중구", "부사동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("서구", "도마동", "대전시 2026년 빈집정비사업 확정 대상지"),
    ("대덕구", "읍내동", "대전시 2026년 빈집정비사업 확정 대상지"),
]

BUILDING_TYPES = ["단독주택(다가구)", "공동주택(다세대·연립)", "그 외 주택"]
BUILDING_TYPE_WEIGHTS = [0.55, 0.30, 0.15]  # ponytail: 국가 통계상 노후 빈집은 단독주택 비중이 높다는 일반 경향만 반영한 가정치


def _synthesize_attrs(rng: random.Random, grade: int) -> dict:
    building_type = rng.choices(BUILDING_TYPES, BUILDING_TYPE_WEIGHTS)[0]
    floors = 1 if building_type != "공동주택(다세대·연립)" else rng.randint(2, 4)
    area_m2 = round(rng.uniform(45, 90) if building_type == "단독주택(다가구)" else rng.uniform(35, 70), 1)
    # 등급이 높을수록(노후·철거 대상) 노후연수도 크게 -- 등급 체계와 방향만 맞춘 단순 매핑
    age_years = rng.randint(20, 35) + (grade - 1) * 10
    return {"building_type": building_type, "floors": floors, "area_m2": area_m2, "age_years": age_years}


def build_donggu_candidates(rng: random.Random) -> list[VacantHouse]:
    houses = []
    for dong, counts in DONGGU_REAL_COUNTS.items():
        for grade, count in enumerate(counts, start=1):
            for i in range(count):
                attrs = _synthesize_attrs(rng, grade)
                houses.append(VacantHouse(
                    id=f"donggu-{dong}-{grade}-{i+1}",
                    district="동구", dong=dong, condition_grade=grade,
                    is_real_case=False, is_simulated=True,
                    source_note="위치·등급: data.go.kr 대전광역시 동구_빈집현황_20260720 실측 / 건물속성: 합성",
                    **attrs,
                ))
    return houses


def build_real_case_candidates(rng: random.Random) -> list[VacantHouse]:
    houses = []
    for i, (district, dong, note) in enumerate(REAL_CASES, start=1):
        attrs = _synthesize_attrs(rng, grade=3)  # 정비사업 확정 대상 = 철거·정비급이므로 3등급으로 취급
        houses.append(VacantHouse(
            id=f"realcase-{i}", district=district, dong=dong, condition_grade=3,
            is_real_case=True, is_simulated=True,
            source_note=f"위치: {note} (실제) / 면적·층수·노후연수: 보도자료에 없어 합성",
            **attrs,
        ))
    return houses


def build() -> list[dict]:
    rng = random.Random(RANDOM_SEED)
    houses = build_donggu_candidates(rng) + build_real_case_candidates(rng)
    result = [vars(h) for h in houses]
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    result = build()
    real_cases = sum(1 for h in result if h["is_real_case"])
    print(f"완료 - 빈집 후보 {len(result)}건(동구 실측 {len(result) - real_cases}건 + 실제 사례 {real_cases}건) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
