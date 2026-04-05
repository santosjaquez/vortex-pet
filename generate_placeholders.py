#!/usr/bin/env python3
"""Generate placeholder PNG sprites for Vortex desktop pet.

Creates simple axolotl drawings using QPainter so the pet can be tested
without real artwork.  Run once from the repo root:

    python generate_placeholders.py
"""

import json
import math
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QRect, QRectF
from PyQt6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication

# ── Paths ───────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "vortex" / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
META_PATH = ASSETS_DIR / "sprites.json"

SIZE = 128  # px, square
ICON_SIZE = 64

# ── Colour palette ──────────────────────────────────────────────────

COLORS: dict[str, str] = {
    "idle": "#FF69B4",
    "walk": "#FF69B4",
    "sleep": "#E6E6FA",
    "happy": "#FF1493",
    "sad": "#87CEEB",
    "typing": "#FF69B4",
    "petted": "#FF1493",
    "confused": "#FF69B4",
    "celebrate": "#FFD700",
    "fall": "#FF69B4",
}

# ── Drawing helpers ─────────────────────────────────────────────────


def _draw_body(p: QPainter, colour: QColor, cx: int, cy: int, tilt: float = 0.0):
    """Draw the main rounded body ellipse, optionally tilted."""
    p.save()
    p.translate(cx, cy)
    if tilt:
        p.rotate(tilt)
    p.setBrush(colour)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRect(-24, -20, 48, 40))
    p.restore()


def _draw_eyes_open(p: QPainter, cx: int, cy: int):
    """Two small black dot eyes."""
    p.setBrush(QColor("black"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPoint(cx - 8, cy - 6), 3, 3)
    p.drawEllipse(QPoint(cx + 8, cy - 6), 3, 3)


def _draw_eyes_closed(p: QPainter, cx: int, cy: int):
    """Eyes as horizontal lines (sleeping)."""
    pen = QPen(QColor("black"), 2)
    p.setPen(pen)
    p.drawLine(cx - 11, cy - 6, cx - 5, cy - 6)
    p.drawLine(cx + 5, cy - 6, cx + 11, cy - 6)


def _draw_eyes_happy(p: QPainter, cx: int, cy: int):
    """^_^ shaped eyes."""
    pen = QPen(QColor("black"), 2)
    p.setPen(pen)
    # Left eye: small inverted V
    p.drawLine(cx - 11, cy - 4, cx - 8, cy - 8)
    p.drawLine(cx - 8, cy - 8, cx - 5, cy - 4)
    # Right eye
    p.drawLine(cx + 5, cy - 4, cx + 8, cy - 8)
    p.drawLine(cx + 8, cy - 8, cx + 11, cy - 4)


def _draw_eyes_sad(p: QPainter, cx: int, cy: int):
    """Downward arcs for sad eyes."""
    pen = QPen(QColor("black"), 2)
    p.setPen(pen)
    p.drawArc(QRect(cx - 12, cy - 10, 8, 6), 0, -180 * 16)
    p.drawArc(QRect(cx + 4, cy - 10, 8, 6), 0, -180 * 16)


def _draw_smile(p: QPainter, cx: int, cy: int):
    """Small smile arc."""
    pen = QPen(QColor("black"), 1.5)
    p.setPen(pen)
    p.drawArc(QRect(cx - 5, cy - 2, 10, 8), 0, -180 * 16)


def _draw_gills(p: QPainter, cx: int, cy: int, phase: float):
    """Three gill branches on each side, animated by phase (0-1)."""
    pen = QPen(QColor("#FF1493"), 2)
    p.setPen(pen)
    for side in (-1, 1):
        base_x = cx + side * 24
        for i, angle_base in enumerate([-30, 0, 30]):
            angle = angle_base + math.sin(phase * math.pi * 2 + i) * 8
            rad = math.radians(angle)
            length = 14
            dx = side * length * math.cos(rad)
            dy = -length * math.sin(rad)
            p.drawLine(
                int(base_x),
                int(cy - 10 + i * 4),
                int(base_x + dx),
                int(cy - 10 + i * 4 + dy),
            )


def _draw_legs(p: QPainter, cx: int, cy: int, left_up: bool = False, right_up: bool = False):
    """Four tiny leg rectangles at the bottom of the body."""
    p.setBrush(QColor("#FF69B4"))
    p.setPen(Qt.PenStyle.NoPen)
    offsets = [(-16, 0), (-6, 0), (6, 0), (16, 0)]
    for idx, (ox, _) in enumerate(offsets):
        y_off = cy + 16
        if idx < 2 and left_up:
            y_off -= 3
        elif idx >= 2 and right_up:
            y_off -= 3
        p.drawRect(cx + ox - 3, y_off, 6, 6)


def _draw_text_above(p: QPainter, cx: int, cy: int, text: str, colour: QColor):
    """Draw short text centred above the character."""
    p.setPen(QPen(colour, 1))
    font = QFont("sans-serif", 11, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(QRect(cx - 30, cy - 42, 60, 18), Qt.AlignmentFlag.AlignCenter, text)


def _draw_hearts(p: QPainter, cx: int, cy: int, count: int = 3):
    """Draw small red hearts above the character."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("red"))
    for i in range(count):
        hx = cx - 20 + i * 20
        hy = cy - 38 + (i % 2) * 6
        path = QPainterPath()
        path.moveTo(hx, hy + 3)
        path.cubicTo(hx - 5, hy - 3, hx - 5, hy + 6, hx, hy + 10)
        path.cubicTo(hx + 5, hy + 6, hx + 5, hy - 3, hx, hy + 3)
        p.drawPath(path)


def _draw_cheeks(p: QPainter, cx: int, cy: int):
    """Rosy cheek circles."""
    p.setBrush(QColor(255, 100, 100, 100))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPoint(cx - 14, cy + 2), 5, 3)
    p.drawEllipse(QPoint(cx + 14, cy + 2), 5, 3)


def _draw_sparkles(p: QPainter, cx: int, cy: int, phase: float):
    """Small star / sparkle shapes around the character."""
    pen = QPen(QColor("#FFD700"), 2)
    p.setPen(pen)
    for i in range(5):
        angle = (i / 5) * 360 + phase * 360
        r = 32 + math.sin(phase * math.pi * 2 + i) * 6
        sx = cx + r * math.cos(math.radians(angle))
        sy = cy + r * math.sin(math.radians(angle))
        size = 4
        p.drawLine(int(sx - size), int(sy), int(sx + size), int(sy))
        p.drawLine(int(sx), int(sy - size), int(sx), int(sy + size))


# ── Frame generators per animation ─────────────────────────────────


def _gen_idle(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    bounce = int(2.5 * math.sin(frame / total * math.pi * 2))
    cy += bounce
    _draw_body(p, colour, cx, cy)
    _draw_eyes_open(p, cx, cy)
    _draw_smile(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)


def _gen_walk(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    tilt = 5 * math.sin(frame / total * math.pi * 2)
    left_up = frame % 2 == 0
    _draw_body(p, colour, cx, cy, tilt=tilt)
    _draw_eyes_open(p, cx, cy)
    _draw_smile(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy, left_up=left_up, right_up=not left_up)


def _gen_sleep(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2 + 2
    _draw_body(p, colour, cx, cy)
    _draw_eyes_closed(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)
    # Zzz
    z_count = (frame % 3) + 1
    _draw_text_above(p, cx + 10, cy - 4, "Z" * z_count, QColor("#6A5ACD"))


def _gen_happy(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    bounce = -int(5 * abs(math.sin(frame / total * math.pi)))
    cy += bounce
    _draw_body(p, colour, cx, cy)
    _draw_eyes_happy(p, cx, cy)
    _draw_smile(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)


def _gen_sad(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2 + 3  # droops
    _draw_body(p, colour, cx, cy)
    _draw_eyes_sad(p, cx, cy)
    # Frown
    pen = QPen(QColor("black"), 1.5)
    p.setPen(pen)
    p.drawArc(QRect(cx - 5, cy + 2, 10, 8), 0, 180 * 16)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)


def _gen_typing(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    _draw_body(p, colour, cx, cy)
    _draw_eyes_open(p, cx, cy)
    _draw_smile(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    # Arms / typing motion
    arm_up = frame % 2 == 0
    p.setBrush(colour)
    p.setPen(Qt.PenStyle.NoPen)
    left_y = cy + 12 if arm_up else cy + 16
    right_y = cy + 16 if arm_up else cy + 12
    p.drawRect(cx - 20, left_y, 8, 5)
    p.drawRect(cx + 12, right_y, 8, 5)
    _draw_legs(p, cx, cy)


def _gen_petted(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    _draw_body(p, colour, cx, cy)
    _draw_eyes_happy(p, cx, cy)
    _draw_smile(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)
    _draw_cheeks(p, cx, cy)
    _draw_hearts(p, cx, cy, count=min(frame + 1, 3))


def _gen_confused(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    tilt = 8 * math.sin(frame / total * math.pi * 2)
    _draw_body(p, colour, cx, cy, tilt=tilt)
    _draw_eyes_open(p, cx, cy)
    # Flat mouth
    pen = QPen(QColor("black"), 1.5)
    p.setPen(pen)
    p.drawLine(cx - 4, cy + 4, cx + 4, cy + 4)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)
    _draw_text_above(p, cx, cy, "?", QColor("#FFD700"))


def _gen_celebrate(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    bounce = -int(6 * abs(math.sin(frame / total * math.pi)))
    cy += bounce
    _draw_body(p, colour, cx, cy)
    _draw_eyes_happy(p, cx, cy)
    _draw_smile(p, cx, cy)
    _draw_gills(p, cx, cy, frame / total)
    _draw_legs(p, cx, cy)
    _draw_sparkles(p, cx, cy, frame / total)


def _gen_fall(p: QPainter, frame: int, total: int, colour: QColor):
    cx, cy = SIZE // 2, SIZE // 2
    tilt = 15 if frame % 2 == 0 else -15
    _draw_body(p, colour, cx, cy, tilt=tilt)
    _draw_eyes_open(p, cx, cy)
    # Open mouth (surprise)
    p.setBrush(QColor("black"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPoint(cx, cy + 4), 3, 4)
    _draw_gills(p, cx, cy, frame / total)
    # Spread limbs
    p.setBrush(colour)
    offsets = [(-22, -8), (22, -8), (-18, 18), (18, 18)]
    for ox, oy in offsets:
        p.drawRect(cx + ox - 3, cy + oy, 6, 6)


GENERATORS = {
    "idle": _gen_idle,
    "walk": _gen_walk,
    "sleep": _gen_sleep,
    "happy": _gen_happy,
    "sad": _gen_sad,
    "typing": _gen_typing,
    "petted": _gen_petted,
    "confused": _gen_confused,
    "celebrate": _gen_celebrate,
    "fall": _gen_fall,
}


# ── Icon generator ──────────────────────────────────────────────────


def _generate_icon(out_path: Path):
    """Generate a 64x64 tray icon — simple axolotl face."""
    img = QImage(ICON_SIZE, ICON_SIZE, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2 + 4
    colour = QColor("#FF69B4")

    # Body / face
    p.setBrush(colour)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRect(cx - 18, cy - 14, 36, 28))

    # Gills (simple)
    pen = QPen(QColor("#FF1493"), 2)
    p.setPen(pen)
    for side in (-1, 1):
        bx = cx + side * 18
        for i, a in enumerate([-25, 0, 25]):
            rad = math.radians(a)
            ln = 10
            p.drawLine(int(bx), cy - 6 + i * 4,
                        int(bx + side * ln * math.cos(rad)),
                        int(cy - 6 + i * 4 - ln * math.sin(rad)))

    # Eyes
    p.setBrush(QColor("black"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPoint(cx - 6, cy - 4), 2, 2)
    p.drawEllipse(QPoint(cx + 6, cy - 4), 2, 2)

    # Smile
    pen = QPen(QColor("black"), 1)
    p.setPen(pen)
    p.drawArc(QRect(cx - 4, cy, 8, 5), 0, -180 * 16)

    p.end()
    img.save(str(out_path))


# ── Main ────────────────────────────────────────────────────────────


def main():
    app = QApplication(sys.argv)  # noqa: F841  — needed for QPainter

    with open(META_PATH, "r") as f:
        meta: dict = json.load(f)

    total_frames = sum(info["frames"] for info in meta.values())
    generated = 0

    for anim_name, info in meta.items():
        num_frames = info["frames"]
        colour = QColor(COLORS.get(anim_name, "#FF69B4"))
        gen_fn = GENERATORS.get(anim_name)
        if gen_fn is None:
            print(f"  [skip] No generator for '{anim_name}'")
            continue

        anim_dir = SPRITES_DIR / anim_name
        anim_dir.mkdir(parents=True, exist_ok=True)

        for frame in range(num_frames):
            img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            gen_fn(p, frame, num_frames, colour)

            p.end()

            out_path = anim_dir / f"{anim_name}_{frame:02d}.png"
            img.save(str(out_path))
            generated += 1
            print(f"  [{generated}/{total_frames}] {out_path.relative_to(ROOT)}")

    # Tray icon
    icon_path = ASSETS_DIR / "icon.png"
    _generate_icon(icon_path)
    print(f"  [icon] {icon_path.relative_to(ROOT)}")

    print(f"\nDone — {generated} sprite frames + 1 icon generated.")


if __name__ == "__main__":
    main()
