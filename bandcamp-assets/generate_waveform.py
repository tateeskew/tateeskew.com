#!/usr/bin/env python3
"""
Generate Waveform Bleed v4 — Bold dramatic waveforms.
Uses thick anti-aliased strokes and glow effects for visual richness.
"""

import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HEADER_W = 975
HEADER_H = 180
BG_W = 3840
BG_H = 2160
MASTER_W = BG_W
MASTER_H = HEADER_H + BG_H
COL_LEFT = (BG_W - HEADER_W) // 2
COL_RIGHT = COL_LEFT + HEADER_W

BG_COLOR = (11, 14, 24)
BODY_COLOR = (16, 20, 32)
TEXT_COLOR = (232, 224, 208)
GOLD = (218, 182, 92)

random.seed(42)


def wave_y(t, amp, freq, phase, harmonics=True):
    """Calculate y position for a flowing waveform at parameter t."""
    y = amp * math.sin(2 * math.pi * freq * t + phase)
    if harmonics:
        y += amp * 0.3 * math.sin(2 * math.pi * freq * 2.17 * t + phase * 1.3)
        y += amp * 0.18 * math.sin(2 * math.pi * freq * 3.41 * t + phase * 0.7)
        y += amp * 0.1 * math.sin(2 * math.pi * freq * 5.03 * t + phase * 2.1)
    return y


def draw_glow_line(draw, points, color, base_width=3, glow_radius=3):
    """Draw a line with glow effect by drawing multiple passes."""
    # Outer glow (wider, dimmer)
    for r in range(glow_radius, 0, -1):
        alpha = 0.1 + 0.15 * (1 - r / glow_radius)
        c = tuple(max(0, min(255, int(ch * alpha))) for ch in color)
        draw.line(points, fill=c, width=base_width + r * 2)
    # Core line
    draw.line(points, fill=color, width=base_width)


def generate_wave_points(x_start, x_end, y_center, amp, freq, phase, density=2):
    """Generate list of (x, y) points for a waveform."""
    points = []
    num = int(abs(x_end - x_start) / density)
    for i in range(num + 1):
        t = i / max(num, 1)
        x = x_start + t * (x_end - x_start)
        y = y_center + wave_y(t, amp, freq, phase)
        points.append((x, y))
    return points


def draw_header_waveforms(draw, y_center, width):
    """Draw the big, dramatic, layered header waveforms."""
    # Waveform definitions: (y_offset, amplitude, frequency, phase, line_width, brightness)
    waves = [
        # Big sweeping background waves — very high amplitude for dramatic effect
        (0, 140, 0.7, 0.3, 5, 0.5),
        (-10, 120, 0.9, 1.5, 4, 0.45),
        (15, 130, 0.6, 3.8, 5, 0.4),
        (20, 110, 0.5, 5.2, 4, 0.35),

        # Primary visible waves - large amplitude, bold
        (-5, 100, 1.0, 0.0, 5, 0.95),
        (5, 90, 1.2, 1.2, 4, 0.9),
        (0, 110, 0.8, 2.5, 5, 0.95),
        (-10, 85, 1.4, 0.7, 4, 0.85),
        (10, 95, 1.1, 3.2, 4, 0.8),
        (-15, 105, 0.75, 4.5, 4, 0.7),

        # Medium detail waves - crossing patterns
        (-15, 70, 1.6, 1.8, 3, 0.65),
        (8, 65, 1.8, 2.8, 3, 0.6),
        (-8, 75, 1.3, 4.0, 3, 0.7),
        (12, 60, 2.0, 0.5, 3, 0.55),
        (0, 80, 1.5, 5.5, 3, 0.6),

        # Fine detail / texture waves
        (0, 45, 2.5, 1.0, 2, 0.4),
        (-5, 40, 2.8, 2.2, 2, 0.35),
        (5, 50, 2.2, 3.5, 2, 0.45),
        (0, 35, 3.5, 0.8, 2, 0.3),
        (3, 30, 4.0, 1.5, 1, 0.25),
    ]

    for y_off, amp, freq, phase, lw, brightness in waves:
        y = y_center + y_off
        points = generate_wave_points(0, width, y, amp, freq, phase)
        color = tuple(max(0, min(255, int(c * brightness))) for c in GOLD)
        glow = 4 if lw >= 3 else 2
        draw_glow_line(draw, points, color, lw, glow)


def draw_seismograph(draw, x_start, x_end, y_center, intensity=1.0, width=2):
    """Draw detailed seismograph trace with variable activity."""
    points = []
    x = x_start
    while x < x_end:
        # Create sections of quiet and active
        section_t = (x - x_start) / max(x_end - x_start, 1)
        activity = 0.3 + 0.7 * abs(math.sin(section_t * 8 + random.random()))

        spike = random.random()
        if spike > 0.92:
            jitter = random.gauss(0, 25 * intensity * activity)
        elif spike > 0.7:
            jitter = random.gauss(0, 12 * intensity * activity)
        else:
            jitter = random.gauss(0, 4 * intensity * activity)
        points.append((x, y_center + jitter))
        x += random.uniform(1, 3)

    if len(points) > 1:
        brightness = 0.4 + intensity * 0.4
        color = tuple(max(0, min(255, int(c * brightness))) for c in GOLD)
        draw_glow_line(draw, points, color, width, 2)


def draw_contour_field(draw, ox, oy, num_lines, angle_start, angle_end,
                       bright=1.0, spacing=16):
    """Draw concentric topographic contour curves."""
    for i in range(num_lines):
        points = []
        base_r = 60 + i * spacing
        b = bright * max(0.15, 1 - i / num_lines * 0.6)
        color = tuple(max(0, min(255, int(c * b))) for c in GOLD)

        for step in range(250):
            t = step / 249
            angle = math.radians(angle_start + t * (angle_end - angle_start))
            r = base_r
            r += base_r * 0.07 * math.sin(angle * 3 + i * 0.35)
            r += base_r * 0.04 * math.sin(angle * 7 + i * 0.2)
            r += base_r * 0.025 * math.sin(angle * 11 + i * 0.5)
            x = ox + r * math.cos(angle)
            y = oy - r * math.sin(angle)
            points.append((x, y))

        if len(points) > 1:
            w = 3 if i < num_lines * 0.3 else 2 if i < num_lines * 0.7 else 1
            draw_glow_line(draw, points, color, w, 2 if i < num_lines // 2 else 1)


def draw_organic_edge(draw, x_center, y_start, y_end, side='left'):
    """Draw organic curved boundary for column edge."""
    points = []
    y = y_start
    while y < y_end:
        t = (y - y_start) / (y_end - y_start)
        offset = 35 * math.sin(t * 5.5 + 1.2)
        offset += 22 * math.sin(t * 9.3 + 3.4)
        offset += 14 * math.sin(t * 15.7 + 0.8)
        offset += 8 * math.sin(t * 23 + 2.1)
        if side == 'left':
            x = x_center - abs(offset) - 10
        else:
            x = x_center + abs(offset) + 10
        points.append((x, y))
        y += 2

    if len(points) > 1:
        color = tuple(max(0, min(255, int(c * 0.5))) for c in GOLD)
        draw_glow_line(draw, points, color, 2, 4)


def main():
    print("Creating 4K master canvas...")
    master = Image.new('RGB', (MASTER_W, MASTER_H), BG_COLOR)
    draw = ImageDraw.Draw(master)

    # Content column fill
    draw.rectangle([COL_LEFT, 0, COL_RIGHT, MASTER_H], fill=BODY_COLOR)

    # === HEADER ===
    print("Drawing header waveforms (bold, dramatic)...")
    draw_header_waveforms(draw, HEADER_H // 2, MASTER_W)

    # === TEXT ===
    print("Drawing header text...")
    try:
        font = ImageFont.truetype(
            '/usr/share/fonts/noto/NotoSans-CondensedExtraBold.ttf', 120
        )
    except Exception:
        font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', 100)

    text = "TATE ESKEW"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = COL_LEFT + (HEADER_W - tw) // 2
    ty = HEADER_H // 2 - th // 2 - 8

    # Draw text with strong outline/shadow for readability against waveforms
    # Multiple shadow passes for thickness
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if dx*dx + dy*dy <= 20:  # circular shadow
                draw.text((tx + dx, ty + dy), text, fill=BODY_COLOR, font=font)
    # Subtle glow shadow
    draw.text((tx + 2, ty + 2), text, fill=(6, 8, 14), font=font)
    draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)

    # Redraw some waveforms over text edges for weaving
    weave_waves = [
        (0, 100, 1.0, 0.0, 4, 0.8),
        (-10, 80, 1.3, 1.2, 3, 0.6),
        (5, 90, 0.9, 2.5, 4, 0.7),
        (-5, 70, 1.5, 4.0, 3, 0.5),
    ]
    for y_off, amp, freq, phase, lw, brightness in weave_waves:
        y = HEADER_H // 2 + y_off
        pts_left = generate_wave_points(0, tx + tw // 5, y, amp, freq, phase)
        pts_right = generate_wave_points(tx + tw * 4 // 5, MASTER_W, y, amp, freq, phase)
        color = tuple(max(0, min(255, int(c * brightness))) for c in GOLD)
        draw_glow_line(draw, pts_left, color, lw, 2)
        draw_glow_line(draw, pts_right, color, lw, 2)

    # === BACKGROUND ===
    bg_top = HEADER_H

    # Left: seismograph traces
    print("Drawing seismograph traces...")
    traces = [
        (bg_top + 300, 0.7), (bg_top + 380, 0.9), (bg_top + 460, 1.1),
        (bg_top + 540, 0.8), (bg_top + 620, 0.6),
        (bg_top + 900, 1.0), (bg_top + 980, 0.7), (bg_top + 1060, 0.5),
        (bg_top + 1400, 0.4), (bg_top + 1480, 0.6),
    ]
    for y_pos, intensity in traces:
        x0 = random.randint(30, 120)
        x1 = COL_LEFT - random.randint(15, 70)
        draw_seismograph(draw, x0, x1, y_pos, intensity, 2)

    # Left organic edge
    print("Drawing organic edges...")
    draw_organic_edge(draw, COL_LEFT, bg_top + 80, bg_top + 1600, 'left')

    # Right: contour curves
    print("Drawing contour fields...")
    draw_contour_field(draw, MASTER_W + 80, MASTER_H + 120, 50,
                       85, 175, bright=0.85, spacing=18)
    draw_contour_field(draw, MASTER_W + 60, bg_top + 450, 28,
                       95, 180, bright=0.45, spacing=15)

    # Right organic edge
    draw_organic_edge(draw, COL_RIGHT, bg_top + 120, bg_top + 1400, 'right')

    # Transition waveforms from header into background sides
    print("Drawing transitions...")
    for i, (y_off, amp, freq, phase) in enumerate([
        (40, 55, 1.0, 0.5), (70, 45, 1.3, 1.2),
        (100, 38, 1.6, 2.0), (140, 30, 1.8, 2.8),
        (180, 22, 2.1, 3.5), (230, 18, 2.3, 4.0),
    ]):
        y = bg_top + y_off
        b = max(0.12, 0.6 - i * 0.08)
        color = tuple(max(0, min(255, int(c * b))) for c in GOLD)
        pts_l = generate_wave_points(0, COL_LEFT + 50, y, amp, freq, phase)
        pts_r = generate_wave_points(COL_RIGHT - 50, MASTER_W, y, amp, freq, phase + 0.5)
        draw_glow_line(draw, pts_l, color, 2, 2)
        draw_glow_line(draw, pts_r, color, 2, 2)

    # Bottom-left trailing traces
    for i in range(6):
        y = MASTER_H - 500 + i * 65
        draw_seismograph(draw, 40, COL_LEFT - 50 + random.randint(-100, 50), y, 0.3 + i * 0.08, 1)

    # === EXPORT ===
    print("Exporting...")
    header = master.crop((COL_LEFT, 0, COL_RIGHT, HEADER_H))
    header.save('/home/teskew/sourcecode/tateeskew.com/bandcamp-assets/waveform_header.png', 'PNG')
    master.save('/home/teskew/sourcecode/tateeskew.com/bandcamp-assets/waveform_background.jpg', 'JPEG', quality=95)

    # Reference with alignment guides
    ref = master.copy()
    rd = ImageDraw.Draw(ref)
    for y in range(0, MASTER_H, 30):
        rd.line([(COL_LEFT, y), (COL_LEFT, y+15)], fill=(255, 50, 50), width=1)
        rd.line([(COL_RIGHT, y), (COL_RIGHT, y+15)], fill=(255, 50, 50), width=1)
    for x in range(0, MASTER_W, 30):
        rd.line([(x, HEADER_H), (x+15, HEADER_H)], fill=(50, 255, 50), width=1)
    ref.save('/home/teskew/sourcecode/tateeskew.com/bandcamp-assets/waveform_master_reference.jpg', 'JPEG', quality=85)

    import os
    for f in ['waveform_header.png', 'waveform_background.jpg']:
        p = f'/home/teskew/sourcecode/tateeskew.com/bandcamp-assets/{f}'
        print(f"  {f}: {os.path.getsize(p)/1024:.0f} KB")

    print(f"\n✅ Done! 4K assets ({MASTER_W}×{MASTER_H}) from unified canvas")
    print(f"  Header:  975×180 sliced from center column")
    print(f"  Body:    #101420 | BG: #0B0E18")


if __name__ == '__main__':
    main()
