import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

test("test_renderer_pixel_sampling_disables_smoothing_for_all_characters", async () => {
  // Arrange
  const rendererPath = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../src/taskbar-pet/renderer.js",
  );
  const rendererSource = await readFile(rendererPath, "utf8");

  // Act
  const smoothingAssignment = rendererSource.match(
    /petContext\.imageSmoothingEnabled\s*=\s*([^;]+);/,
  );
  const qualityAssignment = rendererSource.match(
    /petContext\.imageSmoothingQuality\s*=\s*([^;]+);/,
  );

  // Assert
  assert.ok(smoothingAssignment, "renderer must set imageSmoothingEnabled explicitly");
  assert.equal(smoothingAssignment[1].trim(), "false");
  assert.ok(qualityAssignment, "renderer must set imageSmoothingQuality explicitly");
  assert.equal(qualityAssignment[1].trim(), '"low"');
  assert.doesNotMatch(
    rendererSource,
    /imageSmoothingEnabled\s*=\s*config\.character/,
  );
});
