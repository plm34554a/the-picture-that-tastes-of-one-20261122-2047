#!/usr/bin/env python3
"""The picture that tastes of one ingredient: a glossy halved orange.

Pure standard library only (zlib + struct). Renders one big, juicy orange
half, cut face toward the viewer, on a dark warm background. Writes a PNG
to $MAKEFUN_OUTPUT (default /output/entry.png).
"""
import math
import os
import struct
import zlib

W, H = 900, 900
CX, CY = 450, 460          # orange centre
R_OUT = 330                # outer rind radius
R_PITH = 298               # flesh radius (inside the cream pith ring)
NSEG = 12                  # juice segments
TAU = math.tau


def clamp(v, lo=0.0, hi=255.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


def hash2(ix, iy):
    """Deterministic pseudo-random in [0, 1) from integer cell coords."""
    h = (ix * 374761393 + iy * 668265263) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def png_encode(width, height, rows):
    """rows: list of bytes objects, each width*3 RGB bytes. Returns PNG bytes."""
    raw = b"".join(b"\x00" + row for row in rows)
    comp = zlib.compress(raw, 6)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def render():
    rows = []
    sqrt = math.sqrt
    sin = math.sin
    cos = math.cos
    atan2 = math.atan2
    exp = math.exp
    for y in range(H):
        row = bytearray(W * 3)
        dy_all = y - CY
        for x in range(W):
            dx = x - CX
            dy = dy_all
            r = sqrt(dx * dx + dy * dy)

            # ---- background: dark warm radial glow + vignette ----
            d = sqrt((x - 450.0) ** 2 + (y - 430.0) ** 2) / 640.0
            glow = exp(-d * d * 2.2)
            br = 26.0 + 52.0 * glow
            bg = 18.0 + 34.0 * glow
            bb = 12.0 + 18.0 * glow
            # vignette: darken corners
            vig = 1.0 - 0.28 * smooth((d - 0.55) / 0.55)
            r0, g0, b0 = br * vig, bg * vig, bb * vig

            # ---- plate: soft dark disc under the orange ----
            pdx, pdy = x - 450.0, (y - 470.0) * 1.06
            pr = sqrt(pdx * pdx + pdy * pdy)
            if pr < 405.0:
                t = smooth((405.0 - pr) / 26.0)
                r0 = lerp(r0, 52.0 + 22.0 * glow, t)
                g0 = lerp(g0, 40.0 + 14.0 * glow, t)
                b0 = lerp(b0, 32.0 + 10.0 * glow, t)

            # ---- soft shadow under the orange ----
            shx, shy = (x - 450.0) / 300.0, (y - 812.0) / 34.0
            sh = shx * shx + shy * shy
            if sh < 1.0:
                s = 0.5 * (1.0 - sh)
                r0 *= 1.0 - s
                g0 *= 1.0 - s
                b0 *= 1.0 - s

            if r <= R_OUT:
                ang = atan2(dy, dx)
                # ---- rind: deep orange skin with dimples ----
                if r > 312.0:
                    dimple = 0.5 + 0.5 * sin(x * 0.31) * sin(y * 0.27 + 1.7)
                    dimple *= 0.5 + 0.5 * sin(x * 0.11 + y * 0.13)
                    rr = 214.0 + 26.0 * dimple - 30.0 * smooth((r - 312.0) / 18.0)
                    gg = 92.0 + 18.0 * dimple
                    bb2 = 12.0 + 8.0 * dimple
                    # rind edge darkens toward the rim
                    edge = smooth((r - 322.0) / 8.0)
                    rr = lerp(rr, 150.0, edge)
                    gg = lerp(gg, 58.0, edge)
                    r0, g0, b0 = rr, gg, bb2
                # ---- pith: pale cream ring ----
                elif r > R_PITH:
                    t = smooth((r - R_PITH) / 14.0)
                    rr = lerp(255.0, 232.0, t)
                    gg = lerp(214.0, 176.0, t)
                    bb2 = lerp(150.0, 96.0, t)
                    r0, g0, b0 = rr, gg, bb2
                # ---- flesh: juicy segments ----
                else:
                    seg = (ang + TAU) % (TAU / NSEG)
                    half = TAU / NSEG / 2.0
                    # distance from segment centre line (0 at centre, 1 at membrane)
                    off = abs(seg - half) / half
                    # radial gradient: bright heart, deep orange mid, lighter rim
                    rt = r / R_PITH
                    base_r = lerp(255.0, 252.0, rt)
                    base_g = lerp(158.0, 118.0, rt)
                    base_b = lerp(38.0, 6.0, rt)
                    # segment shading: darker toward membranes, brighter centre
                    shade = 1.0 - 0.28 * smooth((off - 0.55) / 0.45)
                    rr = base_r * shade
                    gg = base_g * shade
                    bb2 = base_b * shade
                    # juice vesicles: tiny bright dots in a jittered grid
                    cell = 9.0
                    gx = int((x + 4.0) // cell)
                    gy = int((y + 4.0) // cell)
                    hv = hash2(gx, gy)
                    if hv > 0.74:
                        jx = gx * cell + hv * cell - 4.0
                        jy = gy * cell + hash2(gx + 7, gy + 3) * cell - 4.0
                        ddx, ddy = x - jx, y - jy
                        if ddx * ddx + ddy * ddy < 4.0:
                            rr = lerp(rr, 255.0, 0.55)
                            gg = lerp(gg, 205.0, 0.55)
                            bb2 = lerp(bb2, 110.0, 0.55)
                    # pale membranes between segments
                    mem = smooth((off - 0.90) / 0.10)
                    rr = lerp(rr, 255.0, mem * 0.85)
                    gg = lerp(gg, 226.0, mem * 0.85)
                    bb2 = lerp(bb2, 150.0, mem * 0.85)
                    # central core: pale star
                    if r < 30.0:
                        t = smooth((30.0 - r) / 30.0)
                        rr = lerp(rr, 255.0, t * 0.9)
                        gg = lerp(gg, 232.0, t * 0.9)
                        bb2 = lerp(bb2, 165.0, t * 0.9)
                    r0, g0, b0 = rr, gg, bb2

                # ---- gloss: big soft specular highlight, top-left ----
                for (hx, hy, hr, amt) in ((-150.0, -165.0, 95.0, 0.55),
                                          (120.0, -185.0, 55.0, 0.35),
                                          (-215.0, 60.0, 60.0, 0.22)):
                    gx = (x - (CX + hx)) / hr
                    gy = (y - (CY + hy)) / (hr * 0.62)
                    g2 = gx * gx + gy * gy
                    if g2 < 1.0:
                        a = amt * (1.0 - g2)
                        r0 = lerp(r0, 255.0, a)
                        g0 = lerp(g0, 240.0, a)
                        b0 = lerp(b0, 200.0, a)

            i = x * 3
            row[i] = int(clamp(r0))
            row[i + 1] = int(clamp(g0))
            row[i + 2] = int(clamp(b0))
        rows.append(bytes(row))
    return rows


def main():
    out = os.environ.get("MAKEFUN_OUTPUT", "/output/entry.png")
    rows = render()
    data = png_encode(W, H, rows)
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    os.chmod(out, 0o644)
    print(f"wrote {out}: {len(data)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
