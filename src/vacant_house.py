"""빈집 후보 레코드 스키마 -- "AI 기반 대전 빈집 활용 최적화" 피벗용.

대전 5개 구의 공식 빈집 데이터(동구/서구/대덕구는 행정동별 등급 개수 집계,
유성구는 921건 개별 레코드지만 주소·좌표·면적 없음)에는 개별 건물 단위 속성이
없다. 그래서 위치(구·법정동)만 실제 데이터/실제 사례를 따르고, 면적·층수·
노후도 같은 건물 속성은 합성(is_simulated=True)한다 -- 실제 값으로 오인되지
않도록 항상 이 플래그를 같이 노출한다.

real_case 5곳(대전시 2026년 빈집정비사업 확정 대상지, 언론보도 기준)은 위치가
실제이므로 발표 데모의 핵심 사례로 쓴다: 동구 용운동·용전동, 중구 부사동,
서구 도마동, 대덕구 읍내동.
"""
from dataclasses import dataclass


@dataclass
class VacantHouse:
    id: str
    district: str          # 구 (동구/중구/서구/유성구/대덕구)
    dong: str               # 법정동/행정동
    building_type: str      # 단독주택(다가구) / 공동주택(다세대·연립) / 그 외 주택
    floors: int
    area_m2: float
    age_years: int
    condition_grade: int    # 1(양호, 즉시활용) ~ 3(노후, 철거·정비 필요) -- 대전 구청 등급 체계 기준
    is_real_case: bool = False   # True면 위치가 실제 확정 사업지(뉴스 보도 기준)
    is_simulated: bool = True    # building_type/floors/area_m2/age_years/condition_grade가 합성값이면 True
    source_note: str = ""        # 위치·속성의 근거를 짧게 남김 (실제/합성 구분용)
