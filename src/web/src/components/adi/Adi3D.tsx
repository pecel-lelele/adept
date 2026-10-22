"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { AdiMascot, type AdiMood } from "./AdiMascot";

type Props = {
  size?: number;
  mood?: AdiMood;
  className?: string;
  /** Accessible name; omit when decorative. */
  title?: string;
  /** Follow the pointer with head and eyes (off for small, static placements). */
  follow?: boolean;
};

/**
 * Adi in real 3D (three.js, loaded on demand). Built from rounded primitives, lit like a toy:
 * idle bob and breathing, blinking, a radar dish sending signal rings, head and eyes that follow
 * the pointer, a wave, a thinking tilt, a talking mouth and a happy hop. A click makes Adi spin.
 *
 * Shows the flat SVG Adi until the 3D model is ready, and keeps it when WebGL is missing, the
 * person prefers reduced motion, or the page is in the background (rendering pauses off-screen).
 */
export function Adi3D({ size = 120, mood = "idle", className = "", title, follow = true }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const moodRef = useRef<AdiMood>(mood);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    moodRef.current = mood;
  }, [mood]);

  useEffect(() => {
    const el = host.current;
    if (!el || reduced) return;
    let disposed = false;
    let cleanup: (() => void) | undefined;
    (async () => {
      try {
        const THREE = await import("three");
        const { RoundedBoxGeometry } = await import("three/examples/jsm/geometries/RoundedBoxGeometry.js");
        if (disposed) return;
        cleanup = mount(THREE, RoundedBoxGeometry, el, size, moodRef, follow, () => setReady(true));
      } catch {
        if (!disposed) setFailed(true);
      }
    })();
    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [size, follow, reduced]);

  const height = Math.round(size * 1.15);
  return (
    <div
      ref={host}
      className={`adi3d ${className}`}
      data-ready={ready && !failed && !reduced}
      style={{ width: size, height }}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {!ready || failed || reduced ? <AdiMascot size={size * 0.86} mood={mood} className="adi3d-fallback" /> : null}
    </div>
  );
}

const MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (notify) => {
      const query = window.matchMedia(MOTION_QUERY);
      query.addEventListener("change", notify);
      return () => query.removeEventListener("change", notify);
    },
    () => window.matchMedia(MOTION_QUERY).matches,
    () => false,
  );
}

type Three = typeof import("three");
type RoundedBoxCtor = typeof import("three/examples/jsm/geometries/RoundedBoxGeometry.js").RoundedBoxGeometry;

function mount(
  THREE: Three,
  RoundedBox: RoundedBoxCtor,
  el: HTMLDivElement,
  size: number,
  moodRef: { current: AdiMood },
  follow: boolean,
  onReady: () => void,
): () => void {
  const width = size;
  const height = Math.round(size * 1.15);
  let renderer: import("three").WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  } catch {
    throw new Error("webgl");
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.domElement.className = "adi3d-canvas";
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 50);
  camera.position.set(0, 0.45, 6.4);
  camera.lookAt(0, 0.3, 0);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x2f5a40, 1.15));
  const key = new THREE.DirectionalLight(0xffffff, 1.9);
  key.position.set(3, 5, 4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x86efac, 1.1);
  rim.position.set(-4, 2, -3);
  scene.add(rim);

  const disposables: { dispose: () => void }[] = [];
  const geo = <T extends { dispose: () => void }>(g: T) => (disposables.push(g), g);
  const mat = <T extends { dispose: () => void }>(m: T) => (disposables.push(m), m);

  const green = mat(new THREE.MeshPhysicalMaterial({ color: 0x22c55e, roughness: 0.32, clearcoat: 0.8, clearcoatRoughness: 0.2 }));
  const deep = mat(new THREE.MeshPhysicalMaterial({ color: 0x15803d, roughness: 0.4, clearcoat: 0.5 }));
  const screen = mat(new THREE.MeshStandardMaterial({ color: 0xf4fff7, roughness: 0.22, emissive: 0xe8faee, emissiveIntensity: 0.25 }));
  const ink = mat(new THREE.MeshStandardMaterial({ color: 0x123321, roughness: 0.3 }));
  const white = mat(new THREE.MeshBasicMaterial({ color: 0xffffff }));
  const blush = mat(new THREE.MeshBasicMaterial({ color: 0xfb7185, transparent: true, opacity: 0.35 }));
  const mint = mat(new THREE.MeshStandardMaterial({ color: 0xbbf7d0, roughness: 0.3, side: THREE.DoubleSide }));
  const glow = mat(new THREE.MeshStandardMaterial({ color: 0x86efac, emissive: 0x4ade80, emissiveIntensity: 0.9 }));
  const leaf = mat(new THREE.MeshStandardMaterial({ color: 0xdcfce7, roughness: 0.4 }));

  const adi = new THREE.Group();
  scene.add(adi);
  const body = new THREE.Group();
  adi.add(body);

  const shell = new THREE.Mesh(geo(new RoundedBox(2.0, 1.9, 1.5, 6, 0.62)), green);
  body.add(shell);

  const face = new THREE.Mesh(geo(new RoundedBox(1.5, 0.98, 0.14, 4, 0.065)), screen);
  face.position.set(0, 0.16, 0.72);
  body.add(face);

  const eyes = new THREE.Group();
  eyes.position.set(0, 0.24, 0.8);
  body.add(eyes);
  const eyeGeo = geo(new THREE.SphereGeometry(0.11, 24, 16));
  const shineGeo = geo(new THREE.SphereGeometry(0.035, 12, 8));
  const eyeMeshes: import("three").Mesh[] = [];
  for (const x of [-0.29, 0.29]) {
    const eye = new THREE.Mesh(eyeGeo, ink);
    eye.position.x = x;
    eye.scale.set(1, 1.35, 0.6);
    eyes.add(eye);
    eyeMeshes.push(eye);
    const shine = new THREE.Mesh(shineGeo, white);
    shine.position.set(x + 0.04, 0.06, 0.07);
    eyes.add(shine);
  }
  const cheekGeo = geo(new THREE.CircleGeometry(0.085, 20));
  for (const x of [-0.5, 0.5]) {
    const cheek = new THREE.Mesh(cheekGeo, blush);
    cheek.position.set(x, 0.02, 0.795);
    body.add(cheek);
  }
  const smile = new THREE.Mesh(geo(new THREE.TorusGeometry(0.15, 0.032, 8, 28, Math.PI)), ink);
  smile.rotation.z = Math.PI;
  smile.position.set(0, 0.04, 0.8);
  body.add(smile);
  const mouth = new THREE.Mesh(geo(new THREE.SphereGeometry(0.1, 20, 12)), ink);
  mouth.scale.set(1.25, 0.7, 0.4);
  mouth.position.set(0, -0.02, 0.79);
  mouth.visible = false;
  body.add(mouth);

  // Leaf badge (the SDG link) on the chest.
  const leafShape = new THREE.Shape();
  leafShape.moveTo(0, -0.16);
  leafShape.bezierCurveTo(0.16, -0.08, 0.15, 0.1, 0, 0.18);
  leafShape.bezierCurveTo(-0.15, 0.1, -0.16, -0.08, 0, -0.16);
  const badge = new THREE.Mesh(geo(new THREE.ExtrudeGeometry(leafShape, { depth: 0.04, bevelEnabled: false })), leaf);
  badge.position.set(0, -0.56, 0.74);
  badge.rotation.z = -0.5;
  body.add(badge);

  // Antenna: stalk, radar dish, glowing tip and signal rings.
  const antenna = new THREE.Group();
  antenna.position.y = 0.94;
  body.add(antenna);
  const stalk = new THREE.Mesh(geo(new THREE.CylinderGeometry(0.035, 0.045, 0.34, 12)), deep);
  stalk.position.y = 0.16;
  antenna.add(stalk);
  const dish = new THREE.Mesh(geo(new THREE.SphereGeometry(0.24, 28, 12, 0, Math.PI * 2, 0, Math.PI / 2.6)), mint);
  dish.position.y = 0.34;
  dish.rotation.x = Math.PI;
  antenna.add(dish);
  const tip = new THREE.Mesh(geo(new THREE.SphereGeometry(0.065, 16, 12)), glow);
  tip.position.y = 0.36;
  antenna.add(tip);
  const rings: { mesh: import("three").Mesh; material: import("three").MeshBasicMaterial }[] = [];
  for (let i = 0; i < 2; i++) {
    const material = mat(new THREE.MeshBasicMaterial({ color: 0x22c55e, transparent: true, opacity: 0 }));
    const mesh = new THREE.Mesh(geo(new THREE.TorusGeometry(0.2 + i * 0.12, 0.018, 6, 36, Math.PI * 0.75)), material);
    mesh.position.y = 0.5 + i * 0.08;
    mesh.rotation.z = Math.PI * 0.125;
    antenna.add(mesh);
    rings.push({ mesh, material });
  }

  // Arms on shoulder pivots.
  const armGeo = geo(new THREE.CapsuleGeometry(0.13, 0.42, 6, 14));
  const makeArm = (side: number) => {
    const pivot = new THREE.Group();
    pivot.position.set(side * 1.0, -0.12, 0.05);
    const arm = new THREE.Mesh(armGeo, deep);
    arm.position.y = -0.3;
    pivot.add(arm);
    pivot.rotation.z = side * 0.35;
    body.add(pivot);
    return pivot;
  };
  const left = makeArm(-1);
  const right = makeArm(1);

  // Soft contact shadow.
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const g = canvas.getContext("2d");
  if (g) {
    const grad = g.createRadialGradient(32, 32, 2, 32, 32, 32);
    grad.addColorStop(0, "rgba(13,42,23,0.35)");
    grad.addColorStop(1, "rgba(13,42,23,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 64, 64);
  }
  const shadowTex = new THREE.CanvasTexture(canvas);
  disposables.push(shadowTex);
  const shadow = new THREE.Mesh(
    geo(new THREE.PlaneGeometry(2.4, 0.9)),
    mat(new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false })),
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -1.18;
  scene.add(shadow);

  // ---- motion ----
  const pointer = { x: 0, y: 0, at: -10 };
  const onMove = (e: PointerEvent) => {
    const r = el.getBoundingClientRect();
    pointer.x = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / (window.innerWidth / 2)));
    pointer.y = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height / 2)) / (window.innerHeight / 2)));
    pointer.at = performance.now() / 1000;
  };
  if (follow) window.addEventListener("pointermove", onMove, { passive: true });
  let spinFrom = -10;
  const onClick = () => (spinFrom = performance.now() / 1000);
  el.addEventListener("click", onClick);

  let nextBlink = 2 + Math.random() * 3;
  let visible = true;
  const io = new IntersectionObserver((entries) => (visible = entries[0]?.isIntersecting ?? true));
  io.observe(el);

  const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
  let frame = 0;
  let last = performance.now() / 1000;
  const clock0 = last;
  let first = true;

  const tick = () => {
    frame = requestAnimationFrame(tick);
    if (!visible || document.hidden) return;
    const now = performance.now() / 1000;
    const dt = Math.min(0.05, now - last);
    last = now;
    const t = now - clock0;
    const mood = moodRef.current;

    // idle bob, breathing and the happy hop
    const hop = mood === "happy" ? Math.abs(Math.sin(t * 6)) * 0.28 : 0;
    const spinT = now - spinFrom;
    const spinning = spinT < 0.9;
    adi.position.y = Math.sin(t * 2.2) * 0.06 + hop + (spinning ? Math.sin((spinT / 0.9) * Math.PI) * 0.35 : 0);
    shell.scale.y = 1 + Math.sin(t * 2.2 + 0.6) * 0.012;
    shadow.scale.setScalar(1 - adi.position.y * 0.35);

    // look at the pointer, or sway gently when the pointer has been still
    const recent = now - pointer.at < 3;
    const yaw = recent ? pointer.x * 0.6 : Math.sin(t * 0.6) * 0.22;
    const pitch = recent ? pointer.y * 0.3 : Math.sin(t * 0.45) * 0.05;
    body.rotation.y = lerp(body.rotation.y, yaw, 0.08);
    body.rotation.x = lerp(body.rotation.x, pitch, 0.08);
    body.rotation.z = lerp(body.rotation.z, mood === "think" ? 0.16 : 0, 0.06);
    adi.rotation.y = spinning ? (spinT / 0.9) * Math.PI * 2 : 0;
    eyes.position.x = lerp(eyes.position.x, yaw * 0.07, 0.15);
    eyes.position.y = lerp(eyes.position.y, 0.24 + (mood === "think" ? 0.07 : -pitch * 0.05), 0.15);

    // blink
    let lid = 1;
    if (t > nextBlink) {
      const p = (t - nextBlink) / 0.14;
      lid = p < 1 ? 1 - Math.sin(p * Math.PI) * 0.92 : 1;
      if (p >= 1) nextBlink = t + 2.5 + Math.random() * 3.5;
    }
    for (const eye of eyeMeshes) eye.scale.y = 1.35 * (mood === "happy" ? 0.55 : lid);

    // mouth
    mouth.visible = mood === "talk";
    smile.visible = mood !== "talk";
    if (mouth.visible) mouth.scale.y = 0.3 + Math.abs(Math.sin(t * 13)) * 0.55;

    // arms
    // Positive z swings the right arm outward and up; the left arm mirrors it.
    const rightTarget =
      mood === "wave" ? 2.35 + Math.sin(t * 9) * 0.35 : mood === "happy" ? 2.1 + Math.sin(t * 6) * 0.2 : 0.35 + Math.sin(t * 2.2) * 0.05;
    const leftTarget = mood === "happy" ? -2.1 - Math.sin(t * 6) * 0.2 : -0.35 - Math.sin(t * 2.2) * 0.05;
    right.rotation.z = lerp(right.rotation.z, rightTarget, 0.15);
    left.rotation.z = lerp(left.rotation.z, leftTarget, 0.15);

    // antenna and signal rings (faster while thinking)
    antenna.rotation.y += dt * (mood === "think" ? 4 : 0.6);
    const speed = mood === "think" ? 1.8 : 0.8;
    rings.forEach(({ mesh, material }, i) => {
      const phase = (t * speed + i * 0.5) % 1;
      mesh.scale.setScalar(1 + phase * 0.6);
      material.opacity = (1 - phase) * 0.85;
    });

    renderer.render(scene, camera);
    if (first) {
      first = false;
      onReady();
    }
  };
  frame = requestAnimationFrame(tick);

  return () => {
    cancelAnimationFrame(frame);
    io.disconnect();
    window.removeEventListener("pointermove", onMove);
    el.removeEventListener("click", onClick);
    for (const d of disposables) d.dispose();
    renderer.dispose();
    renderer.domElement.remove();
  };
}
