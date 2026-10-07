#!/usr/bin/env python3
"""
Saltglass pack icon generator.

512x512, built from the six-colour palette in DESIGN.md, drawn procedurally so it is
reproducible and licence-clean (no third-party assets, no font dependency).

Composition: the upper half is a bleached salt flat under a pale sky; the lower half is
the mirror — the same scene inverted into Deep Glass teal, because in Saltglass the sea
is the reflection. A lighthouse stands on the horizon with Beacon Amber light.

Usage:  python3 tools/make_icon.py [output.png]
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
HORIZON = 236

SALT = (0xE8, 0xE3, 0xD6)
TEAL = (0x7F, 0xB4, 0xB0)
DEEP = (0x1D, 0x4C, 0x57)
ABYSS = (0x0A, 0x14, 0x18)
AMBER = (0xE0, 0xA3, 0x2E)
TAR = (0x8A, 0x5A, 0x3B)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def vgrad(draw, box, top, bottom, steps=128):
    x0, y0, x1, y1 = box
    h = max(1, y1 - y0)
    for i in range(steps):
        c = lerp(top, bottom, i / (steps - 1))
        y = y0 + int(h * i / steps)
        y_next = y0 + int(h * (i + 1) / steps)
        draw.rectangle([x0, y, x1, max(y + 1, y_next)], fill=c)


def hexagon(cx, cy, r, rot=math.pi / 6):
    return [
        (cx + r * math.cos(rot + i * math.pi / 3), cy + r * math.sin(rot + i * math.pi / 3))
        for i in range(6)
    ]


def salt_crust(draw, region, base, accent, seed=7):
    """Flat crystalline hatch: short pale strokes suggesting a salt pan."""
    x0, y0, x1, y1 = region
    n = seed
    for row in range(0, (y1 - y0), 11):
        n = (n * 1103515245 + 12345) & 0x7FFFFFFF
        for step in range(-40, (x1 - x0) + 40, 26):
            n = (n * 1103515245 + 12345) & 0x7FFFFFFF
            jx = (n >> 8) % 13 - 6
            length = 7 + ((n >> 20) % 12)
            y = y0 + row + ((n >> 16) % 5) - 2
            if not (y0 <= y <= y1):
                continue
            a = x0 + step + jx
            b = min(a + length, x1)
            if b - a < 4:
                continue
            draw.line([(a, y), (b, y + 1)], fill=accent, width=1)


def scene(draw, flip=False):
    """Draw one half of the composition. flip=True renders the reflection (in the mirror)."""
    x0, x1 = 0, SIZE
    if flip:
        # mirror: compressed vertically, in deep teal, with the water tint
        vgrad(draw, (x0, HORIZON, x1, SIZE), TEAL, DEEP)
        k = 0.52
        y_of = lambda y: HORIZON + int((SIZE - y - (SIZE - HORIZON)) * 0)  # noqa: E731
    else:
        vgrad(draw, (x0, 0, x1, HORIZON), SALT, lerp(SALT, TEAL, 0.35))


def lighthouse(draw, cx, base_y, height, scale=1.0, reflected=False):
    """A tapered salt-glazed tower with a lit amber lantern room."""
    w = 34 * scale
    wt = 22 * scale
    top_y = base_y - height
    body = SALT if not reflected else lerp(TEAL, DEEP, 0.45)
    shade = lerp(SALT, TAR, 0.35) if not reflected else lerp(DEEP, ABYSS, 0.5)
    # tower body
    draw.polygon(
        [(cx - w / 2, base_y), (cx + w / 2, base_y), (cx + wt / 2, top_y + 12 * scale),
         (cx - wt / 2, top_y + 12 * scale)],
        fill=body,
    )
    # shaded right face for volume
    draw.polygon(
        [(cx + w / 6, base_y), (cx + w / 2, base_y), (cx + wt / 2, top_y + 12 * scale),
         (cx + wt / 6, top_y + 12 * scale)],
        fill=shade,
    )
    # two tar bands: the Kettle Sea harbour pattern
    for frac in (0.34, 0.66):
        by = base_y - height * frac
        hw = w / 2 - (w - wt) / 2 * frac
        draw.rectangle([cx - hw, by - 5 * scale, cx + hw, by + 1 * scale],
                       fill=TAR if not reflected else lerp(TAR, DEEP, 0.55))
    # gallery
    gw = wt / 2 + 7 * scale
    draw.rectangle([cx - gw, top_y + 6 * scale, cx + gw, top_y + 12 * scale],
                   fill=TAR if not reflected else lerp(TAR, ABYSS, 0.4))
    # lantern room (the light itself)
    lw = wt / 2 + 1
    lantern = AMBER if not reflected else lerp(AMBER, TEAL, 0.5)
    draw.rectangle([cx - lw, top_y - 12 * scale, cx + lw, top_y + 6 * scale], fill=lantern)
    # roof
    draw.polygon(
        [(cx - lw - 3 * scale, top_y - 12 * scale), (cx + lw + 3 * scale, top_y - 12 * scale),
         (cx, top_y - 26 * scale)],
        fill=TAR if not reflected else lerp(TAR, ABYSS, 0.5),
    )
    # concentrated glow on the lantern: the pack's only warm accent
    for r, a in ((16, 60), (10, 100), (5, 200)):
        draw.ellipse([cx - r, top_y - 3 * scale - r, cx + r, top_y - 3 * scale + r],
                     fill=AMBER + (a,))
    return (cx, top_y - 3 * scale)


def beams(img, origin, spread, tint, alpha=120, reach=(0, 1.0)):
    """Soft amber light cone drawn onto an overlay then blurred."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = origin
    for ang in spread:
        for i, wdt in enumerate((26, 12, 5)):
            length = 460 * (1 + i * 0.12)
            a = math.radians(ang)
            x2 = cx + length * math.cos(a)
            y2 = cy + length * math.sin(a)
            d.line([(cx, cy), (x2, y2)], fill=tint + (max(20, alpha - i * 26),), width=wdt)
    layer = layer.filter(ImageFilter.GaussianBlur(9))
    img.alpha_composite(layer)


def build():
    img = Image.new("RGBA", (SIZE, SIZE), ABYSS + (255,))
    d = ImageDraw.Draw(img)

    # ---- upper world: the drained basin -----------------------------------
    vgrad(d, (0, 0, SIZE, HORIZON), lerp(SALT, (255, 255, 255), 0.45), SALT)
    # far salt ridges
    d.polygon([(0, HORIZON - 34), (96, HORIZON - 58), (168, HORIZON - 30), (232, HORIZON - 52),
               (310, HORIZON - 24), (392, HORIZON - 46), (462, HORIZON - 22), (SIZE, HORIZON - 36),
               (SIZE, HORIZON), (0, HORIZON)],
              fill=lerp(SALT, TEAL, 0.28))
    salt_crust(d, (0, HORIZON - 22, SIZE, HORIZON - 2), SALT, lerp(SALT, TEAL, 0.5))

    # stranded hull on the flat, right of the tower: a ship with no water
    hull = [(300, HORIZON - 12), (392, HORIZON - 12), (378, HORIZON - 30), (312, HORIZON - 30)]
    d.polygon(hull, fill=TAR)
    d.polygon([(312, HORIZON - 30), (378, HORIZON - 30), (372, HORIZON - 34), (318, HORIZON - 34)],
              fill=lerp(TAR, SALT, 0.4))
    d.line([(344, HORIZON - 34), (344, HORIZON - 66)], fill=lerp(TAR, SALT, 0.2), width=3)
    d.polygon([(344, HORIZON - 64), (344, HORIZON - 44), (368, HORIZON - 50)],
              fill=lerp(SALT, TAR, 0.15))

    # the lighthouse, standing on the crust
    top = lighthouse(d, 176, HORIZON - 4, 150, 1.0)

    # ---- the mirror -------------------------------------------------------
    d.rectangle([0, HORIZON - 2, SIZE, HORIZON + 3], fill=lerp(TEAL, SALT, 0.55))

    # ---- lower world: the reflection that is the sea ----------------------
    vgrad(d, (0, HORIZON + 3, SIZE, SIZE), lerp(DEEP, TEAL, 0.55), lerp(ABYSS, DEEP, 0.3))
    # inverted skyline pressed against the glass
    d.polygon([(0, HORIZON + 30), (96, HORIZON + 50), (168, HORIZON + 26), (232, HORIZON + 44),
               (310, HORIZON + 20), (392, HORIZON + 38), (462, HORIZON + 16), (SIZE, HORIZON + 28),
               (SIZE, HORIZON + 3), (0, HORIZON + 3)],
              fill=lerp(DEEP, TEAL, 0.45))
    refl_top = lighthouse(d, 176, HORIZON + 96, 92, 0.62, reflected=True)
    # the hull, upside down
    d.polygon([(300, HORIZON + 26), (392, HORIZON + 26), (378, HORIZON + 40), (312, HORIZON + 40)],
              fill=lerp(TAR, DEEP, 0.35))
    # cathedral spires under the glass — Act III, seen from above
    for sx, sw, sh in ((70, 16, 58), (410, 20, 74), (458, 12, 44)):
        d.polygon([(sx - sw, SIZE), (sx + sw, SIZE), (sx + sw * 0.55, SIZE - sh),
                   (sx - sw * 0.55, SIZE - sh)],
                  fill=lerp(DEEP, TEAL, 0.32))
        d.polygon([(sx - sw * 0.55, SIZE - sh), (sx + sw * 0.55, SIZE - sh), (sx, SIZE - sh - 18)],
                  fill=lerp(DEEP, TEAL, 0.5))
    # ripple lines across the reflection
    for row in range(HORIZON + 14, SIZE - 6, 9):
        n = (row * 2654435761) & 0x7FFFFFFF
        xoff = n % 34 - 17
        length = 40 + (n >> 12) % 90
        d.line([(40 + xoff, row), (40 + xoff + length, row)],
               fill=lerp(TEAL, SALT, 0.35) + (46,), width=1)
        x2 = 300 + ((n >> 8) % 120)
        d.line([(x2, row + 3), (x2 + length * 0.7, row + 3)], fill=lerp(TEAL, SALT, 0.3) + (34,), width=1)

    # ---- light ------------------------------------------------------------
    beams(img, top, (-150, -172, 178), AMBER, alpha=95)
    beams(img, refl_top, (22, -20), lerp(AMBER, TEAL, 0.55), alpha=60)

    # ---- corner darkening, so the icon reads on a light launcher ----------
    # Radial falloff from the centre: alpha 0 in the middle 60%, up to 120 at
    # the extreme corners only. Deliberately gentle — it must not fog the art.
    corners = []
    for cy in range(0, SIZE, 8):
        dy = HORIZON - cy
        for cx in range(0, SIZE, 8):
            dx = 256 - cx
            dmin = min(dx * dx, dy * dy) / max(1, (256 * 256 + HORIZON * HORIZON))
            corners.append(int(190 * max(0.0, dmin - 0.62)))
    vig = Image.new("L", (SIZE // 8 + 1, SIZE // 8 + 1), 0)
    vig.putdata(corners)
    vig = vig.resize((SIZE, SIZE), Image.BILINEAR).filter(ImageFilter.GaussianBlur(18))
    dark = Image.new("RGBA", (SIZE, SIZE), ABYSS + (255,))
    dark.putalpha(vig)
    img.alpha_composite(dark)

    # thin deep-glass frame so the icon reads on any launcher background
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, SIZE - 1, SIZE - 1], outline=DEEP + (255,), width=8)
    d.rectangle([8, 8, SIZE - 9, SIZE - 9], outline=lerp(SALT, TEAL, 0.4) + (120,), width=1)

    # rounded corners
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=72, fill=255)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def verify(img):
    """Cheap structural self-check: the composition must read as light over dark,
    split by a mirror line, with amber light in the upper-left-of-centre."""
    g = img.convert("L")
    top = sum(g.crop((0, 0, SIZE, HORIZON - 40)).getdata()) / (SIZE * (HORIZON - 40))
    bot = sum(g.crop((0, HORIZON + 40, SIZE, SIZE)).getdata()) / (SIZE * (SIZE - HORIZON - 40))
    rgb = img.convert("RGB")
    amber = sum(1 for p in rgb.getdata()
                if p[0] > 190 and 120 < p[1] < 200 and p[2] < 90)
    deep = sum(1 for p in rgb.getdata() if abs(p[0] - 0x1D) < 10 and abs(p[1] - 0x4C) < 10
               and abs(p[2] - 0x57) < 10)
    checks = [
        ("upper half brighter than lower", top > bot + 40, f"top={top:.0f} bottom={bot:.0f}"),
        ("amber lantern light present", amber > 900, f"{amber}px"),
        ("deep-glass reflection present", deep > 6000, f"{deep}px"),
    ]
    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print(f"  [{'ok' if passed else 'FAIL'}] {name} ({detail})")
    return ok


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "export/saltglass-icon/icon.png"
    img = build()
    img.save(path)
    print(f"wrote {path} {img.size[0]}x{img.size[1]}")
    for side in (256, 128, 64, 32):
        small = img.resize((side, side), Image.LANCZOS)
        p = path.replace("icon.png", f"icon-{side}.png")
        small.save(p)
        print(f"wrote {p}")
    print("icon composition check:")
    if not verify(img):
        print("WARNING: composition check failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
