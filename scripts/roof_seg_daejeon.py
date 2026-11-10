"""시험 학습한 지붕 분할 모델(roof_seg_train.py)을 대전 공공건물 항공사진에 적용.

브이월드 WMTS Satellite(z19, 약 24cm) + 2D데이터 LT_C_BLDGINFO(건물 경계·건축면적).
.env 의 VWORLD_KEY 사용.

python -I scripts/roof_seg_daejeon.py <roof_seg.pt> <출력 폴더>
"""
import io, json, math, os, sys, urllib.parse, urllib.request

import cv2
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from roof_seg_train import lraspp_mobilenet_v3_large, overlay, to_t, PX_M2

# docs/solar_demo.html 의 건물 목록과 같은 좌표
BLDGS = [
    ("대전광역시청", 36.35055, 127.38496, 4500), ("대전컨벤션센터", 36.37499, 127.39177, 9000),
    ("대전예술의전당", 36.36661, 127.38368, 5500), ("대전시립미술관", 36.36671, 127.38574, 4200),
    ("한밭도서관", 36.30965, 127.40935, 3600), ("대전시립박물관", 36.33683, 127.33539, 5000),
    ("유성구청", 36.36222, 127.35616, 3200), ("대덕구청", 36.34666, 127.41557, 2800),
    ("중구청", 36.32557, 127.42149, 2600), ("서구청", 36.35548, 127.38379, 2900),
    ("동구청", 36.31181, 127.45481, 3000),
]
# 청사 MVP 추가분(2026-11-09, 브이월드 장소검색 좌표). 데모 가정 지붕면적은 없음(0)
# 충북도청: 여러 동 중 가장 큰 1989년 7층 동만. 충남도청: 브이월드 건축면적 속성이 0이라 폴리곤 면적으로 고름
BLDGS_CHEONGSA = [
    ("대전광역시교육청", 36.3524, 127.38365, 0), ("충청북도청", 36.63617, 127.49117, 0),
    ("충청남도청", 36.65863, 126.67258, 0), ("천안시청", 36.8149, 127.11398, 0),
]
Z = 19
N = 2 ** Z
# 건물 경계가 자동 정렬 범위(8m)보다 크게 어긋난 건물: 항공사진 보고 손으로 맞춘 이동량 (남+, 동+ m)
# 시립박물관: 대장 경계가 실제 쐐기형 건물보다 북쪽 32m. 지붕 대부분이 옥상정원이라 AI 지붕으로 정렬이 안 됨
FP_FIX = {"대전시립박물관": (31.75, -4.25)}
# 브이월드 경계가 의회·주차장·옆 땅까지 묶어 잡는 6곳(팀원 육안 검증 ①번): 팀원이 라벨링 도구(브이월드 사진 위)로
# 그린 실제 지붕 윤곽으로 바꿈. 좌표는 label/<이름>.png 픽셀이라 사진과 바로 맞음 → 자동 정렬·여유폭 안 씀.
# (geojson.io로 그린 윤곽은 해외 위성지도 기준이라 브이월드 사진과 10~25m 어긋나서 못 씀, 2026-11-09)
FP_LABEL = os.path.join(os.path.dirname(__file__), "..", "docs", "boundary_fix_labels.json")
FP_LABEL_USE = {"대전광역시청", "대전시립미술관", "유성구청", "서구청", "동구청", "중구청"}


def fp_from_label(name, shape):
    if name not in FP_LABEL_USE or not os.path.exists(FP_LABEL):
        return None
    lab = json.load(open(FP_LABEL, encoding="utf-8")).get(name)
    if not lab or (lab["height"], lab["width"]) != shape:  # 사진 범위가 바뀌면 픽셀 좌표가 안 맞음
        return None
    fp = np.zeros(shape, np.uint8)
    for g in lab["polygons"]:  # 지붕(1) + 그 위 구조물(2) 전체가 건물 윤곽
        cv2.fillPoly(fp, [np.round(np.array(g["points"])).astype(np.int32)], 1)
    return fp
MARGIN_M = 3  # 고층 건물은 지붕이 경계에서 밀려 보여서(기울어짐) 경계를 조금 넓혀서 셈. 크게 잡으면 광장·도로까지 지붕으로 셈
# ponytail: 기울어짐을 margin으로 때움. 정확히 하려면 높이·촬영각으로 경계를 옮기거나 수직정사영상 사용.

def key():
    return dict(l.strip().split("=", 1) for l in open(".env", encoding="utf-8") if "=" in l)["VWORLD_KEY"]


def get(url):
    req = urllib.request.Request(url, headers={"Referer": "http://localhost"})
    for i in range(4):
        try:
            return urllib.request.urlopen(req, timeout=30).read()
        except OSError:
            if i == 3:
                raise


def world_px(lat, lon):
    x = (lon + 180) / 360 * N * 256
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * N * 256
    return x, y


def features(lat, lon, r_m, size=100):
    dy, dx = r_m / 111320, r_m / (111320 * math.cos(math.radians(lat)))
    q = dict(service="data", request="GetFeature", data="LT_C_BLDGINFO", key=key(), domain="http://localhost",
             geomFilter=f"BOX({lon - dx},{lat - dy},{lon + dx},{lat + dy})", format="json", size=str(size),
             crs="EPSG:4326")
    r = json.loads(get("https://api.vworld.kr/req/data?" + urllib.parse.urlencode(q)))["response"]
    return r["result"]["featureCollection"]["features"] if r["status"] == "OK" else []


def building(lat, lon, r_m=50):
    # 데모 좌표가 건물 밖에 찍힌 경우가 있어 주변 r_m 안에서 건축면적이 가장 큰 건물
    # ponytail: 옆에 더 큰 건물이 있으면 그걸 잡음. 정확히 하려면 건물명/PNU로 조회.
    fs = features(lat, lon, r_m)
    if not fs:
        return None
    f = max(fs, key=lambda f: float(f["properties"]["archarea"] or 0) or poly_deg2(f["geometry"]["coordinates"]))
    return f["properties"], f["geometry"]["coordinates"]


def poly_deg2(mp):
    # 건축면적 속성이 0인 지역(충남 내포 등)에서 크기 비교용. 단위는 도² (같은 동네끼리 비교만)
    r = np.array(mp[0][0])
    return abs(np.dot(r[:, 0], np.roll(r[:, 1], 1)) - np.dot(r[:, 1], np.roll(r[:, 0], 1))) / 2 * 1e-9


def bld_height(p):
    h = float(p["height"] or 0)
    return h if h > 0 else float(p["grnd_flr"] or 0) * 3.5  # 높이 비어 있으면 층수 x 3.5m


def tiles(x0, y0, x1, y1, cache):
    tx0, ty0, tx1, ty1 = int(x0 // 256), int(y0 // 256), int(x1 // 256), int(y1 // 256)
    img = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256, 3), np.uint8)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            p = os.path.join(cache, f"{Z}_{ty}_{tx}.jpeg")
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                b = get(f"https://api.vworld.kr/req/wmts/1.0.0/{key()}/Satellite/{Z}/{ty}/{tx}.jpeg")
                if b[:2] != b"\xff\xd8":
                    raise RuntimeError(f"타일 아님 {ty}/{tx}: {b[:200]!r}")
                open(p, "wb").write(b)
            img[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = \
                np.array(Image.open(p).convert("RGB"))
    return img, tx0 * 256, ty0 * 256


# 패널 배치 규칙 (평지붕, 정남향 고정식 가정). 수치는 팀 검토 필요.
MOD_W, MOD_D, TILT = 2.28, 1.13, 15  # 모듈 가로(동서)·세로(m), 경사각 15°: 지붕당 발전량 우선 (docs/panel_params_review.md 4번)
KW_M2 = 0.22  # 모듈 효율 22% (TOPCon 상업용 580W급)
SETBACK_M = 0.5   # 지붕 가장자리 이격: 국토부 건축물 태양광 운영지침(2015) 난간 안쪽 50cm 이내 설치 금지
# 구조물·기존 패널 주변 여유(m): 높이 3m 옥탑이 연간 일사 20% 넘게 가리는 범위 + 남쪽은 점검통로
STRUCT_BUF_N, STRUCT_BUF_EW, STRUCT_BUF_S = 3.0, 2.0, 0.5
STRUCT_REVIEW_YEAR = 1988  # 내진설계 의무화(1988) 전 사용승인 건물은 '구조검토 필요' 표시
MIN_PART_M2 = 20  # 이보다 작은 조각은 버림


def shift(m, dy, dx):
    return np.roll(np.roll(m, dy, 0), dx, 1)


def align(fp, roof, max_m=8, px_m=0.25):  # 12m로 두면 옆 지하차도 덮개 같은 평평한 면을 따라감 (시립박물관 17m)
    """fp를 ±max_m 안에서 평행이동해 roof와 IoU가 가장 큰 (dy, dx)와 그 IoU."""
    r = round(max_m / px_m)
    near = cv2.dilate((fp > 0).astype(np.uint8), np.ones((2 * r + 1,) * 2, np.uint8)) > 0
    fp, roof = fp > 0, (roof > 0) & near  # 멀리 있는 다른 건물 지붕은 셈에서 뺌

    def iou(dy, dx):
        s = shift(fp, dy, dx)
        return (s & roof).sum() / max((s | roof).sum(), 1)
    best = max(((iou(dy, dx), dy, dx) for dy in range(-r, r + 1, 4) for dx in range(-r, r + 1, 4)))
    _, by, bx = best
    best = max(((iou(dy, dx), dy, dx) for dy in range(by - 3, by + 4) for dx in range(bx - 3, bx + 4)))
    return (best[1], best[2]), float(best[0])


SHADE_R_M = 150   # 이 거리 안의 건물만 그림자 계산
SHADE_MAX = 0.2   # 연간 일사(가중) 중 이 비율 넘게 가려지는 곳에는 패널 안 깜. 팀 검토 필요


def sun_positions(lat=36.35):
    """매월 21일 07~17시(태양시) 태양 (고도, 북쪽 기준 방위각, 가중치=sin 고도)."""
    phi = math.radians(lat)
    for m in range(12):
        dec = math.radians(23.44 * math.sin(math.radians(360 / 365 * (284 + 21 + 30.4 * m))))
        for hour in range(7, 18):
            ha = math.radians(15 * (hour - 12))
            sin_h = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha)
            if sin_h < math.sin(math.radians(5)):
                continue
            h = math.asin(sin_h)
            c = (math.sin(dec) - sin_h * math.sin(phi)) / (math.cos(h) * math.cos(phi))
            az = math.acos(max(-1, min(1, c)))
            yield h, (2 * math.pi - az if ha > 0 else az), sin_h


def shade_loss(H, S=None, px_m=1.0, lat=36.35, max_m=SHADE_R_M):
    """높이지도 H(m, 위=북)에서 높이 S(기본 H)인 면이 1년 동안 주변 건물에 가려지는 비율(일사 가중)."""
    S = H if S is None else S
    pad = int(max_m / px_m) + 1
    Hp = np.pad(H, pad)
    hmax = H.max()
    lost = np.zeros(H.shape); total = 0.0
    for h, az, w in sun_positions(lat):
        t = math.tan(h)
        sx, sy = math.sin(az), -math.cos(az)  # 태양 쪽으로 한 걸음: 동(+x), 북(-y)
        shaded = np.zeros(H.shape, bool)
        for step in range(1, int(min(max_m, hmax / t) / px_m) + 1):
            d = step * px_m
            ox, oy = round(sx * step), round(sy * step)
            ob = Hp[pad + oy:pad + oy + H.shape[0], pad + ox:pad + ox + H.shape[1]]
            shaded |= ob > S + d * t
        lost += w * shaded; total += w
    return lost / total


def row_pitch(lat=36.35, tilt=TILT, depth=MOD_D):
    """동지 09~15시에 앞줄 그림자가 뒷줄에 안 닿는 남북 줄 간격(m)."""
    phi, dec, ha = math.radians(lat), math.radians(-23.44), math.radians(45)
    sin_h = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha)
    h = math.asin(sin_h)
    cos_az = (sin_h * math.sin(phi) - math.sin(dec)) / (math.cos(h) * math.cos(phi))
    t = math.radians(tilt)
    return depth * math.cos(t) + depth * math.sin(t) / math.tan(h) * cos_az


def layout(pred, px_m=0.25, pitch_m=None, blocked=None):
    """pred(1=설치가능, 2=구조물)에 패널 직사각형(x, y, w, h px)을 깐다. 이미지 위쪽이 북쪽."""
    pitch = round((pitch_m or row_pitch(tilt=TILT)) / px_m)
    w, d = round(MOD_W / px_m), round(MOD_D * math.cos(math.radians(TILT)) / px_m)
    roof = (pred > 0).astype(np.uint8)
    sb = round(SETBACK_M / px_m)
    ok = cv2.erode(roof, np.ones((2 * sb + 1,) * 2, np.uint8), borderValue=0)
    # 구조물은 북쪽으로 그림자를 드리우므로 북쪽(이미지 위)으로 더 넓게 막음
    n, ew, so = (round(v / px_m) for v in (STRUCT_BUF_N, STRUCT_BUF_EW, STRUCT_BUF_S))
    k = np.ones((n + so + 1, 2 * ew + 1), np.uint8)
    ok[cv2.dilate((pred == 2).astype(np.uint8), k, anchor=(ew, so)) > 0] = 0
    if blocked is not None:
        ok[blocked] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(ok)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] * px_m ** 2 < MIN_PART_M2:
            ok[lab == i] = 0
    best = []
    for off in range(0, pitch, max(1, pitch // 4)):  # 줄 시작 위치 몇 가지 중 가장 많이 깔리는 것
        rects = []
        for y in range(off, ok.shape[0] - d + 1, pitch):
            full = ok[y:y + d].all(0)  # 이 줄 깊이 전체가 비어 있는 열
            x = 0
            while x <= len(full) - w:
                if full[x:x + w].all():
                    rects.append((x, y, w, d)); x += w
                else:
                    x += 1
        if len(rects) > len(best):
            best = rects
    return best


def main():
    ckpt, out = sys.argv[1], sys.argv[2]
    bldgs = BLDGS_CHEONGSA if sys.argv[3:] == ["cheongsa"] else BLDGS  # cheongsa: 청사 4곳만 (출력 폴더는 따로)
    cache = os.path.join(out, "tiles"); os.makedirs(cache, exist_ok=True)
    model = lraspp_mobilenet_v3_large(num_classes=3)
    model.load_state_dict(torch.load(ckpt, weights_only=True)); model.eval()
    rows = []
    for name, lat, lon, demo_roof in bldgs:
        b = building(lat, lon)
        if not b:
            print(name, "건물 경계 없음"); continue
        props, mp = b
        m_px = 156543.03392 * math.cos(math.radians(lat)) / N  # z19 m/px
        scale = m_px / 0.25  # 학습 데이터(25cm)에 맞춰 리샘플
        polys = [np.array([world_px(la, lo) for lo, la in ring]) for poly in mp for ring in poly[:1]]
        allp = np.vstack(polys)
        pad = 40 / m_px
        (x0, y0), (x1, y1) = allp.min(0) - pad, allp.max(0) + pad
        img, ox, oy = tiles(x0, y0, x1, y1, cache)
        img = img[int(y0 - oy):int(y1 - oy), int(x0 - ox):int(x1 - ox)]
        h, w = img.shape[:2]
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
        fp = np.zeros(img.shape[:2], np.uint8)
        for p in polys:
            cv2.fillPoly(fp, [np.round((p - (x0, y0)) * scale).astype(np.int32)], 1)

        H, W = img.shape[:2]
        ph, pw = -H % 32, -W % 32
        x = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="reflect")[None]
        with torch.no_grad():
            pred = model(to_t(x))["out"].argmax(1)[0, :H, :W].numpy().astype(np.uint8)
        # 건물 경계(지상 기준·대장 오차)와 사진 속 지붕이 수 m 어긋나서, AI 지붕에 가장 잘 겹치게 평행이동
        hand = fp_from_label(name, fp.shape)
        if hand is not None:
            fp, dy, dx = hand, 0, 0
            fit = float(((fp > 0) & (pred > 0)).sum() / max(((fp > 0) | (pred > 0)).sum(), 1))
            print(name, "손 보정 윤곽 사용")
        elif name in FP_FIX:
            dy, dx = (round(v / 0.25) for v in FP_FIX[name])
            s, r = shift(fp, dy, dx) > 0, pred > 0
            fit = float((s & r).sum() / max((s | r).sum(), 1))
        else:
            (dy, dx), fit = align(fp, pred > 0)
        fp = shift(fp, dy, dx)
        k = 0 if hand is not None else int(MARGIN_M / 0.25)  # 손 윤곽은 사진 속 지붕 그대로라 여유폭 없음
        zone = cv2.dilate(fp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1,) * 2))
        pred[zone == 0] = 0

        # 연간 그림자: 주변 건물 높이로 1m 격자 높이지도를 만들어 계산
        # ponytail: 건물 하나(MultiPolygon)는 높이 하나라 같은 건물 안 고층동이 저층 지붕을 가리는 건 못 셈.
        g, M = 4, SHADE_R_M
        hm = np.zeros((H // g + 2 * M, W // g + 2 * M), np.float32)
        nb = sorted(features(lat, lon, SHADE_R_M + 50, size=1000), key=lambda f: bld_height(f["properties"]))
        for f in nb:
            hv = bld_height(f["properties"])
            for poly in f["geometry"]["coordinates"]:
                q = np.array([world_px(la, lo) for lo, la in poly[0]])
                cv2.fillPoly(hm, [np.round((q - (x0, y0)) * scale / g + M).astype(np.int32)], hv)
        hm = np.roll(np.roll(hm, round(dy / g), 0), round(dx / g), 1)
        # 지붕면 높이: AI 지붕이 경계 밖으로 조금 나간 칸이 땅(0m)으로 잡혀 자기 건물에 가려지는 것 방지
        surf = cv2.dilate(hm, np.ones((2 * MARGIN_M + 1,) * 2, np.uint8))
        loss = shade_loss(hm, surf, lat=lat)[M:M + H // g, M:M + W // g]
        loss = cv2.resize(loss.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)
        shaded = (loss > SHADE_MAX) & (pred > 0)

        arch = float(props["archarea"] or 0)
        fpa = float(fp.sum() * PX_M2)  # 경계 다각형 면적 (archarea 속성이 틀린 건물이 있음)
        ai = float((pred == 1).sum() * PX_M2)
        st = float((pred == 2).sum() * PX_M2)
        rects = layout(pred, blocked=shaded)
        n_noshade = len(layout(pred))
        mod_m2 = len(rects) * MOD_W * MOD_D
        yr = (props.get("useapr_day") or "")[:4]
        rows.append(dict(name=name, archarea_m2=arch, demo_roof_m2=demo_roof, footprint_m2=round(fpa), fp_shift_m=[dy * .25, dx * .25], fp_fit_iou=round(fit, 2),
                         ai_usable_m2=round(ai), ai_structure_m2=round(st), shaded_m2=round(float(shaded.sum() * PX_M2)),
                         panels=len(rects), panels_noshade=n_noshade,
                         module_m2=round(mod_m2), module_ratio=round(mod_m2 / fpa, 3),
                         kw_ai=round(mod_m2 * KW_M2), kw_rule25=round(fpa * .25 * KW_M2),
                         use_year=yr or None, struct_review=(int(yr) < STRUCT_REVIEW_YEAR) if yr else None,  # 연도 모르면 None
                         height_m=props["height"], floors=props["grnd_flr"], bld_nm=props["bld_nm"]))
        print(f"{name}: 경계 이동 ({dx * .25:+.1f}, {dy * .25:+.1f})m 겹침 {fit:.2f}{' ⚠경계 확인' if fit < .5 or max(abs(dx), abs(dy)) * .25 >= 7.5 else ''} | 경계 {fpa:,.0f}㎡ | 빈지붕 {ai:,.0f} | 패널 {len(rects)}장 = 모듈 {mod_m2:,.0f}㎡ "
              f"({mod_m2 / fpa:.0%}) | {mod_m2 * KW_M2:,.0f}kW vs 25%가정 {fpa * .25 * KW_M2:,.0f}kW "
              f"| 그림자 {shaded.sum() * PX_M2:,.0f}㎡, 패널 {n_noshade - len(rects)}장 감소", flush=True)

        vis = overlay(img, pred)
        cnts, _ = cv2.findContours(fp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, (255, 60, 60), 2)
        pan = img.copy()
        pan[shaded] = (0.5 * pan[shaded] + [120, 0, 0]).astype(np.uint8)  # 그림자로 뺀 곳: 붉게
        for x, y, w, h in rects:
            cv2.rectangle(pan, (x, y), (x + w - 1, y + h - 1), (20, 40, 120), -1)
            cv2.rectangle(pan, (x, y), (x + w - 1, y + h - 1), (200, 220, 255), 1)
        cv2.drawContours(pan, cnts, -1, (255, 60, 60), 2)
        Image.fromarray(np.hstack([img, vis, pan])).save(os.path.join(out, f"{name}.png"))
        # 정답 라벨링·평가용 (roof_label_eval.py): 원본(25cm), 경계(0/1), 셈 영역(0/1), AI 예측(0/1/2)
        lab = os.path.join(out, "label"); os.makedirs(lab, exist_ok=True)
        Image.fromarray(img).save(os.path.join(lab, f"{name}.png"))
        np.savez_compressed(os.path.join(lab, f"{name}.npz"), fp=fp, zone=zone, pred=pred, shade=loss)
    json.dump(rows, open(os.path.join(out, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
