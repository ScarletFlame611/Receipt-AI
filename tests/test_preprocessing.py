import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from src.data.preprocessing import to_grayscale, denoise, binarize, preprocess
from src.data.perspective import order_points, four_point_transform, detect_and_warp


def make_color_image(h=200, w=150):
    return np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)


def test_to_grayscale_reduces_channels():
    img = make_color_image()
    gray = to_grayscale(img)
    assert gray.ndim == 2
    assert gray.shape == (200, 150)


def test_to_grayscale_idempotent_on_gray():
    gray = np.zeros((50, 50), dtype=np.uint8)
    assert to_grayscale(gray).ndim == 2


def test_denoise_preserves_shape():
    gray = np.full((100, 100), 128, dtype=np.uint8)
    assert denoise(gray).shape == gray.shape


def test_binarize_returns_two_values():
    gray = make_color_image()[:, :, 0]
    result = binarize(gray)
    assert set(np.unique(result)).issubset({0, 255})


def test_preprocess_grayscale_level():
    img = make_color_image()
    out = preprocess(img, level="grayscale")
    assert out.ndim == 2


def test_preprocess_binary_level():
    img = make_color_image()
    out = preprocess(img, level="binary")
    assert set(np.unique(out)).issubset({0, 255})


def test_preprocess_unknown_level_raises():
    img = make_color_image()
    with pytest.raises(ValueError):
        preprocess(img, level="bogus")


def test_order_points_orders_corners():
    pts = np.array([[10, 10], [100, 12], [98, 90], [8, 88]], dtype="float32")
    rect = order_points(pts)
    assert rect[0].sum() <= rect[2].sum()


def test_four_point_transform_output_shape():
    img = make_color_image(300, 300)
    pts = np.array([[20, 20], [260, 30], [250, 270], [10, 260]], dtype="float32")
    warped = four_point_transform(img, pts)
    assert warped.ndim == 3
    assert warped.shape[0] > 0 and warped.shape[1] > 0


def test_detect_and_warp_returns_tuple():
    img = make_color_image()
    result, found = detect_and_warp(img)
    assert isinstance(found, bool)
    assert result.ndim == 3


def test_detect_and_warp_no_crash_on_blank():
    blank = np.full((200, 150, 3), 255, dtype=np.uint8)
    result, found = detect_and_warp(blank)
    assert found is False