"""지붕 패널 배치 규칙 점검. 실행: python -m tests.test_roof_panel_layout"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from roof_seg_daejeon import align, layout, row_pitch, shade_loss


def test_row_pitch_daejeon_winter():
    # 동지 9시 기준 그림자: 약 2.2m 간격 (모듈 깊이 1.13m, 25도)
    assert 2.0 < row_pitch() < 2.4


def test_empty_square_roof():
    pred = np.ones((160, 160), np.uint8)  # 40m x 40m 평지붕
    rects = layout(pred)
    # 이격 0.5m 빼면 39m: 한 줄 17장(39/2.28), 줄 수 = 39m 안에 간격 2.2m로 17~18줄
    assert 17 * 17 <= len(rects) <= 17 * 18
    for x, y, w, h in rects:
        assert pred[y:y + h, x:x + w].all()


def test_structure_blocks_panels():
    pred = np.ones((160, 160), np.uint8)
    pred[60:100, 60:100] = 2  # 10m x 10m 옥탑
    assert len(layout(pred)) < len(layout(np.ones((160, 160), np.uint8)))
    for x, y, w, h in layout(pred):
        assert not (pred[y:y + h, x:x + w] == 2).any()


def test_tiny_roof_gets_nothing():
    assert layout(np.ones((16, 16), np.uint8)) == []  # 4m x 4m


def test_align_recovers_shift():
    roof = np.zeros((300, 300), np.uint8); roof[100:200, 80:220] = 1
    fp = np.roll(np.roll(roof, -22, 0), 15, 1)  # 경계가 5.5m 북쪽, 3.75m 동쪽으로 어긋남
    (dy, dx), fit = align(fp, roof)
    assert (dy, dx) == (22, -15) and fit > .99


def test_shade_open_roof_and_tall_neighbor():
    H = np.zeros((120, 120)); H[40:80, 40:80] = 10  # 10m 건물 하나, 1m 격자
    assert shade_loss(H, max_m=60)[60, 60] == 0  # 주변에 아무것도 없으면 안 가려짐
    H[82:90, 40:80] = 60  # 바로 남쪽에 60m 건물
    loss = shade_loss(H, max_m=60)
    assert loss[78, 60] > .5  # 남쪽 가장자리는 대부분 가려짐
    assert loss[78, 60] > loss[42, 60]  # 남쪽 건물에서 멀수록 덜 가려짐


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
