"""Regenerate the draft comparison from the three supplied DXF exports.

Install benchmark-requirements.txt, then run with the source folder as argument.
Curves are flattened to 0.005 mm; only unambiguous degree-two chains are joined.
No individual part is moved, scaled, or repaired to hide an overlap.
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import ezdxf
from ezdxf.path import make_path
import shapely
from shapely import make_valid
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
FLATTEN_MM = 0.005
JOIN_MM = 0.05
OVERLAP_MM2 = 1.0
DISPLAY_MM = 0.025
SHEET_AREA = 1250 * 2500
FILES = [
    ("kenzap", "Kenzap Nesting", "export_kenzap_nesting.dxf"),
    ("deepnest", "Deepnest", "export_deepnest.dxf"),
    ("deepnest-next", "Deepnest-next", "export_deepnest_next.dxf"),
]


def stitch(paths):
    rings, open_paths = [], []
    joined = 0
    unresolved = []
    for points in paths:
        if math.dist(points[0], points[-1]) <= JOIN_MM:
            # A duplicate end vertex can differ slightly after DXF rounding.
            rings.append(points[:-1] + [points[0]])
        else:
            open_paths.append(points)
    while open_paths:
        chain = open_paths.pop(0)
        consumed = [chain]
        chain = list(chain)
        chain_joins = 0
        while math.dist(chain[0], chain[-1]) > JOIN_MM:
            matches = []
            for i, points in enumerate(open_paths):
                for reverse, endpoint in [(False, points[0]), (True, points[-1])]:
                    if math.dist(chain[-1], endpoint) <= JOIN_MM:
                        matches.append((i, reverse))
            if len(matches) != 1:
                unresolved.extend(consumed)
                break
            i, reverse = matches[0]
            segment = open_paths.pop(i)
            consumed.append(segment)
            if reverse:
                segment = segment[::-1]
            chain.extend(segment[1:])
            chain_joins += 1
        else:
            rings.append(chain[:-1] + [chain[0]])
            joined += chain_joins
    return rings, joined, unresolved


def common_xy(key, point):
    x, y = point[:2]
    if key == "deepnest":
        return y, 1250 - x
    if key == "deepnest-next":
        return -y, x
    return x, y


def svg_path(key, points):
    coords = [common_xy(key, p) for p in LineString(points).simplify(DISPLAY_MM).coords]
    return "M" + " L".join(f"{x:.4f},{1250-y:.4f}" for x, y in coords) + " Z"


def svg_line(key, points):
    return svg_path(key, points).removesuffix(" Z")


def polygon_paths(key, geometry):
    polygons = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    return " ".join(
        svg_path(key, polygon.exterior.coords)
        + " " + " ".join(svg_path(key, hole.coords) for hole in polygon.interiors)
        for polygon in polygons if polygon.geom_type == "Polygon"
    )


def analyze(source, key, name, filename):
    file = source / filename
    doc = ezdxf.readfile(file)
    entities = list(doc.modelspace())
    paths, annotation_count, unsupported = [], 0, []
    for entity in entities:
        if entity.dxftype() == "LINE":
            annotation_count += 1
            continue
        if entity.dxftype() not in {"POLYLINE", "LWPOLYLINE", "CIRCLE", "ARC", "ELLIPSE", "SPLINE"}:
            unsupported.append(entity.dxftype())
            continue
        points = [(v.x, v.y) for v in make_path(entity).flattening(FLATTEN_MM)]
        if len(points) > 2:
            paths.append(points)
    if unsupported:
        raise ValueError(f"Unsupported geometry in {filename}: {unsupported}")
    rings, joined, unresolved = stitch(paths)
    records = [(points, Polygon(points)) for points in rings]
    records.sort(key=lambda record: -record[1].area)
    # Containment, not entity count, distinguishes parts from their internal cuts.
    outers, holes, orphan_holes = [], [], []
    for points, polygon in records:
        parent = next((i for i, (_, outer) in enumerate(outers)
                       if outer.buffer(JOIN_MM).covers(polygon)), None)
        if parent is None:
            # This fixture repeats one 177 x 380 mm profile. Small unattached
            # rings belong to fragmented parts, not additional tiny parts.
            if polygon.area < 10000:
                orphan_holes.append((points, polygon))
                continue
            if not polygon.is_valid:
                raise ValueError(f"Invalid outer contour in {filename}; refusing to repair")
            outers.append((points, polygon))
            holes.append([])
        else:
            holes[parent].append((points, polygon))
    all_holes = [hole for group in holes for hole in group] + orphan_holes
    invalid_holes = sum(not hole.is_valid for _, hole in all_holes)
    polygons = [outer for _, outer in outers]
    overlaps = []
    for i, a in enumerate(polygons):
        for j in range(i + 1, len(polygons)):
            intersection = a.intersection(polygons[j])
            if intersection.area > OVERLAP_MM2:
                overlaps.append((i, j, intersection))
    merged = unary_union(polygons)
    gross_area = sum(p.area for p in polygons)
    occupied = [common_xy(key, p) for points in paths for p in points]
    min_x = min(x for x, _ in occupied)
    max_x = max(x for x, _ in occupied)
    min_y = min(y for _, y in occupied)
    max_y = max(y for _, y in occupied)
    length, width = max_x - min_x, max_y - min_y
    net_area = sum(outer.difference(unary_union([
        make_valid(hole) for _, hole in group
    ])).area for outer, group in zip(polygons, holes))
    parts_markup = []
    for i, ((points, _), group) in enumerate(zip(outers, holes)):
        d = svg_path(key, points) + " " + " ".join(svg_path(key, ring) for ring, _ in group)
        parts_markup.append(f'<path class="part" data-part="{i+1}" d="{d}"/>')
    overlap_markup = "".join(
        f'<path class="overlap" d="{polygon_paths(key, shape)}"/>'
        for _, _, shape in overlaps
    )
    fragment_markup = "".join(f'<path class="fragment" d="{svg_line(key, points)}"/>' for points in unresolved)
    fragment_markup += "".join(f'<path class="fragment-hole" d="{svg_path(key, points)}"/>' for points, _ in orphan_holes)
    unused = f'<rect class="unused" x="{max_x:.4f}" y="0" width="{max(0,2500-max_x):.4f}" height="1250"/>' if key == "kenzap" else ""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 -8 2516 1266" role="img" aria-labelledby="{key}-title {key}-desc">
<title id="{key}-title">{name}: {len(outers)} intact outer contours</title>
<desc id="{key}-desc">Supplied DXF in a common 2500 by 1250 mm frame. {len(overlaps)} outer-contour intersection pairs above 1 square mm. {len(unresolved)} open fragments are drawn without invented closing lines.</desc>
<style>.part{{fill:#e8ecfc;stroke:#1941df;stroke-width:1;vector-effect:non-scaling-stroke;fill-rule:evenodd}}.fragment,.fragment-hole{{fill:none;stroke:#1941df;stroke-width:1;vector-effect:non-scaling-stroke}}.overlap{{fill:#d94b3e;fill-opacity:.8;display:none}}.unused{{fill:#eef4ee}}.sheet{{fill:none;stroke:#8a9099;stroke-width:1;vector-effect:non-scaling-stroke}}svg[data-overlaps="true"] .overlap{{display:initial}}svg[data-outlines="true"] .part{{fill:none}}</style>
<rect fill="#fff" x="0" y="0" width="2500" height="1250"/>{unused}
{"".join(parts_markup)}{fragment_markup}{overlap_markup}<rect class="sheet" x="0" y="0" width="2500" height="1250"/>
</svg>'''
    assets = ROOT / "public/articles/deepnest-vs-kenzap-nesting"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / f"{key}.svg").write_text(svg, encoding="utf-8")
    return {
        "id": key, "name": name, "file": filename,
        "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        "fileBytes": file.stat().st_size,
        "entityCounts": dict(Counter(e.dxftype() for e in entities)),
        "parts": len(outers) if not unresolved else None,
        "closedOuterContours": len(outers), "openFragments": len(unresolved),
        "holes": len(all_holes), "orphanInternalContours": len(orphan_holes),
        "joinedFragments": joined, "annotationLinesExcluded": annotation_count,
        "invalidHoleRings": invalid_holes,
        "lengthMm": round(length, 4), "widthMm": round(width, 4),
        "bounds": [round(n, 4) for n in [min_x, min_y, max_x, max_y]],
        "grossAreaMm2": round(gross_area, 3), "netAreaMm2": round(net_area, 3),
        "grossCoveragePercent": round(100 * gross_area / SHEET_AREA, 3) if not unresolved else None,
        "uniqueCoveragePercent": round(100 * merged.area / SHEET_AREA, 3) if not unresolved else None,
        "usedRectangleCoveragePercent": round(100 * gross_area / (length * width), 3) if not unresolved else None,
        "overlapPairs": len(overlaps),
        "overlapAreaMm2": round(max(0, gross_area - merged.area), 3),
        "intersections": [{"parts": [i+1, j+1], "areaMm2": round(shape.area, 3)}
                          for i, j, shape in overlaps],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    results = [analyze(args.source, *spec) for spec in FILES]
    data = {
        "date": "2026-10-05", "targetParts": 61,
        "sheet": {"widthMm": 1250, "lengthMm": 2500},
        "analysis": {"ezdxf": ezdxf.__version__, "shapely": shapely.__version__,
                     "curveToleranceMm": FLATTEN_MM, "joinToleranceMm": JOIN_MM,
                     "overlapThresholdMm2": OVERLAP_MM2, "displayToleranceMm": DISPLAY_MM},
        "results": results,
    }
    content = json.dumps(data, indent=2) + "\n"
    (ROOT / "src/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "src/data/deepnest-benchmark.json").write_text(content, encoding="utf-8")
    (ROOT / "public/articles/deepnest-vs-kenzap-nesting/analysis.json").write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
