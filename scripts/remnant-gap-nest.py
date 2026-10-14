"""Generates src/components/remnant-gap-nest.json for HeroNestFigure.astro and RemnantGapFigure.astro.

Dense left-packed nests for a 3000 x 1500 mm sheet, an irregular remnant, and the largest
clean rectangle inside that remnant. 1 unit = 5 mm.

Placement runs on a 2.5 mm raster: every candidate position for every rotation is tested at once
with an FFT correlation against the occupancy grid. Both the grid and the part masks are dilated
conservatively, so a free raster cell guarantees real clearance. The final layout is then
re-checked with exact geometry.

    pip install shapely numpy scipy && python3 scripts/remnant-gap-nest.py
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.signal import correlate
from shapely import affinity, contains_xy
from shapely.geometry import Point, Polygon, box

CELL = 0.5    # raster resolution (2.5 mm)
GAP = 1.0     # part-to-part spacing (5 mm)
MARGIN = 1.0  # sheet edge trim (5 mm)
R = CELL * 0.75  # conservative dilation, >= half the cell diagonal

plate = box(0, 0, 600, 300)
remnant_outline = Polygon([(0, 0), (330, 0), (330, 50), (365, 85), (420, 85), (420, 135),
                           (500, 135), (535, 180), (600, 180), (600, 300), (55, 300), (0, 245)])
hole_circle = Point(110, 215).buffer(30, quad_segs=12)
hole_slot = box(215, 50, 285, 92)
remnant = remnant_outline.difference(hole_circle).difference(hole_slot)
consumed = plate.difference(remnant_outline)


# ---------- part library ----------

def rounded(g, r):
    return g.buffer(-r, quad_segs=3).buffer(r, quad_segs=3)

def holes(g, *circles):
    for x, y, r in circles:
        g = g.difference(Point(x, y).buffer(r, quad_segs=3))
    return g

LIB = {
    'rail': holes(rounded(box(0, 0, 120, 18), 1.5), (7, 9, 2.2), (113, 9, 2.2)),
    'cover': holes(rounded(Polygon([(0, 0), (64, 0), (64, 26), (56, 34), (0, 34)]), 1.5),
                   (5, 5, 1.6), (59, 5, 1.6), (5, 29, 1.6)),
    'bracket': holes(rounded(Polygon([(0, 0), (70, 0), (70, 14), (14, 14), (14, 44), (0, 44)]), 1.2),
                     (7, 7, 2.4), (62, 7, 2.4), (7, 36, 2.4)),
    'tee': holes(rounded(Polygon([(0, 0), (56, 0), (56, 14), (37, 14), (37, 40), (19, 40), (19, 14), (0, 14)]), 1.2),
                 (8, 7, 2), (48, 7, 2), (28, 32, 2.4)),
    'hex': holes(rounded(Polygon([(0, 0), (44, 0), (55, 22), (38, 33), (6, 33), (0, 16)]), 1.2),
                 (14, 16, 3), (36, 16, 3)),
    'flange': holes(rounded(Polygon([(0, 0), (60, 0), (52, 22), (8, 22)]), 1.2), (14, 9, 2.2), (46, 9, 2.2)),
    'gusset': holes(rounded(Polygon([(0, 0), (36, 0), (36, 5), (5, 30), (0, 30)]), 1), (8, 7, 2.2)),
    'tab': holes(rounded(box(0, 0, 18, 12), 2.5), (9, 6, 2)),
    'disc': holes(Point(10, 10).buffer(10, quad_segs=8), (10, 10, 3.5)),
}
JOB = [('rail', 8), ('cover', 12), ('bracket', 10), ('tee', 8), ('hex', 8), ('flange', 8),
       ('gusset', 14), ('tab', 28), ('disc', 10)]
QUEUE = [name for name, n in JOB for _ in range(n)]


def norm(g):
    minx, miny, _, _ = g.bounds
    return affinity.translate(g, -minx, -miny)

def variants(name):
    seen, out = set(), []
    for a in (0, 90, 180, 270):
        g = norm(affinity.rotate(LIB[name], a, origin=(0, 0)))
        key = tuple(round(v, 1) for v in g.bounds) + (round(g.centroid.x, 1), round(g.centroid.y, 1))
        if key not in seen:
            seen.add(key)
            out.append(g)
    return out


# ---------- raster nesting ----------

def cells_in(geom, rows, cols):
    """Boolean mask of raster cells (rows x cols, origin 0,0) whose centres fall inside geom."""
    ys = (np.arange(rows) + 0.5) * CELL
    xs = (np.arange(cols) + 0.5) * CELL
    X, Y = np.meshgrid(xs, ys)
    return contains_xy(geom, X, Y)

def part_mask(g):
    k = math.ceil(R / CELL) + 1
    rows = math.ceil(g.bounds[3] / CELL) + 2 * k
    cols = math.ceil(g.bounds[2] / CELL) + 2 * k
    return cells_in(affinity.translate(Polygon(g.exterior).buffer(R), k * CELL, k * CELL), rows, cols), k

def nest(container, queue, limit=None, occ=None):
    rows, cols = int(300 / CELL), int(600 / CELL)
    if occ is None:
        occ = (~cells_in(container.buffer(-MARGIN - R), rows, cols)).astype(np.float32)
    cache = {name: [(g, *part_mask(g)) for g in variants(name)] for name in set(queue)}
    placed = []
    for name in queue:
        best = None
        for g, mask, k in cache[name]:
            padded = np.pad(occ, k, constant_values=1)
            hits = correlate(padded, mask.astype(np.float32), mode='valid', method='fft')
            ok = hits < 0.5
            if limit is not None:
                ok &= (np.arange(ok.shape[1]) * CELL + g.bounds[2] <= limit)[None, :]
            if not ok.any():
                continue
            # left-most column first, then top-most row: packs the job toward x = 0
            col = int(np.argmax(ok.any(axis=0)))
            row = int(np.argmax(ok[:, col]))
            key = (col * CELL + g.bounds[2], row)
            if best is None or key < best[0]:
                best = (key, g, row, col)
        if best is None:
            continue
        _, g, row, col = best
        part = affinity.translate(g, col * CELL, row * CELL)
        placed.append((name, part))
        occ[cells_in(Polygon(part.exterior).buffer(GAP + R), rows, cols)] = 1
    return placed, occ

def fill(container, placed, occ, fillers):
    """Pack small filler parts into the gaps left inside the used length, like CAM 'fill parts'."""
    limit = max(g.bounds[2] for _, g in placed)
    for name in fillers:
        while True:
            more, occ = nest(container, [name], limit, occ)
            if not more:
                break
            placed += more
    return placed

def verify(container, placed):
    for i, (_, a) in enumerate(placed):
        assert container.contains(a), f'part {i} leaves the container'
        for _, b in placed[i + 1:]:
            assert Polygon(a.exterior).distance(Polygon(b.exterior)) >= GAP - 1e-6, 'parts too close'

def cut_order(placed, band=48):
    """Serpentine order by vertical bands, like a CAM post would sequence the cuts."""
    def key(item):
        c = item[1].centroid
        b = int(c.x // band)
        return (b, c.y if b % 2 == 0 else -c.y)
    return sorted(placed, key=key)


# ---------- output ----------

def num(v):
    s = f'{v:.1f}'.rstrip('0').rstrip('.')
    return '0' if s == '-0' else s

def path(g):
    g = g.simplify(0.12)
    def ring(r):
        return 'M' + 'L'.join(f'{num(x)} {num(y)}' for x, y in list(r.coords)[:-1]) + 'Z'
    return ring(g.exterior) + ''.join(ring(i) for i in g.interiors)

def area(placed):
    return sum(g.area for _, g in placed)

rect = box(150, 186, 596, 296)
full = cut_order(fill(plate, *nest(plate, QUEUE), ['flange', 'gusset', 'tab', 'disc']))
QUEUE = [name for name, n in JOB for _ in range(n + sum(1 for m, _ in full if m == name) - n)]
rectn, _ = nest(rect, QUEUE)
true, _ = nest(remnant, QUEUE)
ghost, _ = nest(max(consumed.geoms, key=lambda g: g.area), ['rail', 'cover', 'cover', 'bracket', 'hex', 'tee'] * 4)
for c, p in ((plate, full), (rect, rectn), (remnant, true)):
    verify(c, p)

used_w = max(g.bounds[2] for _, g in full) + MARGIN
stats = {
    'n_job': len(QUEUE),
    'n_full': len(full), 'n_rect': len(rectn), 'n_true': len(true),
    'full_util': area(full) / plate.area,
    'full_used_width_mm': round(used_w * 5),
    'full_used_util': area(full) / (used_w * 300),
    'rect_util': area(rectn) / remnant.area,
    'true_util': area(true) / remnant.area,
    'remnant_area_pct_of_plate': remnant.area / plate.area,
    'rect_area_pct_of_remnant': rect.area / remnant.area,
}
res = {
    'remnant': path(remnant_outline),
    'consumed': [path(g) for g in consumed.geoms],
    'holes': [path(hole_circle), path(hole_slot)],
    'ghost': [path(g) for _, g in ghost],
    'rect': [150, 186, 446, 110],
    'full': [path(g) for _, g in full],
    'rectNest': [path(g) for _, g in rectn],
    'trueNest': [path(g) for _, g in true],
    'stats': {k: round(v, 4) if isinstance(v, float) else v for k, v in stats.items()},
}
out = Path(__file__).resolve().parent.parent / 'src/components/remnant-gap-nest.json'
out.write_text(json.dumps(res, separators=(',', ':')))
print(json.dumps(res['stats'], indent=1))
