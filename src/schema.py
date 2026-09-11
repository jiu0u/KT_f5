"""폐기물 레코드 스키마 — CLAUDE.md 3.1단계(정보구조화)의 출력 형식."""
from dataclasses import dataclass, field


@dataclass
class WasteRecord:
    id: str
    company: str
    address: str = ""
    industry: str = ""
    waste_type: str = ""          # 예: 폐산, 폐알칼리, 폐유기용제, 슬러지
    cas_no: str = ""              # 명확한 식별정보 — 있으면 우선 매칭에 사용
    components: list[str] = field(default_factory=list)
    state: str = ""               # 고체/액체
    amount_ton_per_year: float = 0.0
    description: str = ""         # 비정형 텍스트(성분·공정 설명) — CAS No. 없을 때 사용
