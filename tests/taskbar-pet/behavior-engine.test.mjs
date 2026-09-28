import test from "node:test";
import assert from "node:assert/strict";
import { BehaviorEngine } from "../../src/taskbar-pet/behavior-engine.js";

function createConfig(overrides = {}) {
  return {
    decisionIntervalMs: 0,
    immediateRepeat: { exclude: true, penalty: 0.1 },
    needs: {
      hunger: { ratePerSecond: 0.1, urgentAt: 0.5 },
      sleepiness: { ratePerSecond: 0.1, urgentAt: 0.6 },
    },
    movement: {
      workArea: { minX: 0, maxX: 100 },
      minDistance: 10,
      maxDistance: 20,
      speedPxPerSecond: 10,
    },
    actions: {
      walk: { weight: 1, durationMs: 100 },
      pause: { weight: 3, durationMs: 100 },
      signature: { weight: 1, durationMs: 100 },
    },
    hunger: {
      noticeAction: "hungry_notice",
      noticeDurationMs: 10,
      noticeCooldownMs: 0,
    },
    sleep: {
      cueAction: "sleep_cue",
      enterAction: "sleep_enter",
      sleepAction: "sleep",
      wakeAction: "wake",
      cueDurationMs: 10,
      enterDurationMs: 10,
      minDurationMs: 8000,
      maxDurationMs: 12000,
    },
    ...overrides,
  };
}

test("test_behavior_weighted_selection_uses_eligible_action_weights", () => {
  // Arrange
  const engine = new BehaviorEngine({
    character: "miyabi",
    config: createConfig(),
    rng: () => 0.2,
    clock: () => 0,
  });

  // Act
  const snapshot = engine.tick(0);

  // Assert
  assert.equal(snapshot.action, "pause");
  assert.equal(snapshot.character, "miyabi");
});

test("test_behavior_ordinary_decisions_randomly_choose_actions_without_fixed_sequence", () => {
  // Arrange
  const randomValues = [0.01, 0.99, 0.01, 0.99, 0.01];
  const engine = new BehaviorEngine({
    character: "firefly",
    config: createConfig(),
    rng: () => randomValues.shift() ?? 0.01,
    clock: () => 0,
  });

  // Act
  const first = engine.tick(0).action;
  const second = engine.tick(100).action;
  const third = engine.tick(200).action;

  // Assert
  assert.deepEqual([first, second, third], ["walk", "signature", "walk"]);
});

test("test_behavior_cooldown_and_immediate_repeat_exclusion_avoid_same_action", () => {
  // Arrange
  const engine = new BehaviorEngine({
    character: "firefly",
    config: createConfig({
      actions: {
        walk: { weight: 1, durationMs: 10, cooldownMs: 1000 },
        pause: { weight: 1, durationMs: 10, cooldownMs: 0 },
      },
    }),
    rng: () => 0,
    clock: () => 0,
  });

  // Act
  const first = engine.tick(0);
  const second = engine.tick(10);

  // Assert
  assert.equal(first.action, "walk");
  assert.equal(second.action, "pause");
  assert.ok(second.deadline > 10);
});

test("test_behavior_needs_accumulate_by_elapsed_real_time", () => {
  // Arrange
  const engine = new BehaviorEngine({
    character: "miyabi",
    config: createConfig(),
    rng: () => 0.5,
    clock: () => 0,
  });
  engine.tick(0);

  // Act
  const snapshot = engine.tick(5000);

  // Assert
  assert.equal(snapshot.needs.hunger, 0.5);
  assert.equal(snapshot.needs.sleepiness, 0.5);
  assert.equal(snapshot.needs.hungerUrgent, true);
  assert.equal(snapshot.needs.sleepUrgent, false);
});

test("test_behavior_urgent_sleep_runs_cue_enter_sleep_random_duration_then_wake", () => {
  // Arrange
  const randomValues = [0.5, 0.5, 0.5, 0.5];
  const engine = new BehaviorEngine({
    character: "firefly",
    config: createConfig({
      needs: {
        hunger: { ratePerSecond: 0, urgentAt: 1 },
        sleepiness: { ratePerSecond: 0, urgentAt: 0 },
      },
    }),
    initialNeeds: { hunger: 0, sleepiness: 1 },
    rng: () => randomValues.shift() ?? 0.5,
    clock: () => 0,
  });

  // Act
  const cue = engine.tick(0);
  const enter = engine.tick(10);
  const sleep = engine.tick(20);
  const wake = engine.tick(10020);

  // Assert
  assert.equal(cue.action, "sleep_cue");
  assert.equal(enter.action, "sleep_enter");
  assert.equal(sleep.action, "sleep");
  assert.equal(sleep.deadline, 10020);
  assert.equal(wake.action, "wake");
  assert.equal(wake.needs.sleepiness, 0.05);
});

test("test_behavior_hunger_notice_is_urgent_until_feed_resets_hunger", () => {
  // Arrange
  const engine = new BehaviorEngine({
    character: "miyabi",
    config: createConfig({
      needs: {
        hunger: { ratePerSecond: 0, urgentAt: 0.5 },
        sleepiness: { ratePerSecond: 0, urgentAt: 1 },
      },
    }),
    initialNeeds: { hunger: 0.5, sleepiness: 0 },
    rng: () => 0.5,
    clock: () => 0,
  });

  // Act
  const notice = engine.tick(0);
  engine.tick(10);
  const fed = engine.feed(11);
  const ordinary = engine.tick(11);

  // Assert
  assert.equal(notice.action, "hungry_notice");
  assert.equal(fed.needs.hunger, 0);
  assert.equal(fed.needs.hungerUrgent, false);
  assert.notEqual(ordinary.action, "hungry_notice");
});

test("test_behavior_hunger_notice_repeats_without_blocking_ordinary_actions", () => {
  const engine = new BehaviorEngine({
    character: "miyabi",
    config: createConfig({
      ordinaryActions: ["pause"],
      actions: {
        pause: { weight: 1, durationMs: 100 },
        hungry_notice: { durationMs: 10 },
      },
      needs: {
        hunger: { ratePerSecond: 0, urgentAt: 0.5 },
        sleepiness: { ratePerSecond: 0, urgentAt: 1 },
      },
      hunger: {
        noticeAction: "hungry_notice",
        cueRepeatMsAtThreshold: 20000,
        cueRepeatMsAtMaximum: 8000,
      },
    }),
    initialNeeds: { hunger: 0.5, sleepiness: 0 },
    rng: () => 0,
    clock: () => 0,
  });
  assert.equal(engine.tick(0).action, "hungry_notice");
  assert.equal(engine.tick(10).action, "pause");
  assert.equal(engine.tick(110).action, "pause");
  assert.equal(engine.tick(19999).action, "pause");
  assert.equal(engine.tick(20000).action, "hungry_notice");
});

test("test_behavior_snapshot_exposes_public_overlay_state", () => {
  // Arrange
  const engine = new BehaviorEngine({
    character: "firefly",
    config: createConfig(),
    initialAnchorX: 25,
    rng: () => 0.5,
    clock: () => 0,
  });

  // Act
  const snapshot = engine.snapshot(0);

  // Assert
  assert.deepEqual(Object.keys(snapshot).sort(), [
    "action",
    "anchorX",
    "character",
    "deadline",
    "direction",
    "needs",
    "remainingMs",
    "state",
  ]);
  assert.equal(snapshot.anchorX, 25);
  assert.equal(snapshot.direction, "right");
});
