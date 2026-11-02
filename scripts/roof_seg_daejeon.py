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
Z = 19
N = 2 ** Z
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


def building(lat, lon, r_m=50):
    # 데모 좌표가 건물 밖에 찍힌 경우가 있어 주변 r_m 안에서 건축면적이 가장 큰 건물
    # ponytail: 옆에 더 큰 건물이 있으면 그걸 잡음. 정확히 하려면 건물명/PNU로 조회.
    dy, dx = r_m / 111320, r_m / (111320 * math.cos(math.radians(lat)))
    q = dict(service="data", request="GetFeature", data="LT_C_BLDGINFO", key=key(), domain="http://localhost",
             geomFilter=f"BOX({lon - dx},{lat - dy},{lon + dx},{lat + dy})", format="json", size="100",
             crs="EPSG:4326")
    r = json.loads(get("https://api.vworld.kr/req/data?" + urllib.parse.urlencode(q)))["response"]
    if r["status"] != "OK":
        return None
    f = max(r["result"]["featureCollection"]["features"], key=lambda f: float(f["properties"]["archarea"] or 0))
    return f["properties"], f["geometry"]["coordinates"]


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
MOD_W, MOD_D, TILT = 2.28, 1.13, 25  # 모듈 가로(동서)·세로(m), 경사각
SETBACK_M = 1.0   # 지붕 가장자리 이격
STRUCT_BUF_M = 1.0  # 구조물·기존 패널 주변 여유
MIN_PART_M2 = 20  # 이보다 작은 조각은 버림


def row_pitch(lat=36.35, tilt=TILT, depth=MOD_D):
    """동지 09~15시에 앞줄 그림자가 뒷줄에 안 닿는 남북 줄 간격(m)."""
    phi, dec, ha = math.radians(lat), math.radians(-23.44), math.radians(45)
    sin_h = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha)
    h = math.asin(sin_h)
    cos_az = (sin_h * math.sin(phi) - math.sin(dec)) / (math.cos(h) * math.cos(phi))
    t = math.radians(tilt)
    return depth * math.cos(t) + depth * math.sin(t) / math.tan(h) * cos_az


def layout(pred, px_m=0.25, pitch_m=None):
    """pred(1=설치가능, 2=구조물)에 패널 직사각형(x, y, w, h px)을 깐다. 이미지 위쪽이 북쪽."""
    pitch = round((pitch_m or row_pitch()) / px_m)
    w, d = round(MOD_W / px_m), round(MOD_D * math.cos(math.radians(TILT)) / px_m)
    roof = (pred > 0).astype(np.uint8)
    sb = round(SETBACK_M / px_m)
    ok = cv2.erode(roof, np.ones((2 * sb + 1,) * 2, np.uint8), borderValue=0)
    sbuf = round(STRUCT_BUF_M / px_m)
    ok[cv2.dilate((pred == 2).astype(np.uint8), np.ones((2 * sbuf + 1,) * 2, np.uint8)) > 0] = 0
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
    cache = os.path.join(out, "tiles"); os.makedirs(cache, exist_ok=True)
    model = lraspp_mobilenet_v3_large(num_classes=3)
    model.load_state_dict(torch.load(ckpt, weights_only=True)); model.eval()
    rows = []
    for name, lat, lon, demo_roof in BLDGS:
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
        k = int(MARGIN_M / 0.25)
        zone = cv2.dilate(fp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1,) * 2))

        H, W = img.shape[:2]
        ph, pw = -H % 32, -W % 32
        x = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="reflect")[None]
        with torch.no_grad():
            pred = model(to_t(x))["out"].argmax(1)[0, :H, :W].numpy().astype(np.uint8)
        pred[zone == 0] = 0

        arch = float(props["archarea"] or 0)
        fpa = float(fp.sum() * PX_M2)  # 경계 다각형 면적 (archarea 속성이 틀린 건물이 있음)
        ai = float((pred == 1).sum() * PX_M2)
        st = float((pred == 2).sum() * PX_M2)
        rects = layout(pred)
        mod_m2 = len(rects) * MOD_W * MOD_D
        rows.append(dict(name=name, archarea_m2=arch, demo_roof_m2=demo_roof, footprint_m2=round(fpa),
                         ai_usable_m2=round(ai), ai_structure_m2=round(st), panels=len(rects),
                         module_m2=round(mod_m2), module_ratio=round(mod_m2 / fpa, 3),
                         kw_ai=round(mod_m2 * 0.2), kw_rule25=round(fpa * .25 * 0.2),
                         height_m=props["height"], floors=props["grnd_flr"], bld_nm=props["bld_nm"]))
        print(f"{name}: 경계 {fpa:,.0f}㎡ | 빈지붕 {ai:,.0f} | 패널 {len(rects)}장 = 모듈 {mod_m2:,.0f}㎡ "
              f"({mod_m2 / fpa:.0%}) | {mod_m2 * .2:,.0f}kW vs 25%가정 {fpa * .25 * .2:,.0f}kW", flush=True)

        vis = overlay(img, pred)
        cnts, _ = cv2.findContours(fp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, (255, 60, 60), 2)
        pan = img.copy()
        for x, y, w, h in rects:
            cv2.rectangle(pan, (x, y), (x + w - 1, y + h - 1), (20, 40, 120), -1)
            cv2.rectangle(pan, (x, y), (x + w - 1, y + h - 1), (200, 220, 255), 1)
        cv2.drawContours(pan, cnts, -1, (255, 60, 60), 2)
        Image.fromarray(np.hstack([img, vis, pan])).save(os.path.join(out, f"{name}.png"))
    json.dump(rows, open(os.path.join(out, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
