"""Watch a camera feed and exit 0 once a configured region matches a reference image.

Meant to be used as a trigger/gate step in a larger script: point it at a
webcam or RTSP stream, tell it which rectangle of the frame to watch and what
image it should eventually match, and it blocks until that happens (or times
out). No GUI is required -- pass --no-gui to run it headless.

Exit codes:
    0   region matched the reference image (threshold reached)
    1   timed out before matching
    2   configuration or camera/image error
    130 interrupted (Ctrl+C, or 'q'/Esc in the preview window)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

import cv2
from skimage.metrics import structural_similarity


class ConfigError(Exception):
    pass


def load_config(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {exc}")

    for key in ("source", "region", "reference_image", "threshold"):
        if key not in raw:
            raise ConfigError(f"Config is missing required field: {key}")

    region = raw["region"]
    for key in ("x", "y", "width", "height"):
        if key not in region:
            raise ConfigError(f"Config 'region' is missing field: {key}")

    raw.setdefault("timeout", None)
    raw.setdefault("poll_interval", 0.5)
    return raw


def _check_source_is_playable(source: Any) -> None:
    # The most common mistake: pasting a go2rtc (or similar) browser preview
    # page instead of a real stream URL. It's HTML+JS, not decodable video,
    # so fail early with a pointer to the actual endpoint instead of a
    # generic "could not open" error from deep inside FFmpeg.
    if not isinstance(source, str) or "stream.html" not in source:
        return
    parsed = urlparse(source)
    src = parse_qs(parsed.query).get("src", [None])[0]
    suggestion = f"rtsp://{parsed.hostname}:8554/{src}" if parsed.hostname and src else None
    hint = f" Try: \"{suggestion}\"" if suggestion else ""
    raise ConfigError(
        f"{source} looks like a go2rtc (or similar) browser preview page, "
        f"not a raw stream -- OpenCV can't decode HTML/JS.{hint}"
    )


def open_capture(source: Any) -> cv2.VideoCapture:
    _check_source_is_playable(source)
    # A numeric-looking source (webcam index) comes through as int from JSON
    # already; an RTSP/HTTP URL stays a string. cv2.VideoCapture accepts both.
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise ConfigError(f"Could not open video source: {source}")
    return cap


def load_reference(path: Path):
    image = cv2.imread(str(path))
    if image is None:
        raise ConfigError(f"Could not load reference image: {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def crop_region(frame, region: Dict[str, int]):
    x, y, w, h = region["x"], region["y"], region["width"], region["height"]
    frame_h, frame_w = frame.shape[:2]
    x = max(0, min(x, frame_w - 1))
    y = max(0, min(y, frame_h - 1))
    w = max(1, min(w, frame_w - x))
    h = max(1, min(h, frame_h - y))
    return frame[y : y + h, x : x + w]


def compare_to_reference(crop, reference_gray) -> float:
    crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ref_h, ref_w = reference_gray.shape[:2]
    if crop_gray.shape != reference_gray.shape:
        crop_gray = cv2.resize(crop_gray, (ref_w, ref_h))
    score, _ = structural_similarity(crop_gray, reference_gray, full=True)
    return score


def run(config: Dict[str, Any], no_gui: bool) -> int:
    region = config["region"]
    threshold = float(config["threshold"])
    timeout = config["timeout"]
    poll_interval = float(config["poll_interval"])

    reference_gray = load_reference(Path(config["reference_image"]))
    cap = open_capture(config["source"])

    window_name = "camtrigger"
    start = time.monotonic()
    try:
        while True:
            if timeout is not None and time.monotonic() - start >= timeout:
                print(f"Timed out after {timeout}s without reaching threshold {threshold}")
                return 1

            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from video source", file=sys.stderr)
                return 2

            crop = crop_region(frame, region)
            score = compare_to_reference(crop, reference_gray)
            print(f"score={score:.4f} threshold={threshold}")

            if not no_gui:
                x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(
                    frame, f"score: {score:.4f}", (x, max(0, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
                )
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):  # 'q' or Esc
                    print("Aborted from preview window")
                    return 130

            if score >= threshold:
                print(f"Threshold reached: score={score:.4f} >= {threshold}")
                return 0

            if no_gui and poll_interval > 0:
                time.sleep(poll_interval)
    finally:
        cap.release()
        if not no_gui:
            cv2.destroyAllWindows()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Watch a camera feed and exit 0 once a region matches a reference image."
    )
    parser.add_argument("--config", required=True, help="Path to the JSON config file")
    parser.add_argument(
        "--no-gui", action="store_true", help="Run headless: no preview window, no keyboard abort"
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        return run(config, no_gui=args.no_gui)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
