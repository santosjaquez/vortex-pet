#!/usr/bin/env python3
"""Generate detailed kawaii axolotl PNG sprites for Vortex desktop pet.

Creates cute, recognizable axolotl drawings using QPainter with antialiasing,
gradients, and smooth QPainterPath curves. Run once from the repo root:

    python generate_placeholders.py
"""

import json
import math
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QPolygonF,
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

BODY_PINK = QColor("#FF8FAB")
BODY_PINK_DARK = QColor("#F07090")
BELLY_PINK = QColor("#FFD4E0")
GILL_COLOR = QColor("#FF6B8A")
GILL_COLOR_DARK = QColor("#E8456A")
GILL_TIP = QColor("#FF4570")
OUTLINE = QColor("#D06080")
OUTLINE_PEN = QPen(QColor("#C05575"), 1.5)
EYE_BLACK = QColor("#1A1A2E")
EYE_HIGHLIGHT = QColor(255, 255, 255, 230)
CHEEK_BLUSH = QColor(255, 100, 120, 90)
HEART_RED = QColor("#FF3366")
SPARKLE_GOLD = QColor("#FFD700")
TEAR_BLUE = QColor("#88CCFF")
ZZZ_PURPLE = QColor("#8B7EC8")


# ── Drawing primitives ──────────────────────────────────────────────


def _body_gradient(cx: float, cy: float) -> QRadialGradient:
    """Create a soft radial gradient for the body."""
    g = QRadialGradient(QPointF(cx - 4, cy - 6), 40)
    g.setColorAt(0.0, BELLY_PINK)
    g.setColorAt(0.5, BODY_PINK)
    g.setColorAt(1.0, BODY_PINK_DARK)
    return g


def _draw_tail(p: QPainter, cx: float, cy: float, body_w: float, body_h: float,
               wag: float = 0.0):
    """Draw a flat fin-like tail tapering to a point."""
    p.save()
    tail_base_x = cx + body_w * 0.38
    tail_base_y = cy + 2
    tip_x = tail_base_x + 28
    tip_y = tail_base_y - 4 + wag * 6

    path = QPainterPath()
    path.moveTo(tail_base_x, tail_base_y - 6)
    path.cubicTo(tail_base_x + 12, tail_base_y - 12 + wag * 3,
                 tip_x - 8, tip_y - 6,
                 tip_x, tip_y)
    path.cubicTo(tip_x - 8, tip_y + 8,
                 tail_base_x + 12, tail_base_y + 10 + wag * 2,
                 tail_base_x, tail_base_y + 6)
    path.closeSubpath()

    # Gradient along tail
    tg = QLinearGradient(QPointF(tail_base_x, tail_base_y),
                         QPointF(tip_x, tip_y))
    tg.setColorAt(0.0, BODY_PINK)
    tg.setColorAt(1.0, BODY_PINK_DARK)
    p.setBrush(QBrush(tg))
    p.setPen(QPen(OUTLINE, 1.2))
    p.drawPath(path)

    # Fin line detail
    p.setPen(QPen(QColor(200, 100, 130, 80), 0.8))
    mid_x = (tail_base_x + tip_x) / 2
    mid_y = (tail_base_y + tip_y) / 2
    p.drawLine(QPointF(tail_base_x + 6, tail_base_y),
               QPointF(mid_x + 4, mid_y - 1 + wag * 2))
    p.restore()


def _draw_body(p: QPainter, cx: float, cy: float, scale_x: float = 1.0,
               scale_y: float = 1.0, tilt: float = 0.0):
    """Draw the main rounded body with gradient and belly highlight."""
    p.save()
    p.translate(cx, cy)
    if tilt:
        p.rotate(tilt)
    p.scale(scale_x, scale_y)

    body_w, body_h = 44, 34

    # Main body ellipse with gradient
    grad = _body_gradient(0, 0)
    p.setBrush(QBrush(grad))
    p.setPen(QPen(OUTLINE, 1.3))
    body_rect = QRectF(-body_w / 2, -body_h / 2, body_w, body_h)
    p.drawEllipse(body_rect)

    # Belly highlight (lighter ellipse in lower-center)
    belly = QPainterPath()
    belly.addEllipse(QRectF(-body_w * 0.3, -body_h * 0.05, body_w * 0.6, body_h * 0.55))
    p.setPen(Qt.PenStyle.NoPen)
    belly_color = QColor(BELLY_PINK)
    belly_color.setAlpha(120)
    p.setBrush(belly_color)
    p.drawPath(belly)

    p.restore()


def _draw_head(p: QPainter, cx: float, cy: float, scale: float = 1.0):
    """Draw the wide, flat-topped, rounded head."""
    p.save()
    p.translate(cx, cy)
    p.scale(scale, scale)

    head_w, head_h = 54, 40

    # Head shape: wider than body, slightly flat on top
    path = QPainterPath()
    # Start from top-left, go clockwise
    path.moveTo(-head_w * 0.35, -head_h * 0.45)
    # Flat top
    path.cubicTo(-head_w * 0.1, -head_h * 0.52,
                 head_w * 0.1, -head_h * 0.52,
                 head_w * 0.35, -head_h * 0.45)
    # Right side bulge
    path.cubicTo(head_w * 0.55, -head_h * 0.3,
                 head_w * 0.55, head_h * 0.2,
                 head_w * 0.3, head_h * 0.45)
    # Bottom (chin)
    path.cubicTo(head_w * 0.1, head_h * 0.52,
                 -head_w * 0.1, head_h * 0.52,
                 -head_w * 0.3, head_h * 0.45)
    # Left side bulge
    path.cubicTo(-head_w * 0.55, head_h * 0.2,
                 -head_w * 0.55, -head_h * 0.3,
                 -head_w * 0.35, -head_h * 0.45)

    grad = QRadialGradient(QPointF(-3, -4), head_w * 0.6)
    grad.setColorAt(0.0, BELLY_PINK)
    grad.setColorAt(0.4, BODY_PINK)
    grad.setColorAt(1.0, BODY_PINK_DARK)
    p.setBrush(QBrush(grad))
    p.setPen(QPen(OUTLINE, 1.3))
    p.drawPath(path)

    p.restore()


def _draw_eyes_open(p: QPainter, cx: float, cy: float, wide: bool = False,
                    blink: float = 1.0):
    """Draw large kawaii eyes with highlights. blink: 1.0=open, 0.0=closed."""
    eye_r = 7 if wide else 6
    eye_spacing = 13
    eye_y = cy - 3

    for side in (-1, 1):
        ex = cx + side * eye_spacing
        ey = eye_y

        if blink < 0.2:
            # Fully closed - draw line
            p.setPen(QPen(EYE_BLACK, 2.0))
            p.drawLine(QPointF(ex - eye_r * 0.7, ey),
                       QPointF(ex + eye_r * 0.7, ey))
            continue

        # Outer eye (white)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 240))
        scaled_h = eye_r * blink
        p.drawEllipse(QPointF(ex, ey), eye_r, scaled_h)

        # Pupil
        pupil_r = eye_r * 0.65
        p.setBrush(EYE_BLACK)
        p.drawEllipse(QPointF(ex, ey), pupil_r, pupil_r * blink)

        # Main highlight (upper-left)
        p.setBrush(EYE_HIGHLIGHT)
        hl_r = eye_r * 0.3
        p.drawEllipse(QPointF(ex - eye_r * 0.25, ey - scaled_h * 0.3),
                       hl_r, hl_r * blink)

        # Small secondary highlight (lower-right)
        p.setBrush(QColor(255, 255, 255, 160))
        hl2_r = eye_r * 0.15
        p.drawEllipse(QPointF(ex + eye_r * 0.2, ey + scaled_h * 0.15),
                       hl2_r, hl2_r * blink)


def _draw_eyes_happy(p: QPainter, cx: float, cy: float):
    """Draw ^_^ eyes."""
    eye_spacing = 13
    eye_y = cy - 3
    p.setPen(QPen(EYE_BLACK, 2.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for side in (-1, 1):
        ex = cx + side * eye_spacing
        # Inverted arc (happy squint)
        arc_rect = QRectF(ex - 5, eye_y - 5, 10, 8)
        p.drawArc(arc_rect, 0, 180 * 16)


def _draw_eyes_sad(p: QPainter, cx: float, cy: float):
    """Draw droopy sad eyes."""
    eye_spacing = 13
    eye_y = cy - 3

    for side in (-1, 1):
        ex = cx + side * eye_spacing
        # Half-closed eye
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(ex, eye_y), 5, 3)
        # Pupil (looking down)
        p.setBrush(EYE_BLACK)
        p.drawEllipse(QPointF(ex, eye_y + 1), 3, 2)
        # Droopy eyelid
        p.setPen(QPen(EYE_BLACK, 1.5))
        lid = QPainterPath()
        lid.moveTo(ex - 6, eye_y - 2 + side)
        lid.quadTo(ex, eye_y - 5, ex + 6, eye_y - 2 - side)
        p.drawPath(lid)
        # Highlight
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 140))
        p.drawEllipse(QPointF(ex - 1.5, eye_y - 0.5), 1.2, 1.0)


def _draw_eyes_surprised(p: QPainter, cx: float, cy: float):
    """Draw O_O surprised eyes."""
    eye_spacing = 13
    eye_y = cy - 3
    eye_r = 7

    for side in (-1, 1):
        ex = cx + side * eye_spacing
        # Large white circle
        p.setPen(QPen(EYE_BLACK, 1.5))
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(ex, eye_y), eye_r, eye_r)
        # Small pupil (contracted)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(EYE_BLACK)
        p.drawEllipse(QPointF(ex, eye_y), 3, 3)
        # Highlight
        p.setBrush(EYE_HIGHLIGHT)
        p.drawEllipse(QPointF(ex - 2, eye_y - 2.5), 1.8, 1.8)


def _draw_eyes_confused(p: QPainter, cx: float, cy: float):
    """One eye bigger than the other."""
    eye_y = cy - 3

    # Left eye (smaller)
    ex = cx - 13
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(ex, eye_y), 4.5, 4.5)
    p.setBrush(EYE_BLACK)
    p.drawEllipse(QPointF(ex, eye_y), 2.8, 2.8)
    p.setBrush(EYE_HIGHLIGHT)
    p.drawEllipse(QPointF(ex - 1.2, eye_y - 1.5), 1.2, 1.2)

    # Right eye (bigger)
    ex = cx + 13
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(ex, eye_y), 7, 7)
    p.setBrush(EYE_BLACK)
    p.drawEllipse(QPointF(ex, eye_y + 0.5), 4, 4)
    p.setBrush(EYE_HIGHLIGHT)
    p.drawEllipse(QPointF(ex - 2, eye_y - 2), 1.8, 1.8)


def _draw_mouth_smile(p: QPainter, cx: float, cy: float):
    """Small permanent smile."""
    p.setPen(QPen(QColor("#8B4060"), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(cx - 4, cy + 6)
    path.quadTo(cx, cy + 10, cx + 4, cy + 6)
    p.drawPath(path)


def _draw_mouth_open(p: QPainter, cx: float, cy: float, size: float = 1.0):
    """Open mouth (surprise/celebrate)."""
    p.setPen(QPen(QColor("#8B4060"), 1.3))
    p.setBrush(QColor("#CC3366"))
    p.drawEllipse(QPointF(cx, cy + 7), 3 * size, 4 * size)


def _draw_mouth_frown(p: QPainter, cx: float, cy: float):
    """Small frown."""
    p.setPen(QPen(QColor("#8B4060"), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(cx - 4, cy + 9)
    path.quadTo(cx, cy + 6, cx + 4, cy + 9)
    p.drawPath(path)


def _draw_gills(p: QPainter, cx: float, cy: float, phase: float,
                droop: float = 0.0, blown_back: float = 0.0):
    """Draw 3 feathery gill branches on each side with sub-branches.

    phase: 0-1 animation cycle for wiggle
    droop: 0-1 how much gills droop down (sad/sleep)
    blown_back: 0-1 how much gills are pushed backward (fall)
    """
    for side in (-1, 1):
        base_x = cx + side * 26
        base_y = cy - 8

        for i, angle_base in enumerate([-35, -5, 25]):
            # Wiggle
            wiggle = math.sin(phase * math.pi * 2 + i * 1.2) * 6
            # Droop pulls angles downward
            droop_offset = droop * 30
            # Blown back pushes toward horizontal on trailing side
            blow_offset = blown_back * side * 25

            angle = angle_base + wiggle - droop_offset + blow_offset
            rad = math.radians(angle)
            length = 16 - i * 1.5

            # Main branch
            end_x = base_x + side * length * math.cos(rad)
            end_y = base_y + i * 4 - length * math.sin(rad)

            # Draw main gill branch (thicker at base)
            p.setPen(QPen(GILL_COLOR, 2.5))
            p.drawLine(QPointF(base_x, base_y + i * 4),
                       QPointF(end_x, end_y))

            # Sub-branches (2 per main branch)
            for j, sub_frac in enumerate([0.45, 0.75]):
                sub_base_x = base_x + (end_x - base_x) * sub_frac
                sub_base_y = (base_y + i * 4) + (end_y - (base_y + i * 4)) * sub_frac
                sub_angle = angle + (15 if j == 0 else -15) + wiggle * 0.5
                sub_rad = math.radians(sub_angle)
                sub_len = 6
                sub_end_x = sub_base_x + side * sub_len * math.cos(sub_rad)
                sub_end_y = sub_base_y - sub_len * math.sin(sub_rad)

                p.setPen(QPen(GILL_TIP, 1.5))
                p.drawLine(QPointF(sub_base_x, sub_base_y),
                           QPointF(sub_end_x, sub_end_y))

            # Gill tip dot
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(GILL_TIP)
            p.drawEllipse(QPointF(end_x, end_y), 1.8, 1.8)


def _draw_legs(p: QPainter, cx: float, cy: float, body_bottom: float,
               left_phase: float = 0.0, right_phase: float = 0.0):
    """Draw 4 stubby legs with tiny toes.

    left_phase/right_phase: 0-1 for walk cycle offset
    """
    leg_positions = [
        (-14, body_bottom - 2, left_phase),      # front-left
        (-6, body_bottom, left_phase + 0.5),      # back-left
        (6, body_bottom, right_phase),             # front-right
        (14, body_bottom - 2, right_phase + 0.5), # back-right
    ]

    for lx_off, ly, phase in leg_positions:
        lx = cx + lx_off
        # Walk bounce
        walk_offset = math.sin(phase * math.pi * 2) * 3

        p.setPen(QPen(OUTLINE, 1.0))
        p.setBrush(BODY_PINK)

        # Leg body (small rounded rect)
        leg_path = QPainterPath()
        leg_top = ly + 1
        leg_bottom = ly + 8 - walk_offset
        leg_path.addRoundedRect(QRectF(lx - 3.5, leg_top, 7, max(4, leg_bottom - leg_top)), 3, 3)
        p.drawPath(leg_path)

        # Tiny toes (3 per foot)
        foot_y = leg_bottom
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BODY_PINK_DARK)
        for t in range(-1, 2):
            p.drawEllipse(QPointF(lx + t * 2.5, foot_y + 1), 1.5, 1.2)


def _draw_legs_spread(p: QPainter, cx: float, cy: float):
    """Draw legs spread out (falling)."""
    positions = [(-20, -8), (20, -8), (-16, 16), (16, 16)]
    for ox, oy in positions:
        lx = cx + ox
        ly = cy + oy
        p.setPen(QPen(OUTLINE, 1.0))
        p.setBrush(BODY_PINK)
        leg_path = QPainterPath()
        leg_path.addRoundedRect(QRectF(lx - 3.5, ly, 7, 7), 3, 3)
        p.drawPath(leg_path)
        # Toes
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BODY_PINK_DARK)
        toe_dir = 1 if ox > 0 else -1
        for t in range(-1, 2):
            tx = lx + toe_dir * 4
            ty = ly + 3.5 + t * 2.5
            p.drawEllipse(QPointF(tx, ty), 1.2, 1.5)


def _draw_hearts(p: QPainter, cx: float, cy: float, count: int = 3,
                 phase: float = 0.0):
    """Draw floating hearts above the character."""
    for i in range(count):
        t = (phase + i * 0.33) % 1.0
        hx = cx - 16 + i * 16 + math.sin(t * math.pi * 2) * 4
        hy = cy - 30 - t * 15
        alpha = int(255 * (1.0 - t * 0.6))
        sz = 4 + t * 2

        p.setPen(Qt.PenStyle.NoPen)
        color = QColor(HEART_RED)
        color.setAlpha(alpha)
        p.setBrush(color)

        path = QPainterPath()
        path.moveTo(hx, hy + sz * 0.4)
        path.cubicTo(hx - sz, hy - sz * 0.4, hx - sz, hy + sz * 0.6,
                     hx, hy + sz)
        path.cubicTo(hx + sz, hy + sz * 0.6, hx + sz, hy - sz * 0.4,
                     hx, hy + sz * 0.4)
        p.drawPath(path)


def _draw_cheeks(p: QPainter, cx: float, cy: float):
    """Rosy blush circles on cheeks."""
    p.setPen(Qt.PenStyle.NoPen)
    for side in (-1, 1):
        g = QRadialGradient(QPointF(cx + side * 18, cy + 4), 6)
        g.setColorAt(0.0, QColor(255, 100, 130, 110))
        g.setColorAt(1.0, QColor(255, 100, 130, 0))
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx + side * 18, cy + 4), 6, 4)


def _draw_sparkles(p: QPainter, cx: float, cy: float, phase: float, count: int = 6):
    """Draw sparkle/star shapes around the character."""
    for i in range(count):
        angle = (i / count) * 360 + phase * 360
        r = 34 + math.sin(phase * math.pi * 4 + i * 1.3) * 8
        sx = cx + r * math.cos(math.radians(angle))
        sy = cy + r * math.sin(math.radians(angle))

        t = (phase * 3 + i * 0.2) % 1.0
        sz = 3 + math.sin(t * math.pi) * 3
        alpha = int(180 + 75 * math.sin(t * math.pi))

        color = QColor(SPARKLE_GOLD)
        color.setAlpha(alpha)
        p.setPen(QPen(color, 1.5))

        # 4-pointed star
        p.drawLine(QPointF(sx - sz, sy), QPointF(sx + sz, sy))
        p.drawLine(QPointF(sx, sy - sz), QPointF(sx, sy + sz))
        # Diagonal (smaller)
        d = sz * 0.6
        p.drawLine(QPointF(sx - d, sy - d), QPointF(sx + d, sy + d))
        p.drawLine(QPointF(sx + d, sy - d), QPointF(sx - d, sy + d))


def _draw_confetti(p: QPainter, cx: float, cy: float, phase: float):
    """Draw confetti particles."""
    colors = [QColor("#FF6B8A"), QColor("#FFD700"), QColor("#88CCFF"),
              QColor("#90EE90"), QColor("#DDA0DD"), QColor("#FFA500")]
    for i in range(10):
        t = (phase + i * 0.1) % 1.0
        angle = (i / 10) * 360 + phase * 180
        r = 20 + t * 30
        px = cx + r * math.cos(math.radians(angle))
        py = cy - 30 + t * 60
        rot = phase * 360 + i * 40

        p.save()
        p.translate(px, py)
        p.rotate(rot)
        color = QColor(colors[i % len(colors)])
        color.setAlpha(int(255 * (1.0 - t * 0.7)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRect(QRectF(-2, -1, 4, 2))
        p.restore()


def _draw_tear(p: QPainter, cx: float, cy: float, phase: float):
    """Draw a teardrop."""
    t = phase % 1.0
    tx = cx + 17
    ty = cy + 1 + t * 12
    alpha = int(200 * (1.0 - t))

    color = QColor(TEAR_BLUE)
    color.setAlpha(alpha)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)

    path = QPainterPath()
    path.moveTo(tx, ty - 3)
    path.cubicTo(tx - 2.5, ty, tx - 2.5, ty + 3, tx, ty + 4)
    path.cubicTo(tx + 2.5, ty + 3, tx + 2.5, ty, tx, ty - 3)
    p.drawPath(path)


def _draw_party_hat(p: QPainter, cx: float, cy: float):
    """Draw a small party hat on top of head."""
    hat_tip_x = cx + 2
    hat_tip_y = cy - 28

    path = QPainterPath()
    path.moveTo(hat_tip_x, hat_tip_y)
    path.lineTo(cx - 8, cy - 14)
    path.lineTo(cx + 12, cy - 14)
    path.closeSubpath()

    g = QLinearGradient(QPointF(hat_tip_x, hat_tip_y), QPointF(cx, cy - 14))
    g.setColorAt(0.0, QColor("#FFD700"))
    g.setColorAt(0.5, QColor("#FF6B8A"))
    g.setColorAt(1.0, QColor("#8B88FF"))
    p.setBrush(QBrush(g))
    p.setPen(QPen(QColor("#CC5577"), 1.2))
    p.drawPath(path)

    # Pom-pom on top
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFD700"))
    p.drawEllipse(QPointF(hat_tip_x, hat_tip_y - 2), 3, 3)

    # Stripe on hat
    p.setPen(QPen(QColor(255, 255, 255, 130), 1.2))
    p.drawLine(QPointF(cx - 3, cy - 18), QPointF(cx + 7, cy - 18))


def _draw_keyboard(p: QPainter, cx: float, cy: float):
    """Draw a tiny laptop/keyboard in front of the axolotl."""
    kx = cx - 12
    ky = cy + 14

    # Laptop base
    p.setPen(QPen(QColor("#555555"), 1.2))
    p.setBrush(QColor("#888888"))
    p.drawRoundedRect(QRectF(kx, ky, 24, 10), 2, 2)

    # Screen (angled)
    screen_path = QPainterPath()
    screen_path.moveTo(kx + 1, ky)
    screen_path.lineTo(kx + 3, ky - 10)
    screen_path.lineTo(kx + 21, ky - 10)
    screen_path.lineTo(kx + 23, ky)
    screen_path.closeSubpath()
    p.setBrush(QColor("#333333"))
    p.drawPath(screen_path)

    # Screen glow
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#6699CC"))
    p.drawRect(QRectF(kx + 5, ky - 8, 14, 6))

    # Keyboard keys (tiny dots)
    p.setBrush(QColor("#AAAAAA"))
    for row in range(2):
        for col in range(5):
            p.drawRect(QRectF(kx + 2 + col * 4, ky + 2 + row * 3.5, 3, 2.5))


def _draw_zzz(p: QPainter, cx: float, cy: float, count: int, phase: float):
    """Draw floating Z's."""
    font = QFont("sans-serif", 10, QFont.Weight.Bold)
    p.setFont(font)

    for i in range(count):
        t = (phase + i * 0.3) % 1.0
        zx = cx + 18 + i * 8 + t * 5
        zy = cy - 18 - i * 10 - t * 8
        alpha = int(200 * (1.0 - t * 0.5))
        sz = 9 + i * 2

        color = QColor(ZZZ_PURPLE)
        color.setAlpha(alpha)
        p.setPen(QPen(color, 1))
        font.setPixelSize(sz)
        p.setFont(font)
        p.drawText(QPointF(zx, zy), "Z")


def _draw_question_mark(p: QPainter, cx: float, cy: float, phase: float):
    """Draw animated question mark above head."""
    qx = cx + 2
    qy = cy - 32 + math.sin(phase * math.pi * 2) * 3

    font = QFont("sans-serif", 16, QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(SPARKLE_GOLD, 1))
    p.drawText(QPointF(qx - 5, qy), "?")


# ── Composite axolotl drawing ───────────────────────────────────────

def _draw_axolotl(p: QPainter, cx: float, cy: float, phase: float = 0.0,
                  eyes: str = "open", mouth: str = "smile", blink: float = 1.0,
                  body_scale_x: float = 1.0, body_scale_y: float = 1.0,
                  tilt: float = 0.0, gill_droop: float = 0.0,
                  gill_blown: float = 0.0, walk_phase: float = 0.0,
                  spread_legs: bool = False, tail_wag: float = 0.0):
    """Draw the complete axolotl with all parts."""
    body_bottom = cy + 13

    # Tail (behind body)
    _draw_tail(p, cx, cy + 2, 44, 34, wag=tail_wag)

    # Body
    _draw_body(p, cx, cy, scale_x=body_scale_x, scale_y=body_scale_y, tilt=tilt)

    # Head (overlaps body top)
    head_y = cy - 12
    _draw_head(p, cx, head_y)

    # Gills (on sides of head)
    _draw_gills(p, cx, head_y, phase, droop=gill_droop, blown_back=gill_blown)

    # Legs
    if spread_legs:
        _draw_legs_spread(p, cx, cy)
    else:
        left_ph = walk_phase
        right_ph = walk_phase + 0.5
        _draw_legs(p, cx, cy, body_bottom, left_phase=left_ph, right_phase=right_ph)

    # Eyes
    if eyes == "open":
        _draw_eyes_open(p, cx, head_y, blink=blink)
    elif eyes == "happy":
        _draw_eyes_happy(p, cx, head_y)
    elif eyes == "sad":
        _draw_eyes_sad(p, cx, head_y)
    elif eyes == "surprised":
        _draw_eyes_surprised(p, cx, head_y)
    elif eyes == "confused":
        _draw_eyes_confused(p, cx, head_y)
    elif eyes == "closed":
        _draw_eyes_open(p, cx, head_y, blink=0.0)

    # Mouth
    if mouth == "smile":
        _draw_mouth_smile(p, cx, head_y)
    elif mouth == "open":
        _draw_mouth_open(p, cx, head_y)
    elif mouth == "wide":
        _draw_mouth_open(p, cx, head_y, size=1.5)
    elif mouth == "frown":
        _draw_mouth_frown(p, cx, head_y)


# ── Frame generators per animation ─────────────────────────────────


def _gen_idle(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 6
    t = frame / total

    # Breathing: subtle body scale change
    breath = math.sin(t * math.pi * 2) * 0.03
    # Occasional blink (frame 3 out of 6)
    blink = 0.1 if frame == 3 else 1.0
    # Gentle tail sway
    tail = math.sin(t * math.pi * 2) * 0.3

    _draw_axolotl(p, cx, cy, phase=t, eyes="open", mouth="smile",
                  blink=blink, body_scale_x=1.0 + breath,
                  body_scale_y=1.0 - breath * 0.5, tail_wag=tail)


def _gen_walk(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 6
    t = frame / total

    # Bounce while walking
    bounce = -abs(math.sin(t * math.pi * 2)) * 4
    # Body tilt with walk
    tilt = math.sin(t * math.pi * 2) * 4
    # Tail trails behind
    tail = math.sin(t * math.pi * 2 + 0.5) * 0.6

    _draw_axolotl(p, cx, cy + bounce, phase=t, eyes="open", mouth="smile",
                  tilt=tilt, walk_phase=t, tail_wag=tail)


def _gen_sleep(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 8
    t = frame / total

    # Slow breathing
    breath = math.sin(t * math.pi * 2) * 0.04

    _draw_axolotl(p, cx, cy, phase=t * 0.3, eyes="closed", mouth="smile",
                  body_scale_x=1.0 + breath, body_scale_y=1.0 - breath * 0.3,
                  gill_droop=0.6, tail_wag=-0.2)

    # Zzz
    z_count = (frame % 3) + 1
    _draw_zzz(p, cx, cy - 14, z_count, t)


def _gen_happy(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 6
    t = frame / total

    # Jumping
    jump = -abs(math.sin(t * math.pi)) * 10
    tail = math.sin(t * math.pi * 3) * 0.8

    _draw_axolotl(p, cx, cy + jump, phase=t, eyes="happy", mouth="smile",
                  tail_wag=tail)
    _draw_cheeks(p, cx, cy + jump - 12)

    # Sparkles
    _draw_sparkles(p, cx, cy + jump, t, count=4)


def _gen_sad(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 10
    t = frame / total

    _draw_axolotl(p, cx, cy, phase=t * 0.5, eyes="sad", mouth="frown",
                  body_scale_y=0.95, gill_droop=0.8, tail_wag=-0.15)

    # Tear drop
    _draw_tear(p, cx, cy - 12, t)


def _gen_typing(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 2
    t = frame / total

    # Focused expression with slight head bob
    bob = math.sin(t * math.pi * 4) * 1.5

    _draw_axolotl(p, cx, cy + bob, phase=t, eyes="open", mouth="smile",
                  tail_wag=math.sin(t * math.pi) * 0.2)

    # Keyboard in front
    _draw_keyboard(p, cx, cy + bob + 4)


def _gen_petted(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 6
    t = frame / total

    # Slight squish when petted
    squish = math.sin(t * math.pi * 2) * 0.04

    _draw_axolotl(p, cx, cy, phase=t, eyes="happy", mouth="smile",
                  body_scale_x=1.0 + squish, body_scale_y=1.0 - squish,
                  tail_wag=math.sin(t * math.pi * 3) * 0.5)
    _draw_cheeks(p, cx, cy - 12)

    # Floating hearts
    _draw_hearts(p, cx, cy - 12, count=min(frame + 1, 3), phase=t)


def _gen_confused(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 6
    t = frame / total

    # Head tilt
    tilt = 8 + math.sin(t * math.pi * 2) * 5

    _draw_axolotl(p, cx, cy, phase=t, eyes="confused", mouth="smile",
                  tilt=tilt, tail_wag=math.sin(t * math.pi) * 0.3)

    # Question mark
    _draw_question_mark(p, cx, cy - 12, t)


def _gen_celebrate(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 6
    t = frame / total

    # Big jump
    jump = -abs(math.sin(t * math.pi)) * 14
    tail = math.sin(t * math.pi * 4) * 1.0

    _draw_axolotl(p, cx, cy + jump, phase=t, eyes="happy", mouth="wide",
                  tail_wag=tail)

    # Party hat
    _draw_party_hat(p, cx, cy + jump - 12)

    # Confetti
    _draw_confetti(p, cx, cy, t)


def _gen_fall(p: QPainter, frame: int, total: int):
    cx, cy = SIZE // 2, SIZE // 2 + 4
    t = frame / total

    # Rotation while falling
    tilt = 15 * math.sin(t * math.pi * 2)

    _draw_axolotl(p, cx, cy, phase=t, eyes="surprised", mouth="open",
                  tilt=tilt, spread_legs=True, gill_blown=0.8,
                  tail_wag=math.sin(t * math.pi * 4) * 0.8)


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
    """Generate a 64x64 tray icon — cute axolotl face."""
    img = QImage(ICON_SIZE, ICON_SIZE, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2 + 2

    # Head (fills most of icon)
    head_w, head_h = 42, 34
    path = QPainterPath()
    path.moveTo(cx - head_w * 0.35, cy - head_h * 0.45)
    path.cubicTo(cx - head_w * 0.1, cy - head_h * 0.52,
                 cx + head_w * 0.1, cy - head_h * 0.52,
                 cx + head_w * 0.35, cy - head_h * 0.45)
    path.cubicTo(cx + head_w * 0.55, cy - head_h * 0.3,
                 cx + head_w * 0.55, cy + head_h * 0.2,
                 cx + head_w * 0.3, cy + head_h * 0.45)
    path.cubicTo(cx + head_w * 0.1, cy + head_h * 0.52,
                 cx - head_w * 0.1, cy + head_h * 0.52,
                 cx - head_w * 0.3, cy + head_h * 0.45)
    path.cubicTo(cx - head_w * 0.55, cy + head_h * 0.2,
                 cx - head_w * 0.55, cy - head_h * 0.3,
                 cx - head_w * 0.35, cy - head_h * 0.45)

    grad = QRadialGradient(QPointF(cx - 2, cy - 3), head_w * 0.55)
    grad.setColorAt(0.0, BELLY_PINK)
    grad.setColorAt(0.5, BODY_PINK)
    grad.setColorAt(1.0, BODY_PINK_DARK)
    p.setBrush(QBrush(grad))
    p.setPen(QPen(OUTLINE, 1.2))
    p.drawPath(path)

    # Gills (simplified for icon size)
    for side in (-1, 1):
        base_x = cx + side * 20
        for i, angle in enumerate([-30, 0, 25]):
            rad = math.radians(angle)
            length = 10
            end_x = base_x + side * length * math.cos(rad)
            end_y = cy - 4 + i * 3 - length * math.sin(rad)

            p.setPen(QPen(GILL_COLOR, 2.0))
            p.drawLine(QPointF(base_x, cy - 4 + i * 3),
                       QPointF(end_x, end_y))
            # Tip dot
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(GILL_TIP)
            p.drawEllipse(QPointF(end_x, end_y), 1.3, 1.3)

    # Eyes
    eye_y = cy - 2
    for side in (-1, 1):
        ex = cx + side * 9
        # White
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawEllipse(QPointF(ex, eye_y), 5, 5)
        # Pupil
        p.setBrush(EYE_BLACK)
        p.drawEllipse(QPointF(ex, eye_y), 3.2, 3.2)
        # Highlight
        p.setBrush(EYE_HIGHLIGHT)
        p.drawEllipse(QPointF(ex - 1.5, eye_y - 1.8), 1.5, 1.5)

    # Smile
    p.setPen(QPen(QColor("#8B4060"), 1.3))
    p.setBrush(Qt.BrushStyle.NoBrush)
    smile = QPainterPath()
    smile.moveTo(cx - 3, cy + 6)
    smile.quadTo(cx, cy + 9, cx + 3, cy + 6)
    p.drawPath(smile)

    # Blush
    p.setPen(Qt.PenStyle.NoPen)
    for side in (-1, 1):
        g = QRadialGradient(QPointF(cx + side * 13, cy + 4), 4.5)
        g.setColorAt(0.0, QColor(255, 100, 130, 100))
        g.setColorAt(1.0, QColor(255, 100, 130, 0))
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx + side * 13, cy + 4), 4.5, 3)

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
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            gen_fn(p, frame, num_frames)

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
