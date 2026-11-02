"""지붕 패널 배치 규칙 점검. 실행: python -m tests.test_roof_panel_layout"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from roof_seg_daejeon import layout, row_pitch


def test_row_pitch_daejeon_winter():
    # 동지 9시 기준 그림자: 약 2.2m 간격 (모듈 깊이 1.13m, 25도)
    assert 2.0 < row_pitch() < 2.4


def test_empty_square_roof():
    pred = np.ones((160, 160), np.uint8)  # 40m x 40m 평지붕
    rects = layout(pred)
    # 이격 1m 빼면 38m: 한 줄 16장(38/2.28), 줄 수 = 38m 안에 간격 2.2m로 17~18줄
    assert 16 * 17 <= len(rects) <= 16 * 18
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
