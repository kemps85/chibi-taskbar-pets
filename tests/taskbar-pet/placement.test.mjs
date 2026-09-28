import test from "node:test";
import assert from "node:assert/strict";
import { calculateTaskbarPlacement, HUMAN_RIGHT_ANCHOR, isSupportedBottomTaskbar, PIXEL_SCALE } from "../../src/taskbar-pet/placement.js";

test("test_taskbar_placement_bottom_primary_work_area_uses_one_x_right_canvas", () => {
  // Arrange
  const workArea = { x: 0, y: 0, width: 1920, height: 1032 };

  // Act
  const placement = calculateTaskbarPlacement({ workArea });

  // Assert
  assert.deepEqual(placement, { x: 896, y: 912, width: 160, height: 144 });
  assert.equal(placement.y + HUMAN_RIGHT_ANCHOR.y * PIXEL_SCALE, workArea.height);
});

test("test_taskbar_placement_negative_display_origin_preserves_primary_origin", () => {
  // Arrange
  const workArea = { x: -1920, y: 0, width: 1920, height: 1040 };

  // Act
  const placement = calculateTaskbarPlacement({ workArea });

  // Assert
  assert.equal(placement.x, -1024);
  assert.equal(placement.y, 920);
});

test("test_taskbar_layout_accepts_only_visible_bottom_primary_taskbar", () => {
  // Arrange
  const bounds = { x: 0, y: 0, width: 1920, height: 1080 };

  // Act / Assert
  assert.equal(isSupportedBottomTaskbar(bounds, { x: 0, y: 0, width: 1920, height: 1032 }), true);
  assert.equal(isSupportedBottomTaskbar(bounds, bounds), false);
  assert.equal(isSupportedBottomTaskbar(bounds, { x: 48, y: 0, width: 1872, height: 1080 }), false);
  assert.equal(isSupportedBottomTaskbar(bounds, { x: 0, y: 48, width: 1920, height: 1032 }), false);
});

test("test_taskbar_placement_small_work_area_clamps_horizontal_canvas_to_work_area", () => {
  // Arrange
  const workArea = { x: 40, y: 12, width: 120, height: 500 };

  // Act
  const placement = calculateTaskbarPlacement({ workArea });

  // Assert
  assert.equal(placement.x, workArea.x);
  assert.equal(placement.y, workArea.y + workArea.height - 120);
});

test("test_taskbar_placement_runtime_anchor_moves_with_bounded_world_position", () => {
  // Arrange
  const workArea = { x: 0, y: 0, width: 1920, height: 1032 };

  // Act
  const placement = calculateTaskbarPlacement({ workArea, anchorX: 700 });

  // Assert
  assert.equal(placement.x, 636);
  assert.equal(placement.x + HUMAN_RIGHT_ANCHOR.x, 700);
});
