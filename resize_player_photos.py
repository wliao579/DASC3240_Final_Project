import argparse
from pathlib import Path

import cv2


def resize_image(in_path, out_path, size, keep_aspect):
    image = cv2.imread(str(in_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        return False

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if keep_aspect:
        h, w = image.shape[:2]
        if h == 0 or w == 0:
            return False
        scale = min(size / w, size / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Pad to a square canvas
        if resized.shape[2] == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2BGRA)
            resized[:, :, 3] = 255
        canvas = (0, 0, 0, 0)
        final = cv2.copyMakeBorder(
            resized,
            top=(size - new_h) // 2,
            bottom=size - new_h - (size - new_h) // 2,
            left=(size - new_w) // 2,
            right=size - new_w - (size - new_w) // 2,
            borderType=cv2.BORDER_CONSTANT,
            value=canvas,
        )
    else:
        final = cv2.resize(image, (size, size), interpolation=cv2.INTER_AREA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    return cv2.imwrite(str(out_path), final)


def main():
    parser = argparse.ArgumentParser(description="Resize all player photos to a uniform resolution.")
    parser.add_argument("--input-dir", default="player_photos", help="Folder with original images")
    parser.add_argument("--output-dir", default="player_photos_resized", help="Folder for resized images")
    parser.add_argument("--size", type=int, default=256, help="Output size in pixels (square)")
    parser.add_argument(
        "--keep-aspect",
        action="store_true",
        help="Preserve aspect ratio and pad to a square",
    )
    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    exts = {".jpg", ".jpeg", ".png", ".bmp"}

    count = 0
    for path in sorted(in_dir.iterdir()):
        if path.suffix.lower() not in exts:
            continue
        out_path = out_dir / path.name
        ok = resize_image(path, out_path, args.size, args.keep_aspect)
        if ok:
            count += 1

    print(f"Processed {count} images into {out_dir}")


if __name__ == "__main__":
    main()
