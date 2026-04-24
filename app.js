import * as THREE from "https://unpkg.com/three@0.162.0/build/three.module.js";
import { OrbitControls } from "https://unpkg.com/three@0.162.0/examples/jsm/controls/OrbitControls.js";

const theoremContent = {
  complementary: {
    title: "Complementary Angles",
    body:
      "Two angles are complementary when they add to 90°. In this model, two rays split a right angle into 30° and 60°.",
  },
  supplementary: {
    title: "Supplementary Angles",
    body:
      "Two angles are supplementary when they add to 180°. Here, one straight line is split into 110° and 70°.",
  },
  vertical: {
    title: "Vertical Opposite Angles",
    body:
      "When two lines intersect, opposite (vertical) angles are always equal. In this model, the red and blue highlighted pairs match.",
  },
  parallel: {
    title: "Parallel Lines + Transversal",
    body:
      "If a transversal crosses two parallel lines, corresponding angles are equal. Alternate interior angles are equal too.",
  },
  triangle: {
    title: "Triangle Interior Angles",
    body:
      "The three interior angles of any triangle always add to 180°. This model labels a triangle with 40°, 65°, and 75°.",
  },
};

const canvas = document.getElementById("scene");
const theoremText = document.getElementById("theoremText");
const modelSelect = document.getElementById("modelSelect");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);

const scene = new THREE.Scene();
scene.background = new THREE.Color("#f1f5f9");

const camera = new THREE.PerspectiveCamera(50, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
camera.position.set(8, 7, 10);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 1, 0);

const ambient = new THREE.AmbientLight(0xffffff, 0.9);
scene.add(ambient);
const dir = new THREE.DirectionalLight(0xffffff, 0.8);
dir.position.set(7, 10, 5);
scene.add(dir);

const grid = new THREE.GridHelper(20, 20, 0x94a3b8, 0xcbd5e1);
grid.position.y = -1.5;
scene.add(grid);

const activeGroup = new THREE.Group();
scene.add(activeGroup);

function clearGroup(group) {
  while (group.children.length > 0) {
    const child = group.children[0];
    group.remove(child);
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
      else child.material.dispose();
    }
  }
}

function makeLine(start, end, color = 0x0f172a, radius = 0.05) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();

  const geometry = new THREE.CylinderGeometry(radius, radius, length, 18);
  const material = new THREE.MeshStandardMaterial({ color });
  const cylinder = new THREE.Mesh(geometry, material);

  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  cylinder.position.copy(midpoint);
  cylinder.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
  return cylinder;
}

function makeArc(radius, startDeg, endDeg, color = 0xef4444, tube = 0.04, y = 0) {
  const start = THREE.MathUtils.degToRad(startDeg);
  const end = THREE.MathUtils.degToRad(endDeg);
  const points = [];

  for (let i = 0; i <= 60; i += 1) {
    const t = i / 60;
    const angle = start + (end - start) * t;
    points.push(new THREE.Vector3(radius * Math.cos(angle), y, radius * Math.sin(angle)));
  }

  const curve = new THREE.CatmullRomCurve3(points);
  const geometry = new THREE.TubeGeometry(curve, 80, tube, 8, false);
  const material = new THREE.MeshStandardMaterial({ color });
  return new THREE.Mesh(geometry, material);
}

function makeLabel(text, x, y, z, color = "#1e293b") {
  const spriteCanvas = document.createElement("canvas");
  spriteCanvas.width = 256;
  spriteCanvas.height = 128;
  const ctx = spriteCanvas.getContext("2d");

  ctx.fillStyle = "rgba(255,255,255,0.88)";
  ctx.fillRect(0, 0, 256, 128);
  ctx.strokeStyle = "#94a3b8";
  ctx.strokeRect(1, 1, 254, 126);
  ctx.fillStyle = color;
  ctx.font = "bold 44px Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 128, 64);

  const texture = new THREE.CanvasTexture(spriteCanvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(2.2, 1.1, 1);
  sprite.position.set(x, y, z);
  return sprite;
}

function setTheoremText(key) {
  const item = theoremContent[key];
  theoremText.innerHTML = `<strong>${item.title}</strong><br>${item.body}`;
}

function buildComplementary() {
  // Rays at 0°, 30°, and 90°
  const origin = new THREE.Vector3(0, 0, 0);
  const len = 4.8;
  const rayA = new THREE.Vector3(len, 0, 0);
  const rayB = new THREE.Vector3(len * Math.cos(THREE.MathUtils.degToRad(30)), 0, len * Math.sin(THREE.MathUtils.degToRad(30)));
  const rayC = new THREE.Vector3(0, 0, len);

  activeGroup.add(makeLine(origin, rayA, 0x0f172a));
  activeGroup.add(makeLine(origin, rayB, 0x2563eb));
  activeGroup.add(makeLine(origin, rayC, 0x0f172a));
  activeGroup.add(makeArc(1.2, 0, 30, 0xf97316, 0.04, 0.01));
  activeGroup.add(makeArc(1.9, 30, 90, 0x14b8a6, 0.04, 0.01));
  activeGroup.add(makeLabel("30°", 1.5, 0.2, 0.45));
  activeGroup.add(makeLabel("60°", 0.85, 0.2, 1.4));
  activeGroup.add(makeLabel("90° total", 1.8, 1.1, 1.8, "#1d4ed8"));
}

function buildSupplementary() {
  const origin = new THREE.Vector3(0, 0, 0);
  const len = 5;
  const left = new THREE.Vector3(-len, 0, 0);
  const right = new THREE.Vector3(len, 0, 0);
  const split = new THREE.Vector3(len * Math.cos(THREE.MathUtils.degToRad(110)), 0, len * Math.sin(THREE.MathUtils.degToRad(110)));

  activeGroup.add(makeLine(left, right, 0x0f172a));
  activeGroup.add(makeLine(origin, split, 0x2563eb));
  activeGroup.add(makeArc(1.3, 0, 110, 0xf43f5e, 0.04, 0.01));
  activeGroup.add(makeArc(1.95, 110, 180, 0x10b981, 0.04, 0.01));
  activeGroup.add(makeLabel("110°", -0.1, 0.2, 1.5));
  activeGroup.add(makeLabel("70°", -1.6, 0.2, 0.45));
  activeGroup.add(makeLabel("180° straight", -0.2, 1.2, -1.6, "#1d4ed8"));
}

function buildVertical() {
  const len = 5;
  activeGroup.add(makeLine(new THREE.Vector3(-len, 0, -len), new THREE.Vector3(len, 0, len), 0x0f172a));
  activeGroup.add(makeLine(new THREE.Vector3(-len, 0, len), new THREE.Vector3(len, 0, -len), 0x0f172a));

  activeGroup.add(makeArc(1.2, 20, 160, 0xf43f5e, 0.04, 0.01));
  activeGroup.add(makeArc(1.2, 200, 340, 0xf43f5e, 0.04, 0.01));
  activeGroup.add(makeArc(1.9, 160, 200, 0x3b82f6, 0.04, 0.01));
  activeGroup.add(makeArc(1.9, 340, 380, 0x3b82f6, 0.04, 0.01));

  activeGroup.add(makeLabel("A", 0.1, 0.2, 1.8, "#be123c"));
  activeGroup.add(makeLabel("A", -0.1, 0.2, -1.8, "#be123c"));
  activeGroup.add(makeLabel("B", -1.8, 0.2, 0, "#1d4ed8"));
  activeGroup.add(makeLabel("B", 1.8, 0.2, 0, "#1d4ed8"));
}

function buildParallel() {
  const len = 5.2;
  const z1 = 1.8;
  const z2 = -1.8;

  activeGroup.add(makeLine(new THREE.Vector3(-len, 0, z1), new THREE.Vector3(len, 0, z1), 0x0f172a));
  activeGroup.add(makeLine(new THREE.Vector3(-len, 0, z2), new THREE.Vector3(len, 0, z2), 0x0f172a));

  activeGroup.add(makeLine(new THREE.Vector3(-2.5, 0, 3.8), new THREE.Vector3(2.5, 0, -3.8), 0x2563eb));

  activeGroup.add(makeArc(0.9, 315, 360, 0xf97316, 0.03, 0.01));
  activeGroup.add(makeArc(0.9, 315, 360, 0xf97316, 0.03, 0.01).translateY(0).translateZ(-3.6));

  activeGroup.add(makeArc(0.9, 180, 225, 0x14b8a6, 0.03, 0.01).translateZ(-1.8));
  activeGroup.add(makeArc(0.9, 180, 225, 0x14b8a6, 0.03, 0.01).translateZ(1.8));

  activeGroup.add(makeLabel("Corresponding", 2.6, 0.45, 2.8, "#9a3412"));
  activeGroup.add(makeLabel("equal", 2.4, 0.45, -0.8, "#9a3412"));
  activeGroup.add(makeLabel("Alternate interior", -2.6, 0.45, 0.8, "#0f766e"));
  activeGroup.add(makeLabel("equal", -2.4, 0.45, -2.8, "#0f766e"));
}

function buildTriangle() {
  const a = new THREE.Vector3(-3.6, 0, -1.5);
  const b = new THREE.Vector3(3.6, 0, -1.5);
  const c = new THREE.Vector3(-0.7, 0, 3.4);

  activeGroup.add(makeLine(a, b, 0x0f172a));
  activeGroup.add(makeLine(b, c, 0x0f172a));
  activeGroup.add(makeLine(c, a, 0x0f172a));

  activeGroup.add(makeArc(0.9, 0, 40, 0xf97316, 0.04, 0.01).translateX(-3.6).translateZ(-1.5));
  activeGroup.add(makeArc(0.9, 130, 205, 0x3b82f6, 0.04, 0.01).translateX(3.6).translateZ(-1.5));
  activeGroup.add(makeArc(0.9, 245, 320, 0x10b981, 0.04, 0.01).translateX(-0.7).translateZ(3.4));

  activeGroup.add(makeLabel("40°", -2.5, 0.2, -1.1));
  activeGroup.add(makeLabel("65°", 2.45, 0.2, -1));
  activeGroup.add(makeLabel("75°", -0.7, 0.2, 2.35));
  activeGroup.add(makeLabel("40 + 65 + 75 = 180°", -0.1, 1.15, -3.1, "#1d4ed8"));
}

function buildModel(key) {
  clearGroup(activeGroup);
  setTheoremText(key);

  if (key === "complementary") buildComplementary();
  else if (key === "supplementary") buildSupplementary();
  else if (key === "vertical") buildVertical();
  else if (key === "parallel") buildParallel();
  else buildTriangle();
}

modelSelect.addEventListener("change", () => buildModel(modelSelect.value));
buildModel(modelSelect.value);

function onResize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

window.addEventListener("resize", onResize);

function animate() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
animate();
