"""Pillow-based achievement card generator for Apex fitness agent."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD if bold else _FONT_REGULAR
    return ImageFont.truetype(path, size)


def _draw_gradient_bar(draw: ImageDraw.ImageDraw, width: int, y: int, height: int = 8) -> None:
    """Draw a horizontal purple-to-blue gradient bar."""
    left_color = (124, 58, 237)   # #7c3aed purple
    right_color = (37, 99, 235)   # #2563eb blue
    for x in range(width):
        t = x / max(width - 1, 1)
        r = int(left_color[0] + (right_color[0] - left_color[0]) * t)
        g = int(left_color[1] + (right_color[1] - left_color[1]) * t)
        b = int(left_color[2] + (right_color[2] - left_color[2]) * t)
        draw.line([(x, y), (x, y + height - 1)], fill=(r, g, b))


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """Return (width, height) of text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    width: int,
    fill: tuple,
) -> None:
    """Draw text horizontally centered within 'width'."""
    w, _ = _text_size(draw, text, font)
    x = (width - w) // 2
    draw.text((x, y), text, font=font, fill=fill)


def generate_pr_card(
    user_name: str,
    exercise: str,
    weight_kg: float,
    reps: int,
    previous_kg: float | None = None,
) -> bytes:
    """Generate a 900x500 Personal Record card. Returns JPEG bytes."""
    W, H = 900, 500
    BG = (8, 8, 16)  # #080810

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Top and bottom gradient bars
    _draw_gradient_bar(draw, W, 0, height=8)
    _draw_gradient_bar(draw, W, H - 8, height=8)

    # ── LEFT HALF: glowing golden circle ────────────────────────────────────
    cx, cy, radius = 225, 250, 130

    # Glow layer (RGBA, GaussianBlur)
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(251, 191, 36, 80),  # #fbbf24, alpha=80
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=40))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, glow_layer)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Outer dark gold circle
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(180, 83, 9),  # #b45309
    )
    # Inner slightly smaller gold circle
    inner_r = radius - 8
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=(217, 119, 6),  # #d97706
    )

    # "PR" text centered in circle
    pr_font = _font(72, bold=True)
    pr_w, pr_h = _text_size(draw, "PR", pr_font)
    draw.text((cx - pr_w // 2, cy - pr_h // 2), "PR", font=pr_font, fill=(255, 255, 255))

    # ── RIGHT HALF ───────────────────────────────────────────────────────────
    rx = 460  # right half start x

    # "PERSONAL RECORD" label
    label_font = _font(15, bold=True)
    draw.text((rx, 80), "PERSONAL RECORD", font=label_font, fill=(124, 58, 237))

    # Exercise name (truncated to 18 chars)
    ex_display = exercise.upper()[:18]
    ex_font = _font(38, bold=True)
    draw.text((rx, 110), ex_display, font=ex_font, fill=(255, 255, 255))

    # Weight
    weight_font = _font(80, bold=True)
    weight_text = f"{weight_kg:g} KG"
    draw.text((rx, 165), weight_text, font=weight_font, fill=(255, 255, 255))

    # Reps
    reps_font = _font(40, bold=True)
    draw.text((rx, 265), f"× {reps} REPS", font=reps_font, fill=(167, 139, 250))  # #a78bfa

    # Previous best
    if previous_kg is not None:
        prev_font = _font(20, bold=False)
        diff = weight_kg - previous_kg
        prev_text = f"Previous best: {previous_kg:g} kg  (+{diff:g} kg)"
        draw.text((rx, 325), prev_text, font=prev_font, fill=(156, 163, 175))  # #9ca3af

    # User name
    name_font = _font(20, bold=False)
    draw.text((rx, 375), user_name or "Athlete", font=name_font, fill=(156, 163, 175))

    # APEX branding bottom-right
    apex_font = _font(16, bold=True)
    apex_text = "APEX"
    apex_w, apex_h = _text_size(draw, apex_text, apex_font)
    draw.text((870 - apex_w, 475 - apex_h), apex_text, font=apex_font, fill=(124, 58, 237))

    # Encode to JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    radius: int,
    fill: tuple,
    outline: tuple | None = None,
    outline_width: int = 1,
) -> None:
    """Draw a rounded rectangle manually using rectangles and ellipses."""
    # Fill main body
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    # Four corner circles
    draw.ellipse([x0, y0, x0 + 2 * radius, y0 + 2 * radius], fill=fill)
    draw.ellipse([x1 - 2 * radius, y0, x1, y0 + 2 * radius], fill=fill)
    draw.ellipse([x0, y1 - 2 * radius, x0 + 2 * radius, y1], fill=fill)
    draw.ellipse([x1 - 2 * radius, y1 - 2 * radius, x1, y1], fill=fill)

    if outline:
        # Draw outline arcs
        draw.arc([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=outline, width=outline_width)
        draw.arc([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=outline, width=outline_width)
        draw.arc([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=outline, width=outline_width)
        draw.arc([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=outline, width=outline_width)
        draw.line([x0 + radius, y0, x1 - radius, y0], fill=outline, width=outline_width)
        draw.line([x0 + radius, y1, x1 - radius, y1], fill=outline, width=outline_width)
        draw.line([x0, y0 + radius, x0, y1 - radius], fill=outline, width=outline_width)
        draw.line([x1, y0 + radius, x1, y1 - radius], fill=outline, width=outline_width)


def generate_weekly_recap_card(
    user_name: str,
    week_label: str,
    workouts: int,
    avg_calories: float,
    prs_hit: int,
    weight_change_kg: float,
) -> bytes:
    """Generate an 800x960 weekly recap card. Returns JPEG bytes."""
    W, H = 800, 960
    BG = (8, 8, 16)  # #080810
    GRAY = (156, 163, 175)   # #9ca3af
    WHITE = (255, 255, 255)
    PURPLE = (124, 58, 237)  # #7c3aed
    DIVIDER = (31, 41, 55)   # #1f2937
    BOX_BG = (15, 15, 30)    # #0f0f1e
    BOX_BORDER = (31, 41, 55)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Top and bottom gradient bars
    _draw_gradient_bar(draw, W, 0, height=8)
    _draw_gradient_bar(draw, W, H - 8, height=8)

    # y=30: "WEEKLY RECAP" centered, purple, bold, size 15
    _center_text(draw, "WEEKLY RECAP", _font(15, bold=True), 30, W, PURPLE)

    # y=60: week_label centered, white, bold, size 34
    _center_text(draw, week_label, _font(34, bold=True), 60, W, WHITE)

    # y=105: user_name centered, gray, size 20
    _center_text(draw, user_name or "Athlete", _font(20, bold=False), 105, W, GRAY)

    # y=145: horizontal divider
    draw.line([(20, 145), (W - 20, 145)], fill=DIVIDER, width=2)

    # ── 2×2 grid of stat boxes ────────────────────────────────────────────────
    # Each box: 360×190, gap 20, margin 20
    box_w, box_h = 360, 190
    gap = 20
    margin = 20
    grid_top = 175

    box_positions = [
        (margin, grid_top),                         # top-left
        (margin + box_w + gap, grid_top),           # top-right
        (margin, grid_top + box_h + gap),           # bottom-left
        (margin + box_w + gap, grid_top + box_h + gap),  # bottom-right
    ]

    # Prepare stat data
    cal_text = f"{avg_calories:.0f}" if avg_calories else "—"

    # Weight color: green if <= 0, red if > 0
    weight_color = (16, 185, 129) if weight_change_kg <= 0 else (248, 113, 113)  # #10b981 / #f87171

    stats = [
        (str(workouts), "SESSIONS", WHITE),
        (cal_text, "KCAL / DAY", WHITE),
        (str(prs_hit), "RECORDS SET", WHITE),
        (f"{weight_change_kg:+.1f} KG", "WEIGHT", weight_color),
    ]

    corner_r = 12
    for (bx, by), (big_num, label, num_color) in zip(box_positions, stats):
        # Draw box background with rounded corners
        _draw_rounded_rect(
            draw, bx, by, bx + box_w, by + box_h,
            radius=corner_r,
            fill=BOX_BG,
            outline=BOX_BORDER,
            outline_width=1,
        )

        # Big number centered in box
        num_font = _font(64, bold=True)
        num_w, num_h = _text_size(draw, big_num, num_font)
        num_x = bx + (box_w - num_w) // 2
        num_y = by + (box_h - num_h) // 2 - 15
        draw.text((num_x, num_y), big_num, font=num_font, fill=num_color)

        # Label below
        lbl_font = _font(16, bold=False)
        lbl_w, lbl_h = _text_size(draw, label, lbl_font)
        lbl_x = bx + (box_w - lbl_w) // 2
        lbl_y = num_y + num_h + 8
        draw.text((lbl_x, lbl_y), label, font=lbl_font, fill=GRAY)

    # y=595: horizontal divider
    draw.line([(20, 595), (W - 20, 595)], fill=DIVIDER, width=2)

    # y=625: motivational quote, regular font, size 22
    _center_text(
        draw,
        "Keep showing up. That's the whole secret.",
        _font(22, bold=False),
        625,
        W,
        WHITE,
    )

    # y=680: CTA text, gray, size 18
    _center_text(draw, "Train with Apex — it's free", _font(18, bold=False), 680, W, GRAY)

    # y=720: horizontal divider
    draw.line([(20, 720), (W - 20, 720)], fill=DIVIDER, width=2)

    # y=760: placeholder CTA, purple, bold, size 20
    _center_text(
        draw,
        "Text +1 (555) APEX-FIT to start",
        _font(20, bold=True),
        760,
        W,
        PURPLE,
    )

    # y=800: "apex.fit" centered, gray, size 16
    _center_text(draw, "apex.fit", _font(16, bold=False), 800, W, GRAY)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
