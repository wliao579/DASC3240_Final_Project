import argparse
import os
from pathlib import Path

import cv2


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def load_detector():
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_fullbody.xml")
    return cv2.CascadeClassifier(cascade_path)


def detect_largest_box(detector, image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    boxes = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40)
    )
    if len(boxes) > 0:
        # Choose the largest box by area
        return max(boxes, key=lambda f: f[2] * f[3])
    return None


def square_crop_from_box(image_bgr, box, padding_ratio):
    x, y, w, h = box
    h_img, w_img = image_bgr.shape[:2]

    # Center on box, expand to a square with padding
    cx = x + w / 2.0
    cy = y + h / 2.0
    box_size = max(w, h) * (1.0 + padding_ratio)
    half = box_size / 2.0

    left = int(round(cx - half))
    right = int(round(cx + half))
    top = int(round(cy - half))
    bottom = int(round(cy + half))

    # Clamp to image boundaries
    left = max(left, 0)
    top = max(top, 0)
    right = min(right, w_img)
    bottom = min(bottom, h_img)

    return image_bgr[top:bottom, left:right]


def center_square_crop(image_bgr):
    h, w = image_bgr.shape[:2]
    size = min(h, w)
    top = (h - size) // 2
    left = (w - size) // 2
    return image_bgr[top:top + size, left:left + size]


def process_image(detector, in_path, out_path, size, padding_ratio):
    image = cv2.imread(str(in_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        return False

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.shape[2] == 4:
        # Convert BGRA to BGR for face detection, keep alpha for later
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        alpha = image[:, :, 3]
    else:
        bgr = image
        alpha = None

    box = detect_largest_box(detector, bgr)
    if box is not None:
        cropped = square_crop_from_box(bgr, box, padding_ratio)
    else:
        cropped = center_square_crop(bgr)

    resized = cv2.resize(cropped, (size, size), interpolation=cv2.INTER_AREA)

    if alpha is not None:
        # Resize alpha channel to match and re-attach
        alpha_resized = cv2.resize(alpha, (size, size), interpolation=cv2.INTER_AREA)
        resized = cv2.cvtColor(resized, cv2.COLOR_BGR2BGRA)
        resized[:, :, 3] = alpha_resized

    ensure_dir(out_path.parent)
    return cv2.imwrite(str(out_path), resized)


def main():
    parser = argparse.ArgumentParser(description="Crop player photos to full body and resize to a uniform square.")
    parser.add_argument("--input-dir", default="player_photos", help="Folder with original images")
    parser.add_argument("--output-dir", default="player_photos_resized", help="Folder for resized images")
    parser.add_argument("--size", type=int, default=256, help="Output size in pixels (square)")
    parser.add_argument("--padding", type=float, default=0.2, help="Padding ratio around detected box")
    args = parser.parse_args()

    detector = load_detector()
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    count = 0

    for path in sorted(in_dir.iterdir()):
        if path.suffix.lower() not in exts:
            continue
        out_path = out_dir / path.name
        ok = process_image(detector, path, out_path, args.size, args.padding)
        if ok:
            count += 1

    print(f"Processed {count} images into {out_dir}")


if __name__ == "__main__":
    main()
