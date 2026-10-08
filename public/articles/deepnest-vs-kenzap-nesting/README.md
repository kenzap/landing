# Deepnest / Kenzap Nesting: draft benchmark record

Date: 5 October 2026. Prepared by the developer of Kenzap Nesting, not an independent reviewer.

## Operator-reported conditions

- Required quantity: 61 copies of one profile, about 177 x 380 mm, with 12 internal cuts per part.
- Stock sheet: 1250 x 2500 mm.
- Target nesting time: 45 seconds.
- Rotations: 0, 90, 180, 270 degrees.
- Hardware: Apple M5 Pro, macOS (OS version unrecorded).
- Kenzap and original Deepnest versions unrecorded. Deepnest-next v1.5.6 is visible in screenshots.
- Spacing, margins, curve settings, seeds, import options, and thread counts are not yet confirmed.

## Screenshot evidence, not automated timing logs

- Kenzap's capture labeled 45 seconds reports a complete 61-part result.
- Deepnest-next's captures labeled 45 seconds, 5 minutes, 10 minutes report 43, 46, 46 parts.
- Original Deepnest's screenshot reports 55 parts; exact elapsed time is not recorded.
- The operator observed Kenzap's initial complete placement within the first seconds.
- The operator reported original Deepnest reaching 51 within roughly the first minute, then 55 later.
- The screenshot labels do not independently establish elapsed time. No exact speedup ratio is claimed.

## Analysis of the supplied exports

See analysis.json for full-precision measurements, entity counts, and SHA-256 hashes.

| Check | Kenzap | Deepnest-next | Original Deepnest |
| --- | --- | --- | --- |
| Intact outer contours | 61 | 43 | 49 |
| Unresolved open fragments | 0 | 0 | 12 |
| Internal cuts | 732 | 516 | 660 |
| Intersecting outer pairs > 1 mm2 | 0 | 0 | At least 5 |
| Gross envelope coverage of full stock | 77.753% | 54.810% | Not reported |

The original Deepnest screenshot's 55 count is not treated as 55 validated exported parts.
Its 12 open fragments cannot be unambiguously joined into valid contours, and 72 internal
cut contours are not enclosed by an intact outer contour. No fictitious closing edge is added.
Its confirmed overlap count excludes fragments, so it is a lower bound.

The Deepnest-next export contains 43 parts, matching its 45-second screenshot count; the exact
export time is not independently verified. No 46-part follow-up export was supplied.

## Geometry method

Analysis dependencies: ezdxf 1.4.4, shapely 2.1.2.

- Curve flattening tolerance: 0.005 mm.
- Endpoint closing/joining tolerance: 0.05 mm. Only unambiguous chains are joined.
- This repeated-profile fixture uses 10,000 mm2 as the separator between its large outer contours
  and small internal cuts. This is fixture-specific, not a general-purpose arbitrary-DXF importer.
- Pair intersections are against solid outer envelopes. No nesting inside holes is assumed.
- Flag threshold: 1 mm2. Zero flags is not a full clearance, kerf, CAM, or safety certification.
- Kenzap's 915 LINE entities on its secondary layer are annotations, not additional parts.
- Gross coverage = summed outer-envelope area / (1250 * 2500). Internal holes are not subtracted.
- Used-rectangle density uses each output's occupied bounding rectangle, so denominators differ.
- Kenzap's 84.381% used-rectangle density is not compared with Deepnest-next's on-screen
  98.56% / 99.04% statistics: the latter's calculation basis was not verified.
- The SVG display simplifies boundaries within 0.025 mm; analysis uses the higher-resolution curves.
- Entire layouts may be rotated 90 degrees into a common horizontal stock frame. Individual
  placements are never moved, scaled, or repaired. The supplied DXFs remain byte-identical.
- About 196 mm of remaining stock length is a geometric observation, not a guaranteed reusable remnant.

## Re-running the geometry check

In the kenzap-landing source repository:

```sh
python3 -m venv .venv-benchmark
.venv-benchmark/bin/pip install -r scripts/benchmark-requirements.txt
.venv-benchmark/bin/python scripts/analyze-nesting-benchmark.py public/articles/deepnest-vs-kenzap-nesting
npm run test:benchmark
```

This regenerates the analysis JSON and SVGs. It does not re-run any nesting optimizer.
The original source DXF is not included, so this bundle does not reproduce the benchmark
runs end to end. Repeat the runs after capturing input, settings, versions, and exact timings.

## Before publication

Confirm the missing settings, versions, input-file distribution permission, and checkpoint times;
repeat the tests with equal budgets; record typical as well as best results; and invite independent
verification. The article is a noindex mockup, intentionally not linked from the main landing page.
