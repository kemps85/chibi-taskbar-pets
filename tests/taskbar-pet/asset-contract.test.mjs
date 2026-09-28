import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { validateHumanAnimationContract, validateRuntimeConfig } from "../../src/taskbar-pet/asset-contract.js";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const runtimeConfig = JSON.parse(readFileSync(path.join(repositoryRoot, "assets/data/taskbar_pet_runtime_v1.json"), "utf8"));

test("test_asset_contract_approved_firefly_human_right_animation_is_complete", () => {
  // Arrange
  const manifest = JSON.parse(readFileSync(path.join(repositoryRoot, runtimeConfig.source.manifestPath), "utf8"));
  const frameNames = readdirSync(path.join(repositoryRoot, runtimeConfig.source.framesDirectory)).sort();

  // Act
  const report = validateHumanAnimationContract(manifest, frameNames, runtimeConfig);

  // Assert
  assert.equal(report.ok, true, report.errors.join("; "));
  assert.equal(report.frameCount, 164);
  assert.equal(report.durationsMs.length, 164);
  assert.equal(report.durationsMs.reduce((sum, duration) => sum + duration, 0), 10950);
});

test("test_asset_contract_rejects_missing_right_facing_frame", () => {
  // Arrange
  const manifest = {
    status: "PASS",
    human_module_sword_idle: {
      logical_frame_count: 164,
      logical_fps: 15,
      canvas_size: [160, 144],
      directional_anchors: { right: [64, 120] },
      frame_durations_ms: runtimeConfig.timeline.frameCount === 164
        ? [...Array.from({ length: 163 }, () => 67), 29]
        : [],
    },
  };
  const frameNames = Array.from({ length: 163 }, (_, index) => `frame-${String(index).padStart(3, "0")}.png`);

  // Act
  const report = validateHumanAnimationContract(manifest, frameNames, runtimeConfig);

  // Assert
  assert.equal(report.ok, false);
  assert.match(report.errors.join("; "), /missing right-facing frames/);
});

test("test_runtime_config_rejects_path_traversal_and_scale_drift", () => {
  // Arrange
  const unsafe = structuredClone(runtimeConfig);
  unsafe.source.framesDirectory = "../outside";
  unsafe.display.renderScale = 2;

  // Act
  const report = validateRuntimeConfig(unsafe);

  // Assert
  assert.equal(report.ok, false);
  assert.match(report.errors.join("; "), /safe repository-relative path/);
  assert.match(report.errors.join("; "), /display.renderScale must be 1/);
});
