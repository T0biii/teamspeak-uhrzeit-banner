import math
import os
import random
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

WIDTH = int(os.getenv("WIDTH", "468"))
HEIGHT = int(os.getenv("HEIGHT", "120"))
TZ = ZoneInfo(os.getenv("TZ", "Europe/Berlin"))
PORT = int(os.getenv("PORT", "8080"))
SHOW_SECONDS = os.getenv("SHOW_SECONDS", "false").lower() == "true"

FONT_TIME = "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Bold.otf"
FONT_BOLD = "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/montserrat/Montserrat-Medium.ttf"

# Gezeichnet wird in dreifacher Auflösung und am Ende herunterskaliert (glatte Kanten).
S = 3
W, H = WIDTH * S, HEIGHT * S

ACCENT_A = (0, 235, 200)    # Türkis
ACCENT_B = (150, 90, 255)   # Violett
ACCENT_C = (255, 80, 160)   # Pink

DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]


def font(path, size):
    return ImageFont.truetype(path, int(size * S))


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_background() -> Image.Image:
    img = Image.new("RGB", (W, H), (7, 9, 18))

    # Aurora: weiche, farbige Lichtflecken
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((-50 * S, 55 * S, 150 * S, 190 * S), fill=ACCENT_A)
    d.ellipse((150 * S, -80 * S, 330 * S, 40 * S), fill=ACCENT_B)
    d.ellipse((W - 170 * S, 50 * S, W + 50 * S, 190 * S), fill=ACCENT_C)
    glow = glow.filter(ImageFilter.GaussianBlur(34 * S))
    img = ImageChops.add(img, glow.point(lambda v: int(v * 0.62)))

    # feines Filmkorn
    random.seed(7)
    noise = Image.effect_noise((W, H), 30).convert("RGB")
    img = ImageChops.add(img, noise.point(lambda v: max(0, v - 118) // 3))
    img = img.convert("RGBA")

    # Glas-Panel
    inset, radius = 7 * S, 14 * S
    box = (inset, inset, W - inset, H - inset)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)

    tint = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    tint.putalpha(mask.point(lambda v: int(v * 0.07)))
    img = Image.alpha_composite(img, tint)

    # Glanzlicht oben im Panel
    hl = Image.linear_gradient("L").rotate(180).resize((W, H))
    hl = ImageChops.multiply(hl, mask).point(lambda v: int(v * 0.16))
    hl_layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    hl_layer.putalpha(hl)
    img = Image.alpha_composite(img, hl_layer)

    # Rand: oben hell, unten dunkel
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(box, radius=radius, outline=(255, 255, 255, 255), width=S)
    fade = Image.linear_gradient("L").rotate(180).resize((W, H)).point(lambda v: 45 + int(v * 0.5))
    border.putalpha(ImageChops.multiply(border.getchannel("A"), fade))
    img = Image.alpha_composite(img, border)

    line_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(line_layer)
    d = ImageDraw.Draw(img)
    sx = int(W * 0.715)
    for y in range(int(H * 0.22), int(H * 0.78)):
        t = 1 - abs((y - H / 2) / (H * 0.28))
        d.line((sx, y, sx, y), fill=(255, 255, 255, int(70 * max(0, min(1, t)))), width=S)
    return Image.alpha_composite(img, line_layer)


BACKGROUND = make_background()
F_TIME = font(FONT_TIME, HEIGHT * 0.80)
F_ABBR = font(FONT_BOLD, HEIGHT * 0.12)
F_DAY = font(FONT_BOLD, HEIGHT * 0.092)
F_YEAR = font(FONT_REG, HEIGHT * 0.1)

_cache = {"key": None, "png": b""}
_lock = threading.Lock()


def spaced(draw, xy, text, fnt, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="lm")
        x += draw.textlength(ch, font=fnt) + spacing


def ring_color(t):
    return mix(ACCENT_A, ACCENT_B, t * 2) if t < 0.5 else mix(ACCENT_B, ACCENT_C, (t - 0.5) * 2)


def draw_ring(img, cx, cy, r, width, progress):
    """Tagesfortschritt als Ring mit Farbverlauf und runden Enden."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bbox = (cx - r, cy - r, cx + r, cy + r)
    d.arc(bbox, 0, 360, fill=(255, 255, 255, 30), width=width)
    # Mindestens ein kleines Stück zeigen, damit der Ring zu Tagesbeginn nicht leer wirkt
    total = max(360 * progress, 6)
    steps = max(1, int(total / 1.5))
    for i in range(steps):
        a0 = total * i / steps
        a1 = total * (i + 1) / steps + 1
        d.arc(bbox, -90 + a0, -90 + a1, fill=ring_color(a1 / 360) + (255,), width=width)
    # runde Enden
    for ang in (0, total):
        x = cx + r * math.cos(math.radians(ang - 90))
        y = cy + r * math.sin(math.radians(ang - 90))
        d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2),
                  fill=ring_color(min(1, ang / 360)) + (255,))
    return Image.alpha_composite(img, layer)


def render(now: datetime) -> bytes:
    time_txt = now.strftime("%H:%M:%S" if SHOW_SECONDS else "%H:%M")
    secs = now.hour * 3600 + now.minute * 60 + now.second
    cy = H // 2

    # Ring links mit Wochentag-Kürzel
    ring_cx, ring_r = int(W * 0.125), int(H * 0.30)
    img = BACKGROUND.copy()
    img = draw_ring(img, ring_cx, cy, ring_r, 5 * S, secs / 86400)
    d = ImageDraw.Draw(img)
    d.text((ring_cx, cy), DAYS[now.weekday()][:2].upper(), font=F_ABBR, fill=(255, 255, 255),
           anchor="mm")

    # Uhrzeit mit Leuchten
    tx = int(W * 0.235)
    ty = int(H * 0.53)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).text((tx, ty), time_txt, font=F_TIME, fill=ACCENT_A + (255,), anchor="lm")
    halo = halo.filter(ImageFilter.GaussianBlur(7 * S))
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v * 0.55)))
    img = Image.alpha_composite(img, halo)
    d = ImageDraw.Draw(img)
    d.text((tx + S, ty + 2 * S), time_txt, font=F_TIME, fill=(0, 0, 0, 120), anchor="lm")
    d.text((tx, ty), time_txt, font=F_TIME, fill=(255, 255, 255), anchor="lm")

    # Datumsspalte rechts
    rx = int(W * 0.745)
    avail = W - rx - 14 * S
    day_txt = DAYS[now.weekday()].upper()
    month_txt = f"{now.day}. {MONTHS[now.month - 1]}".upper()

    def fit(text, path, size, spacing):
        f = font(path, size)
        while size > 6 and sum(d.textlength(c, font=f) + spacing for c in text) > avail:
            size -= 0.25
            f = font(path, size)
        return f

    f_day = fit(day_txt, FONT_BOLD, HEIGHT * 0.105, 1.5 * S)
    f_date = fit(month_txt, FONT_BOLD, HEIGHT * 0.092, 1 * S)
    spaced(d, (rx, int(H * 0.34)), day_txt, f_day, ACCENT_A + (255,), 1.5 * S)
    spaced(d, (rx, int(H * 0.52)), month_txt, f_date, (255, 255, 255, 255), 1 * S)
    d.text((rx, int(H * 0.69)), str(now.year), font=F_YEAR, fill=(160, 170, 205, 255), anchor="lm")

    out = img.convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def get_png() -> bytes:
    now = datetime.now(TZ)
    key = now.strftime("%Y%m%d%H%M%S") if SHOW_SECONDS else now.strftime("%Y%m%d%H%M")
    with _lock:
        if _cache["key"] != key:
            _cache["png"] = render(now)
            _cache["key"] = key
        return _cache["png"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if path in ("/", "/banner.png", "/clock.png"):
            png = get_png()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(png)
            return
        self.send_error(404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Banner-Server läuft auf Port {PORT} ({WIDTH}x{HEIGHT}, {TZ})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
