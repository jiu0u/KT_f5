# python -X utf8 -I scripts/fund_scenarios.py  → 자금 구조 비교안(Claude Docs) 숫자
"""자금 구조 3안 비교 (단위: 억 원). 우리 데모 가정: 청사 5곳 561kW, 초등학교 99곳 20,129kW,
1년차 1,333kWh/kW·연 0.5% 열화, 147원/kWh, 운영비 설치비 1.5%/년 + 옥상 사용료 0.3만 원/kW·년, 플랫폼 수수료 2%."""
KW1, KW2 = 610, 20129
Y1, DEG, PRICE, OM, RENT, FEE = 1333, .005, 147, .015, .3, .02


def annuity(p, r, n=20):
    return p * r / (1 - (1 + r) ** -n)


def ebitda(kw, cost, y):  # y년차 (1부터), 억 원
    gen = kw * Y1 * (1 - DEG) ** (y - 1)
    return gen * PRICE / 1e8 - kw * cost * OM / 1e4 - kw * RENT / 1e4


def irr(cfs):
    lo, hi = -.9, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        v = sum(c / (1 + m) ** t for t, c in enumerate(cfs))
        lo, hi = (m, hi) if v > 0 else (lo, m)
    return m


def plan_A(cost=109, rate=.045, equity=.2):
    """지금 데모: 출자 20% + 시민 채권 80%(수수료 포함), 이자 먼저·남는 돈으로 원금, 연 30억 한도로 분할"""
    kw = KW1 + KW2
    capex = kw * cost / 1e4
    bond = capex * (1 - equity) / (1 - FEE)
    years = -(-bond // 30)
    remain, payoff = bond, None
    for y in range(1, 21):
        cf = ebitda(kw, cost, y) - remain * rate
        if remain > 0:
            pay = min(remain, cf); remain -= pay
            if remain <= 1e-9 and payoff is None: payoff = y
    return dict(capex=capex, citizen=bond, years=int(years), people=bond * 1e4 / 500, payoff=payoff,
                cover=ebitda(kw, cost, 1) / (bond * rate))


def plan_B(cost=109, r1=.055, r_pf=.045, r_cit=.065, eq=.2, pf=.65, cit=.15):
    """2단계 혼합: 1단계 청사 시민 채권 100% 3년 만기 → 3년차 PF로 차환 / 2단계 학교 출자·PF·시민"""
    c1, c2 = KW1 * cost / 1e4, KW2 * cost / 1e4
    b1 = c1 / (1 - FEE)                    # 1단계 시민 채권
    e2, p2, s2 = c2 * eq, c2 * pf, c2 * cit / (1 - FEE)
    ds2 = annuity(p2, r_pf) + annuity(s2, r_cit)
    ds_refi = annuity(b1, r_pf, 17)        # 4년차부터 1단계 PF 차환분
    dscr = []
    eq_cf = [-e2]
    for y in range(1, 21):
        e = ebitda(KW1, cost, y) + ebitda(KW2, cost, y)
        ds = ds2 + (b1 * r1 if y <= 3 else ds_refi)
        dscr.append(e / ds)
        eq_cf.append(e - ds - (b1 if y == 3 else 0) + (b1 if y == 3 else 0))  # 3년차 상환은 차환 자금으로
    return dict(capex=c1 + c2, stage1=b1, citizen2=s2, equity=e2, pf=p2,
                people1=b1 * 1e4 / 500, people2=s2 * 1e4 / 500, rounds2=-(-s2 // 30),
                dscr1=dscr[0], dscr_min=min(dscr), irr=irr(eq_cf), ds=ds2)


if __name__ == "__main__":
    a = plan_A(); print("A", {k: round(v, 2) if isinstance(v, float) else v for k, v in a.items()})
    for r in (.045, .06, .07):
        print(" A 이율", r, plan_A(rate=r)["payoff"], "년차 상환")
    for cost in (109, 130, 160):
        b = plan_B(cost=cost); print("B", cost, {k: round(v, 2) if isinstance(v, float) else v for k, v in b.items()})
    print("민감도 DSCR 1년차 (설치비 × 판매단가)")
    for cost in (109, 130, 160):
        row = []
        for price in (147, 130, 110):
            PRICE = price; globals()["PRICE"] = price
            row.append(round(plan_B(cost=cost)["dscr1"], 2))
        globals()["PRICE"] = 147
        print(cost, row)
    # 자체 확인: 연금 공식
    assert abs(annuity(100, .045) - 7.688) < .01
