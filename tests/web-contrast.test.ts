import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { loadComponent, React } from "./harness/web-components.ts";

const css = readFileSync(new URL("../src/web/src/app/adept.css", import.meta.url), "utf8");

function rgb(color: string): number[] {
  if (color.startsWith("#")) {
    const hex = color.length === 4 ? color.slice(1).split("").map((digit) => digit + digit).join("") : color.slice(1);
    return [0, 2, 4].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255);
  }
  const [, hue, saturation, lightness] = color.match(/^hsl\(([\d.]+) ([\d.]+)% ([\d.]+)%\)$/);
  const h = Number(hue) / 30;
  const s = Number(saturation) / 100;
  const l = Number(lightness) / 100;
  const a = s * Math.min(l, 1 - l);
  return [0, 8, 4].map((offset) => {
    const k = (offset + h) % 12;
    return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
  });
}

function luminance(color: string): number {
  const values = rgb(color).map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
  return values.reduce((total, value, index) => total + value * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrast(a: string, b: string): number {
  const values = [luminance(a), luminance(b)].sort((left, right) => right - left);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

test("muted text and disclaimer meet 4.5:1 on the existing white and sage surfaces", () => {
  const muted = [...css.matchAll(/--a-muted:\s*(#[0-9a-f]{6})/g)].map((match) => match[1]);
  const surfaces = [...css.matchAll(/--a-(?:paper|surface|sunken|soft):\s*(#[0-9a-f]{6})/g)].map((match) => match[1]);
  assert.ok(muted.length >= 2 && surfaces.length >= 4);
  for (const color of muted) for (const background of surfaces) assert.ok(contrast(color, background) >= 4.5, `${color} on ${background}`);
  assert.match(css, /\.a-foot\s*\{[^}]*color:\s*var\(--a-muted\)/);
  const adi = readFileSync(new URL("../src/web/src/app/adi.css", import.meta.url), "utf8");
  assert.match(adi, /\.adi-foot\s*\{[^}]*color:\s*var\(--a-muted, #5b685f\)/);
  assert.match(css, /@property --a-muted\s*\{[^}]*initial-value:\s*#5b685f/);
});

test("every rendered heatmap cell meets 4.5:1 across the full clamped value range", () => {
  const { Heatmap } = loadComponent("src/components/viz/Heatmap.tsx");
  const values = [-1, ...Array.from({ length: 1001 }, (_, index) => index / 1000), 2];
  const node = Heatmap({ rows: [{ id: "synthetic", label: "Synthetic row", cells: values.map((value, index) => ({ id: String(index), value })) }], columns: [], legend: ["low", "high"] });
  let checked = 0;
  function visit(value) {
    if (Array.isArray(value)) return value.forEach(visit);
    if (!React.isValidElement(value)) return;
    if (value.props.role === "cell") {
      const { color, background } = value.props.style;
      assert.ok(contrast(color, background) >= 4.5, `${color} on ${background}`);
      checked++;
    }
    visit(value.props.children);
  }
  visit(node);
  assert.equal(checked, values.length);
});

test("keyboard focus on an intake radio gives its visible card a contrasting outline", () => {
  assert.match(css, /\.a-choice:has\(input:focus-visible\)\s*\{[^}]*outline:\s*3px solid var\(--a-deep\);[^}]*outline-offset:\s*3px/);
  const deep = css.match(/--a-deep:\s*(#[0-9a-f]{6})/)[1];
  assert.ok(contrast(deep, "#f3faf0") >= 3);
});
