import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const asset = (file) => path.join(root, 'public/articles/deepnest-vs-kenzap-nesting', file);
const data = JSON.parse(readFileSync(path.join(root, 'src/data/deepnest-benchmark.json'), 'utf8'));
assert.deepEqual(data, JSON.parse(readFileSync(asset('analysis.json'), 'utf8')));
const expected = {
  kenzap: { parts: 61, closed: 61, holes: 732, open: 0, overlap: 0 },
  'deepnest-next': { parts: 43, closed: 43, holes: 516, open: 0, overlap: 0 },
  deepnest: { parts: null, closed: 49, holes: 660, open: 12, overlap: 5 },
};
for (const result of data.results) {
  const check = expected[result.id];
  assert.ok(check);
  assert.equal(result.parts, check.parts);
  assert.equal(result.closedOuterContours, check.closed);
  assert.equal(result.holes, check.holes);
  assert.equal(result.openFragments, check.open);
  assert.equal(result.overlapPairs, check.overlap);
  const dxf = readFileSync(asset(result.file));
  assert.equal(createHash('sha256').update(dxf).digest('hex'), result.sha256, 'Original export must not change');
  assert.equal(dxf.byteLength, result.fileBytes);
  const svg = readFileSync(asset(`${result.id}.svg`), 'utf8');
  assert.match(svg, /viewBox="-8 -8 2516 1266"/);
  assert.equal((svg.match(/class="part"/g) || []).length, check.closed);
  assert.equal((svg.match(/class="fragment"/g) || []).length, check.open);
  assert.equal((svg.match(/class="overlap"/g) || []).length, check.overlap);
  assert.match(svg, new RegExp(`id="${result.id}-title"`));
  if (result.parts !== null) {
    assert.ok(Math.abs(result.grossCoveragePercent - result.grossAreaMm2 / 3125000 * 100) < .001);
    assert.ok(result.grossCoveragePercent < 100);
    assert.ok(result.lengthMm <= 2500);
  } else {
    assert.equal(result.grossCoveragePercent, null, 'No invented coverage for unresolved contours');
  }
}
const kenzap = data.results.find((result) => result.id === 'kenzap');
const next = data.results.find((result) => result.id === 'deepnest-next');
assert.ok(Math.abs(kenzap.grossAreaMm2 / 61 - next.grossAreaMm2 / 43) < .05, 'Same repeated outer profile');
assert.ok(Math.abs(kenzap.lengthMm - 2303.6316) < .001);
assert.equal(kenzap.annotationLinesExcluded, 915);
for (const screenshot of ['kenzap-nesting-45s.webp', 'deepnest.webp', 'deepnest-next-45s.webp', 'deepnest-next-5m.webp', 'deepnest-next-10m.webp']) assert.ok(existsSync(asset(screenshot)));
assert.ok(existsSync(asset('benchmark-exports.zip')));
const page = readFileSync(path.join(root, 'src/pages/articles/deepnest-vs-kenzap-nesting.astro'), 'utf8');
assert.match(page, /noindex, nofollow/);
assert.match(page, /Elapsed time was not recorded/);
assert.match(page, /not included/);
assert.match(page, /Deepnest-next v1\.5\.6/);
assert.doesNotMatch(page, /<strong>\{percent\(/, 'Dynamic table values must not leak formatting into the article');
console.log('Benchmark checks passed: unchanged DXFs, contour counts, coverage, intersection masks, evidence, and draft safeguards.');
