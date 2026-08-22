from PIL import Image, ImageDraw, ImageFont
import math, os

def hex_points(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 90)),
             cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]

def draw_hex(draw, cx, cy, r, color, width=2):
    pts = hex_points(cx, cy, r)
    draw.polygon(pts, outline=color, fill=None)
    draw.line(pts + [pts[0]], fill=color, width=width)

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def gen_icon(size, filename):
    img = Image.new('RGBA', (size, size), (8, 12, 22, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    # Corner radius
    r = size // 8
    mask = Image.new('L', (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, size-1, size-1], radius=r, fill=255)

    # Gradient colors
    cyan = (0, 229, 255)
    purple = (124, 77, 255)

    # Border
    for i in range(4):
        t = i / 4
        col = lerp_color(cyan, purple, t)
        border = [i, i, size-1-i, size-1-i]
        draw.rounded_rectangle(border, radius=r, outline=col)

    # Outer hexagon
    outer_r = size * 0.38
    hex_pts = hex_points(cx, cy, outer_r)
    draw.polygon(hex_pts, outline=cyan, fill=None)
    # Thicken
    for offset in range(2):
        r2 = outer_r + offset * 0.5
        pts = hex_points(cx, cy, r2)
        draw.line(pts + [pts[0]], fill=cyan, width=2)

    # Inner hexagon
    inner_r = size * 0.26
    ihex = hex_points(cx, cy, inner_r)
    draw.line(ihex + [ihex[0]], fill=(*cyan, 90), width=1)

    # Signal arcs (3 curved lines)
    for idx, (y_off, alpha) in enumerate([(0.04, 140), (0.12, 110), (0.20, 80)]):
        arc_y = cy - size * y_off
        arc_w = size * (0.28 - idx * 0.04)
        col = (*cyan, alpha)
        pts = []
        for x_i in range(20):
            t = x_i / 19
            x = cx - arc_w + 2 * arc_w * t
            y = arc_y + math.sin(t * math.pi) * size * 0.03
            pts.append((x, y))
        if len(pts) > 1:
            draw.line(pts, fill=col, width=2)

    # "ZI" text
    try:
        zi_size = int(size * 0.28)
        zi_font = ImageFont.truetype("arial.ttf", zi_size)
    except:
        zi_font = ImageFont.load_default()

    zi_bbox = draw.textbbox((0, 0), "ZI", font=zi_font)
    zi_w = zi_bbox[2] - zi_bbox[0]
    zi_h = zi_bbox[3] - zi_bbox[1]
    draw.text((cx - zi_w // 2, cy - zi_h // 2 - size * 0.06), "ZI",
              fill=cyan, font=zi_font)

    # "CHAT" text
    try:
        chat_size = int(size * 0.08)
        chat_font = ImageFont.truetype("arial.ttf", chat_size)
    except:
        chat_font = ImageFont.load_default()

    chat_bbox = draw.textbbox((0, 0), "CHAT", font=chat_font)
    chat_w = chat_bbox[2] - chat_bbox[0]
    draw.text((cx - chat_w // 2, cy + zi_h // 2 + size * 0.02), "CHAT",
              fill=(122, 139, 168), font=chat_font)

    # Apply rounded mask
    img.putalpha(mask)

    out = os.path.join(os.path.dirname(__file__), filename)
    img.save(out, 'PNG')
    print(f"Saved {out} ({size}x{size})")

def gen_favicon(size, filename):
    img = Image.new('RGBA', (size, size), (8, 12, 22, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    cyan = (0, 229, 255)
    purple = (124, 77, 255)

    # Outer hexagon
    hex_pts = hex_points(cx, cy, size * 0.42)
    draw.line(hex_pts + [hex_pts[0]], fill=cyan, width=max(2, size // 20))

    # Z letter
    try:
        z_size = int(size * 0.45)
        z_font = ImageFont.truetype("arial.ttf", z_size)
    except:
        z_font = ImageFont.load_default()

    z_bbox = draw.textbbox((0, 0), "Z", font=z_font)
    z_w = z_bbox[2] - z_bbox[0]
    z_h = z_bbox[3] - z_bbox[1]
    draw.text((cx - z_w // 2, cy - z_h // 2 - 1), "Z", fill=cyan, font=z_font)

    out = os.path.join(os.path.dirname(__file__), filename)
    img.save(out, 'PNG')
    print(f"Saved {out} ({size}x{size})")

base = r"C:\Users\zinem\Documents\zicore-system\frontend\img"
os.makedirs(base, exist_ok=True)

gen_icon(512, os.path.join(base, "zichat-icon-512.png"))
gen_icon(192, os.path.join(base, "zichat-icon-192.png"))
gen_icon(64, os.path.join(base, "zichat-icon-64.png"))
gen_favicon(32, os.path.join(base, "zichat-favicon-32.png"))
gen_favicon(16, os.path.join(base, "zichat-favicon-16.png"))
print("Done generating PNGs")
