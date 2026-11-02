"""AI Hub 「태양광 발전 현황 및 적지 분석 데이터」(71348) 적지분석 25cm로 지붕 분할 시험 학습.

클래스: 0=배경, 1=설치 가능 지붕(Top/Roof), 2=구조물(Structure).
라벨은 '적지'로 고른 건물에만 있어서, 라벨 주변(DILATE px)만 학습·평가하고 나머지는 무시한다.
  -> 건물 경계가 주어진 상태에서 그 안을 분류하는 용도 (대전에선 GIS건물통합정보 경계를 줌).

python -I scripts/roof_seg_train.py <Validation 폴더> <출력 폴더> [epochs]
"""
import glob, io, json, os, sys, time, zipfile, zlib

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision.models.segmentation import lraspp_mobilenet_v3_large

CLS = {"Top": 1, "Roof": 1, "Structure": 2}
DILATE = 32  # px = 8m
IGN = 255
PX_M2 = 0.25 ** 2


def load(base, out):
    cache = os.path.join(out, "cache.npz")
    if os.path.exists(cache):
        d = np.load(cache)
        return d["x"], d["y"], d["names"]
    xs, ys, names = [], [], []
    for kind in ["Roof", "Top"]:
        zi = zipfile.ZipFile(glob.glob(f"{base}/01.원천데이터/*{kind}.zip")[0])
        zl = zipfile.ZipFile(glob.glob(f"{base}/02.라벨링데이터/VL_VL_01*{kind}.zip")[0])
        for n in sorted(zl.namelist()):
            stem = n.strip("/").rsplit(".", 1)[0]
            objs = json.loads(zl.read(n).decode("utf-8-sig"))["Learning Data Info"]["objects"]
            img = np.array(Image.open(io.BytesIO(zi.read("/" + stem + ".tif"))).convert("RGB"))
            y = np.zeros(img.shape[:2], np.uint8)
            # 구조물을 지붕 위에 덮어써야 하므로 지붕 먼저
            for o in sorted(objs, key=lambda o: CLS[o["class_name"]]):
                p = np.round(np.array(o["points"]).reshape(-1, 2)).astype(np.int32)
                cv2.fillPoly(y, [p], CLS[o["class_name"]])
            near = cv2.dilate((y > 0).astype(np.uint8), np.ones((2 * DILATE + 1,) * 2, np.uint8))
            y[near == 0] = IGN
            xs.append(img); ys.append(y); names.append(stem)
    x, y, names = np.stack(xs), np.stack(ys), np.array(names)
    np.savez(cache, x=x, y=y, names=names)
    return x, y, names


def split(names, frac=0.15):
    # 같은 도엽(img_no)의 타일은 겹치는 건물이 있어 같은 쪽으로 보냄
    key = np.array([zlib.crc32(n[8:16].encode()) % 100 for n in names])
    return key >= frac * 100, key < frac * 100


def to_t(x):
    t = torch.from_numpy(x).permute(0, 3, 1, 2).float() / 255
    m = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    s = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
    return (t - m) / s


def batches(x, y, bs, crop, rng):
    idx = rng.permutation(len(x))
    for i in range(0, len(idx) - bs + 1, bs):
        b = idx[i:i + bs]
        r, c = rng.integers(0, 512 - crop + 1, 2)
        xb, yb = x[b, r:r + crop, c:c + crop], y[b, r:r + crop, c:c + crop]
        k = rng.integers(4)
        xb, yb = np.rot90(xb, k, (1, 2)), np.rot90(yb, k, (1, 2))
        if rng.random() < .5:
            xb, yb = xb[:, :, ::-1], yb[:, :, ::-1]
        yield to_t(np.ascontiguousarray(xb)), torch.from_numpy(np.ascontiguousarray(yb)).long()


@torch.no_grad()
def predict(model, x, bs=8):
    model.eval()
    return np.concatenate([model(to_t(x[i:i + bs]))["out"].argmax(1).numpy().astype(np.uint8)
                           for i in range(0, len(x), bs)])


def evaluate(pred, y):
    v = y != IGN
    iou = {}
    for c, nm in [(1, "설치가능지붕"), (2, "구조물")]:
        p, g = (pred == c) & v, (y == c) & v
        iou[nm] = (p & g).sum() / max((p | g).sum(), 1)
    # 이미지(=건물 묶음)별 설치 가능 면적 오차
    ga = ((y == 1) & v).sum((1, 2)) * PX_M2
    pa = ((pred == 1) & v).sum((1, 2)) * PX_M2
    ok = ga > 50
    err = np.abs(pa[ok] - ga[ok]) / ga[ok]
    # 비교: 구조물을 안 빼고 지붕 전체를 다 쓴다고 볼 때 오차
    ra = ((y > 0) & v).sum((1, 2)) * PX_M2
    base = np.abs(ra[ok] - ga[ok]) / ga[ok]
    return iou, float(np.median(err)), float(np.median(base)), int(ok.sum())


def overlay(img, m):
    col = np.array([[0, 0, 0], [60, 160, 255], [255, 220, 0]], np.uint8)
    o = img.copy()
    k = (m == 1) | (m == 2)
    o[k] = (0.55 * img[k] + 0.45 * col[m[k]]).astype(np.uint8)
    return o


def main():
    base, out = sys.argv[1], sys.argv[2]
    epochs = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    os.makedirs(out, exist_ok=True)
    torch.set_num_threads(os.cpu_count())
    torch.manual_seed(0)
    rng = np.random.default_rng(0)

    x, y, names = load(base, out)
    tr, va = split(names)
    print(f"images train {tr.sum()} / val {va.sum()}", flush=True)

    model = lraspp_mobilenet_v3_large(weights_backbone="IMAGENET1K_V1", num_classes=3)
    opt = torch.optim.AdamW(model.parameters(), 1e-3, weight_decay=1e-4)
    steps = int(epochs * (tr.sum() // 16))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=steps)
    w = torch.tensor([1.0, 1.0, 3.0])  # 구조물이 작아서 가중
    t0 = time.time()
    for ep in range(epochs):
        model.train(); tot = n = 0
        for xb, yb in batches(x[tr], y[tr], 16, 256, rng):
            loss = F.cross_entropy(model(xb)["out"], yb, weight=w, ignore_index=IGN)
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            tot += loss.item(); n += 1
        iou, err, base_err, k = evaluate(predict(model, x[va]), y[va])
        print(f"ep{ep + 1} loss {tot / n:.3f} IoU " + " ".join(f"{a} {b:.3f}" for a, b in iou.items())
              + f" | 면적오차 중앙값 {err:.1%} (구조물 안 뺄 때 {base_err:.1%}, n={k}) | {time.time() - t0:.0f}s",
              flush=True)
        torch.save(model.state_dict(), os.path.join(out, "roof_seg.pt"))

    pred = predict(model, x[va])
    vi = np.where(va)[0]
    for j in np.linspace(0, len(vi) - 1, 6).astype(int):
        i = vi[j]
        g = y[i].copy(); g[g == IGN] = 0
        p = pred[j].copy(); p[y[i] == IGN] = 0
        Image.fromarray(np.hstack([x[i], overlay(x[i], g), overlay(x[i], p)])).save(
            os.path.join(out, f"val_{names[i]}.png"))


if __name__ == "__main__":
    main()
