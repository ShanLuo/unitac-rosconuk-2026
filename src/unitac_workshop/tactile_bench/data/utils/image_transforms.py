from __future__ import division, print_function, unicode_literals

import numpy as np
import cv2
import skimage
from skimage.util import random_noise
from scipy import ndimage


def apply(image, channel_mode=None, crop=None, dims=None, stdiz=False,
          normlz=False, binary_threshold=None, circle_mask_radius=None,
          blur_ksize=1, morphology_ksize=1,
          circle_mask_offset=None, **kwargs):
    """ Transform image in various ways. """
    if channel_mode:
        if channel_mode == "gray":
            if image.ndim == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[..., np.newaxis]
            elif image.ndim == 2:
                image = image[..., np.newaxis]
        elif channel_mode in ["red", "green", "blue"]:
            channel_map = {"blue": 0, "green": 1, "red": 2}
            channel_idx = channel_map[channel_mode]
            image = image[:, :, channel_idx][..., np.newaxis]

    if crop:
        h, w = image.shape[:2]
        if len(crop) == 4:
            x0, y0, x1, y1 = crop
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(w, x1), min(h, y1)
            image = image[y0:y1, x0:x1]
        elif len(crop) == 3:
            cx, cy, r = crop
            x0, x1 = cx - r, cx + r
            y0, y1 = cy - r, cy + r
            size = x1 - x0
            src_x0, src_x1 = max(0, x0), min(w, x1)
            src_y0, src_y1 = max(0, y0), min(h, y1)
            dst_x0 = src_x0 - x0
            dst_y0 = src_y0 - y0
            canvas = np.zeros((size, size, image.shape[2]), dtype=image.dtype)
            canvas[dst_y0:dst_y0 + (src_y1 - src_y0),
                   dst_x0:dst_x0 + (src_x1 - src_x0)] = image[src_y0:src_y1, src_x0:src_x1]
            image = canvas

    if dims:
        image = cv2.resize(image, tuple(dims), interpolation=cv2.INTER_AREA)
        if image.ndim < 3:
            image = image[..., np.newaxis]
    if blur_ksize and blur_ksize > 1:
        image = cv2.GaussianBlur(image, (blur_ksize, blur_ksize), 0)
    if binary_threshold:
        image = threshold_image(image, *binary_threshold)[..., np.newaxis]
    if morphology_ksize and morphology_ksize > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morphology_ksize, morphology_ksize))
        image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    if stdiz:
        image = per_image_standardisation(image.astype(np.float32))
    if normlz:
        image = image.astype(np.float32) / 255.0
    if circle_mask_radius:
        if not circle_mask_offset:
            circle_mask_offset = (0, 0)
        image = apply_circle_mask(image, circle_mask_radius, circle_mask_offset)
    return image


def augment_image(image, rshift=None, rzoom=None, brightlims=None,
                  noise_var=None, **kwargs):
    """ Augment image in various ways. """
    if rshift:
        image = random_shift_image(image, *rshift)
    if rzoom:
        image = random_zoom_image(image, rzoom)
    if brightlims:
        image = random_image_brightness(image, brightlims)
    if noise_var:
        image = random_image_noise(image, noise_var)
    return image


def threshold_image(image, block_size=11, offset=-5):
    return cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        block_size, offset
    )


def detect_circles(edges, radii=np.arange(3, 10, 1), min_center_dist=None,
                   target_n=1, init_thr_ratio=0.5):
    hres = skimage.transform.hough_circle(edges, radii)
    max_acc = np.max(hres)
    thr_ratio = init_thr_ratio
    if min_center_dist is None:
        min_center_dist = 2 * radii.min()
    accums, cx, cy, rs = skimage.transform.hough_circle_peaks(
        hres, radii, total_num_peaks=500,
        min_xdistance=int(min_center_dist), min_ydistance=int(min_center_dist),
        threshold=thr_ratio * max_acc, normalize=True,
    )
    if len(cx) == 0:
        return np.array([]), np.array([]), np.array([]), np.array([])
    if len(cx) >= target_n:
        order = np.argsort(-accums)[:target_n]
        return cx[order], cy[order], rs[order], accums[order]
    return cx, cy, rs, accums


def get_circle_mask(image, min_radii, max_radii, scale):
    sk_frame = skimage.img_as_float(image)
    edges = skimage.feature.canny(sk_frame, sigma=2.0)
    outline_radii_range = np.arange(min_radii, max_radii, 1)
    outline_cx, outline_cy, outline_radii, acc = detect_circles(
        edges, radii=outline_radii_range, target_n=1, min_center_dist=6
    )
    print(f"original outline circle x:{outline_cx} y:{outline_cy} r:{outline_radii}")
    return (outline_cx[0], outline_cy[0], round(outline_radii[0] * scale))


def apply_circle_mask(image, radius=110, circle_mask_offset=(0, 0)):
    hh, ww = image.shape[:2]
    hc, wc = hh // 2 + circle_mask_offset[0], ww // 2 + circle_mask_offset[1]
    mask = np.zeros((hh, ww), dtype=np.uint8)
    cv2.circle(mask, (hc, wc), radius, 255, thickness=-1)
    return cv2.bitwise_and(image, image, mask=mask)


def random_image_brightness(image, brightlims):
    if image.dtype != np.uint8:
        raise ValueError('Only applies to uint8 images on a 0-255 scale')
    a1, a2, b1, b2 = brightlims
    alpha, beta = np.random.uniform(a1, a2), np.random.randint(b1, b2)
    return np.clip(alpha*image + beta, 0, 255).astype(np.uint8)


def random_image_noise(image, noise_var):
    return (random_noise(image, var=noise_var) * 255).astype(np.uint8)


def per_image_standardisation(image):
    mean = np.mean(image, axis=(0, 1), keepdims=True)
    std = np.sqrt(((image - mean)**2).mean(axis=(0, 1), keepdims=True))
    return (image - mean) / (std+1e-6)


def random_shift_image(x, wrg, hrg, fill_mode='nearest', cval=0.):
    h, w = x.shape[0], x.shape[1]
    tx, ty = np.random.uniform(-hrg, hrg) * h, np.random.uniform(-wrg, wrg) * w
    return apply_affine_transform(x, tx=tx, ty=ty, fill_mode=fill_mode, cval=cval)


def random_zoom_image(x, zoom_range, fill_mode='nearest', cval=0.):
    if len(zoom_range) != 2:
        raise ValueError('`zoom_range` should be a tuple or list of two floats. Received: %s' % (zoom_range,))
    zx, zy = (1, 1) if zoom_range[0] == 1 and zoom_range[1] == 1 else np.random.uniform(
        zoom_range[0], zoom_range[1], 2)
    return apply_affine_transform(x, zx=zx, zy=zy, fill_mode=fill_mode, cval=cval)


def apply_affine_transform(x, theta=0, tx=0, ty=0, zx=1, zy=1,
                           fill_mode='nearest', cval=0.):
    transform_matrix = None
    if tx != 0 or ty != 0:
        shift_matrix = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]])
        transform_matrix = shift_matrix if transform_matrix is None else np.dot(transform_matrix, shift_matrix)
    if zx != 1 or zy != 1:
        zoom_matrix = np.array([[zx, 0, 0], [0, zy, 0], [0, 0, 1]])
        transform_matrix = zoom_matrix if transform_matrix is None else np.dot(transform_matrix, zoom_matrix)
    if transform_matrix is not None:
        h, w = x.shape[0], x.shape[1]
        transform_matrix = transform_matrix_offset_center(transform_matrix, h, w)
        x = np.rollaxis(x, 2, 0)
        final_affine_matrix = transform_matrix[:2, :2]
        final_offset = transform_matrix[:2, 2]
        channel_images = [ndimage.interpolation.affine_transform(
            x_channel, final_affine_matrix, final_offset, order=1,
            mode=fill_mode, cval=cval) for x_channel in x]
        x = np.stack(channel_images, axis=0)
    return np.rollaxis(x, 0, 3)


def rotate_image(image, angle_deg):
    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(image, M, (h, w))


def transform_matrix_offset_center(matrix, x, y):
    o_x, o_y = float(x) / 2 + 0.5, float(y) / 2 + 0.5
    offset_matrix = np.array([[1, 0, o_x], [0, 1, o_y], [0, 0, 1]])
    reset_matrix = np.array([[1, 0, -o_x], [0, 1, -o_y], [0, 0, 1]])
    return np.dot(np.dot(offset_matrix, matrix), reset_matrix)


def bbox_circular_to_triangular(bb):
    """From (cx, cy, r) to (x0, y0, x1, y1)"""
    return [bb[0] - bb[2], bb[1] - bb[2], bb[0] + bb[2], bb[1] + bb[2]]


def combine_bbox(image_params_1, image_params_2):
    """Combine bounding boxes from two sets of image parameters."""
    b1 = image_params_1.get("bbox", [0, 0, 0, 0])
    b2 = image_params_2.get("bbox", [0, 0, 0, 0])
    b1 = bbox_circular_to_triangular(b1) if len(b1) == 3 else b1
    b2 = bbox_circular_to_triangular(b2) if len(b2) == 3 else b2
    return [int(b) for b in [b1[0] + b2[0], b1[1] + b2[1],
                             b1[0] + b2[2], b1[1] + b2[3]]]


def camera_loop(camera, image_processing_kwargs,
                display_name='processed_image', display_size=(640, 480)):
    cv2.namedWindow(display_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(display_name, *display_size)
    while True:
        image = camera.process()
        processed_image = apply(image, **image_processing_kwargs)
        cv2.imshow(display_name, processed_image)
        if cv2.waitKey(10) == 27:
            break


if __name__ == '__main__':
    from unitac_workshop.tactile_bench.data.utils.sensors import RealSensor
    sensor_params = {'source': 1}
    camera = RealSensor(sensor_params)
    image_processing_params = {
        'channel_mode': 'gray', 'bbox': None, 'dims': None, 'stdiz': False,
        'normlz': False, 'thresh': [11, -30], 'circle_mask_radius': None}
    camera_loop(camera, image_processing_params)
