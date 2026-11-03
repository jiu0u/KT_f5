"""대전 정답 라벨(roof_label_tool.html)로 지붕 AI 평가.

python -I scripts/roof_label_eval.py guide <label 폴더>                  # 라벨링 도구용 경계선 _fp.png 생성
python -I scripts/roof_label_eval.py eval <label 폴더> <roof_labels.json>  # 정답 vs AI
"""
import glob, json, os, sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from roof_seg_daejeon import KW_M2, MOD_D, MOD_W, layout

PX_M2 = 0.25 ** 2


def guide(d):
    for f in glob.glob(os.path.join(d, "*.npz")):
        fp = np.load(f)["fp"]
        rgba = np.zeros(fp.shape + (4,), np.uint8)
        cnts, _ = cv2.findContours(fp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(rgba, cnts, -1, (255, 40, 40, 255), 1)
        Image.fromarray(rgba).save(f[:-4] + "_fp.png")


def rasterize(lab, shape):
    m = np.zeros(shape, np.uint8)
    for g in sorted(lab["polygons"], key=lambda g: g["cls"]):  # 장애물이 지붕 위에 덮이게
        cv2.fillPoly(m, [np.round(np.array(g["points"])).astype(np.int32)], g["cls"])
    return m


def compare(gt, pred, zone):
    # 정답은 경계선 밖이어도 그대로 셈(경계가 어긋난 건물). AI는 파이프라인대로 경계 근처만.
    pred = np.where(zone > 0, pred, 0)
    iou = lambda c: ((gt == c) & (pred == c)).sum() / max(((gt == c) | (pred == c)).sum(), 1)
    ng, na = len(layout(gt)), len(layout(pred))
    return dict(iou_roof=iou(1), iou_obs=iou(2), roof_gt_m2=(gt == 1).sum() * PX_M2,
                roof_ai_m2=(pred == 1).sum() * PX_M2, panels_gt=ng, panels_ai=na,
                kw_gt=ng * MOD_W * MOD_D * KW_M2, kw_ai=na * MOD_W * MOD_D * KW_M2)


def evaluate(d, labels_path):
    labels = json.load(open(labels_path, encoding="utf-8"))
    rows = []
    for name, lab in sorted(labels.items()):
        if not lab["polygons"]:
            continue
        z = np.load(os.path.join(d, name + ".npz"))
        r = compare(rasterize(lab, z["pred"].shape), z["pred"], z["zone"])
        r["fp_m2"] = z["fp"].sum() * PX_M2
        rows.append((name, r))
        print(f"{name}: 지붕 IoU {r['iou_roof']:.2f} 장애물 IoU {r['iou_obs']:.2f} | "
              f"패널 정답 {r['panels_gt']} / AI {r['panels_ai']} ({r['kw_gt']:.0f} / {r['kw_ai']:.0f}kW) | "
              f"25% 가정 {r['fp_m2'] * .25 * KW_M2:.0f}kW")
    if not rows:
        print("라벨 없음"); return
    kg = sum(r["kw_gt"] for _, r in rows)
    ka = sum(r["kw_ai"] for _, r in rows)
    k25 = sum(r["fp_m2"] * .25 * KW_M2 for _, r in rows)
    e_ai = [abs(r["kw_ai"] - r["kw_gt"]) / r["kw_gt"] for _, r in rows if r["kw_gt"] > 0]
    e_25 = [abs(r["fp_m2"] * .25 * KW_M2 - r["kw_gt"]) / r["kw_gt"] for _, r in rows if r["kw_gt"] > 0]
    print(f"\n{len(rows)}곳 | 지붕 IoU 평균 {np.mean([r['iou_roof'] for _, r in rows]):.2f} | "
          f"합계 정답 {kg:.0f}kW, AI {ka:.0f}kW, 25% 가정 {k25:.0f}kW")
    if e_ai:
        print(f"건물별 용량 오차 중앙값: AI {np.median(e_ai):.0%} vs 25% 가정 {np.median(e_25):.0%}")


def _check():
    # AI 예측을 그대로 정답으로 주면 IoU 1, 패널 수 같아야 함
    pred = np.zeros((200, 200), np.uint8); pred[20:180, 20:180] = 1; pred[80:110, 80:110] = 2
    lab = {"polygons": [{"cls": 1, "points": [[20, 20], [179, 20], [179, 179], [20, 179]]},
                        {"cls": 2, "points": [[80, 80], [109, 80], [109, 109], [80, 109]]}]}
    r = compare(rasterize(lab, pred.shape), pred, np.ones_like(pred))
    assert r["iou_roof"] > .97 and r["iou_obs"] > .9 and abs(r["panels_gt"] - r["panels_ai"]) <= 2, r
    print("ok")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"guide": lambda: guide(sys.argv[2]), "eval": lambda: evaluate(sys.argv[2], sys.argv[3]),
     "check": _check}[cmd]()
