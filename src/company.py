"""기업 DB 레코드 스키마 — PDF 제안서 "기업 300개 이상의 데이터베이스"에 대응.

WasteRecord(물질 단위 매칭용)와 달리 이건 기업 자체의 인적사항(이름·주소·업종)을
여러 출처에서 모아 하나로 합친 디렉터리다. 폐기물 정보가 있으면 waste_types에 채운다.
"""
from dataclasses import dataclass, field


@dataclass
class CompanyRecord:
    id: str
    name: str
    address: str = ""
    district: str = ""            # 유성구/대덕구 등
    industry: str = ""            # 업종명 (대기배출업소현황)
    product: str = ""             # 주생산품 (제조업공장등록현황)
    waste_types: list[str] = field(default_factory=list)  # 폐기물종류 (있으면)
    sources: list[str] = field(default_factory=list)      # 어느 원본 데이터에서 왔는지
