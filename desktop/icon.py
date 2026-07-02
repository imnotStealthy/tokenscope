"""Shared TokenScope app icon (drawn with Pillow so the tray and the .ico stay in sync).

A monochrome ascending bar chart on a rounded dark square — matches the dashboard's
control-room aesthetic. Run this module directly to (re)generate tokenscope.ico/.png.
"""


def make_icon(size=256, badge=None):
    """badge: None | 'warn' | 'bad' — colored dot (top-right) showing quota pressure
    so the tray icon itself signals when a subscription window is nearly exhausted."""
    from PIL import Image, ImageDraw

    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded dark square with a faint border
    d.rounded_rectangle([6, 6, S - 6, S - 6], radius=54, fill=(0, 0, 0, 255),
                        outline=(63, 63, 70, 255), width=5)

    # ascending bar chart (token usage growing), white -> grey
    base_y = 198
    left, right = 56, S - 56
    heights = [80, 116, 152, 188]
    cols = [(113, 113, 122, 255), (161, 161, 170, 255), (212, 212, 216, 255), (255, 255, 255, 255)]
    n = len(heights)
    gap = 14
    bw = ((right - left) - gap * (n - 1)) / n
    x = left
    for h, c in zip(heights, cols):
        d.rounded_rectangle([x, base_y - h, x + bw, base_y], radius=7, fill=c)
        x += bw + gap

    if badge:
        col = (255, 59, 48, 255) if badge == "bad" else (255, 204, 0, 255)
        d.ellipse([S - 86, 22, S - 22, 86], fill=col, outline=(0, 0, 0, 255), width=8)

    if size != S:
        img = img.resize((size, size), Image.LANCZOS)
    return img


if __name__ == "__main__":
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    base = make_icon(256)
    base.save(os.path.join(here, "tokenscope.ico"),
              sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    base.save(os.path.join(here, "tokenscope.png"))
    print("wrote tokenscope.ico + tokenscope.png")
