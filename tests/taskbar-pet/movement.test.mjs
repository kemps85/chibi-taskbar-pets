import test from "node:test";
import assert from "node:assert/strict";
import {
  MovementController,
  chooseWalkTarget,
  directionForDelta,
} from "../../src/taskbar-pet/movement.js";

test("test_movement_choose_walk_target_uses_random_distance_and_stays_in_work_area", () => {
  // Arrange
  const randomValues = [0.9, 0.75];
  const rng = () => randomValues.shift() ?? 0;

  // Act
  const target = chooseWalkTarget({
    anchorX: 50,
    workArea: { minX: 0, maxX: 100 },
    minDistance: 20,
    maxDistance: 40,
    rng,
  });

  // Assert
  assert.equal(target, 85);
  assert.ok(target >= 0 && target <= 100);
});

test("test_movement_target_near_edge_clamps_distance_and_never_leaves_bounds", () => {
  // Arrange
  const controller = new MovementController({
    anchorX: 95,
    workArea: { minX: 0, maxX: 100 },
    minDistance: 30,
    maxDistance: 60,
    speedPxPerSecond: 1000,
    rng: () => 0.99,
  });

  // Act
  const target = controller.startWalk();
  controller.update(1000);

  // Assert
  assert.equal(target, 100);
  assert.equal(controller.anchorX, 100);
  assert.ok(controller.anchorX >= 0 && controller.anchorX <= 100);
});

test("test_movement_update_uses_delta_time_and_derives_direction_without_mirroring", () => {
  // Arrange
  const controller = new MovementController({
    anchorX: 20,
    workArea: { minX: 0, maxX: 100 },
    minDistance: 20,
    maxDistance: 20,
    speedPxPerSecond: 10,
    rng: () => 0.99,
  });
  controller.startWalk();

  // Act
  controller.update(500);

  // Assert
  assert.equal(controller.anchorX, 25);
  assert.equal(controller.direction, "right");
  assert.equal(directionForDelta(-1, "right"), "left");
  assert.equal(directionForDelta(0, "left"), "left");
});

test("test_movement_set_anchor_clamps_external_position_to_work_area", () => {
  // Arrange
  const controller = new MovementController({
    anchorX: 50,
    workArea: { x: 10, width: 80 },
    rng: () => 0.5,
  });

  // Act
  controller.setAnchorX(200);

  // Assert
  assert.equal(controller.anchorX, 90);
  assert.equal(controller.targetX, 90);
});
