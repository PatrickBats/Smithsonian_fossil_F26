import cv2
import numpy as np
LOG_KERNEL_SIZE=5
def laplacian_of_gaussian(gray: np.ndarray, k: int=LOG_KERNEL_SIZE) -> np.ndarray:
    """Compute Laplacian of Gaussian for a 2D image.

    Args:
        gray: The grayscale image to compute the Laplacian of Gaussian for.
        k: The kernel size for the Gaussian blur.

    Returns:
        The Laplacian of Gaussian for the image.
    """
    blurred = cv2.GaussianBlur(gray, (k, k), 0)
    return cv2.Laplacian(blurred, cv2.CV_64F, ksize=k)

def _to_gray_stack(tile_zfirst: np.ndarray) -> np.ndarray:
    """Convert (z, h, w, c) tile data into a grayscale stack (z, h, w).

    Args:
        tile_zfirst: The tile data to convert into a grayscale stack.

    Returns:
        The grayscale stack.
    """
    z, h, w, _ = tile_zfirst.shape
    gray_stack = np.zeros((z, h, w), dtype=np.uint8)
    for zi in range(z):
        img = tile_zfirst[zi].astype(np.uint8) if tile_zfirst[zi].dtype != np.uint8 else tile_zfirst[zi]
        gray_stack[zi] = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return gray_stack

def focus_stack(tile: np.ndarray, k: int=LOG_KERNEL_SIZE) -> tuple[np.ndarray, np.ndarray]:
    """Focus stack a tile of shape (h, w, c, z) to (h, w, c).

    Args:
        tile: The tile data to focus stack.
        k: The kernel size for the Gaussian blur.

    Returns:
        stacked: Focus-stacked RGB image.
        avg_logs: Per-z average absolute LoG response used for LoG ranking.
    """
    tile_zfirst = np.moveaxis(tile, -1, 0)
    z, h, w, c = tile_zfirst.shape
    gray_stack = _to_gray_stack(tile_zfirst)
    log_stack = np.array([laplacian_of_gaussian(gray_stack[zi], k) for zi in range(z)])
    log_abs = np.abs(log_stack)
    avg_logs = log_abs.mean(axis=(1, 2))
    best_z = np.argmax(log_abs, axis=0)
    row_idx = np.arange(h)[:, None]
    col_idx = np.arange(w)[None, :]
    stacked = np.zeros((h, w, c), dtype=tile_zfirst.dtype)
    for ch in range(c):
        channel_stack = tile_zfirst[..., ch]
        stacked[..., ch] = channel_stack[best_z, row_idx, col_idx]
    return (stacked, avg_logs)
