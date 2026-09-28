import assert from "node:assert/strict";
import test from "node:test";
import { BehaviorEngine } from "../../src/taskbar-pet/behavior-engine.js";
import {
  buildCharacterRuntimePayload,
  resolveActionDurations,
  validateBehaviorPackManifest,
} from "../../src/taskbar-pet/m1-runtime.js";

const REQUIRED = ["idle", "walk", "hunger_cue", "eat", "sleep_cue", "sleep_enter", "sleep_loop", "wake"];

function stableManifest(character, signatureId = "signature") {
  const clips = Object.fromEntries(REQUIRED.map((id) => [id, {
    frames: "clips/" + id + "/right/frames",
    frame_name_pattern: "frame-{index:000}.png",
    frame_count: 2,
    right_anchor: { x: 64, y: 120 },
    frame_durations_ms: [100, 200],
    loop_policy: id === "sleep_loop" || id === "idle" || id === "walk" ? "loop" : "once",
  }]));
  clips[signatureId] = signatureId === "module_sword"
    ? {
      frames: "clips/module_sword/right/frames",
      frame_name_pattern: "frame-{index:000}.png",
      frame_count: 2,
      right_anchor: { x: 64, y: 120 },
      frame_durations_ms: [50, 50],
      loop_policy: "once",
    }
    : {
      frames: "clips/signature/right/frames",
      frame_name_pattern: "frame-{index:000}.png",
      frame_count: 4,
      right_anchor: { x: 64, y: 120 },
      frame_durations_ms: [50, 50, 50, 50],
      loop_policy: "segmented-enter-loop-exit",
      segments: {
        enter: { start: 0, end: 0 },
        loop: { start: 1, end: 2 },
        exit: { start: 3, end: 3 },
      },
    };
  clips.eat = {
    frames: "clips/eat/right/frames",
    frame_name_pattern: "frame-{index:000}.png",
    frame_count: 2,
    right_anchor: { x: 64, y: 120 },
    frame_durations_ms: [80, 80],
    loop_policy: "once",
  };
  return {
    status: "PASS",
    schema_version: 1,
    character_id: character,
    canvas: { width: 160, height: 144 },
    master_direction: "right",
    left_rendering: {
      strategy: "mirror-right-at-runtime",
      anchor_formula: "canvas.width-right_anchor.x",
    },
    required_clips: [...REQUIRED, signatureId],
    clips,
  };
}

test("test_m1_runtime_stable_manifest_uses_exact_clip_contract", () => {
  const manifest = stableManifest("miyabi");
  const report = validateBehaviorPackManifest(manifest, "miyabi", [...REQUIRED, "signature"]);
  assert.equal(report.ok, true);
  const payload = buildCharacterRuntimePayload({
    character: "miyabi",
    manifest,
    requiredClips: [...REQUIRED, "signature"],
    strictManifest: true,
    frameUrlFor: (clipId, index) => "pet-asset://miyabi/" + clipId + "/frame-" + index + ".png",
  });
  assert.deepEqual(Object.keys(payload.clips), [
    "idle", "walk", "hunger_cue", "eat", "sleep_cue", "sleep_enter", "sleep_loop", "wake", "spirit_tail",
  ]);
  assert.equal(payload.clips.spirit_tail.frames[1], "pet-asset://miyabi/signature/frame-1.png");
});

test("test_m1_runtime_stable_manifest_rejects_missing_direction_and_loop_contract", () => {
  const missingDirection = stableManifest("miyabi");
  delete missingDirection.left_rendering;
  assert.equal(validateBehaviorPackManifest(
    missingDirection,
    "miyabi",
    [...REQUIRED, "signature"],
  ).ok, false);

  const missingPolicy = stableManifest("miyabi");
  delete missingPolicy.clips.walk.loop_policy;
  assert.equal(validateBehaviorPackManifest(
    missingPolicy,
    "miyabi",
    [...REQUIRED, "signature"],
  ).ok, false);

  const missingSegments = stableManifest("miyabi");
  delete missingSegments.clips.signature.segments;
  assert.equal(validateBehaviorPackManifest(
    missingSegments,
    "miyabi",
    [...REQUIRED, "signature"],
  ).ok, false);
});

test("test_m1_runtime_stable_source_cannot_masquerade_as_legacy_manifest", () => {
  const masquerade = stableManifest("miyabi");
  delete masquerade.schema_version;
  delete masquerade.character_id;
  masquerade.character = "miyabi";
  delete masquerade.master_direction;
  delete masquerade.left_rendering;
  delete masquerade.required_clips;
  for (const clip of Object.values(masquerade.clips)) {
    delete clip.frame_name_pattern;
    delete clip.loop_policy;
  }
  const report = validateBehaviorPackManifest(
    masquerade,
    "miyabi",
    [...REQUIRED, "signature"],
    { strictStable: true },
  );
  assert.equal(report.ok, false);
});

test("test_m1_runtime_generated_aliases_map_to_canonical_renderer_ids", () => {
  const stable = stableManifest("miyabi");
  const clips = { ...stable.clips };
  clips.stand = clips.idle;
  clips.hungry_notice = clips.hunger_cue;
  clips.sleepy_notice = clips.sleep_cue;
  delete clips.idle;
  delete clips.hunger_cue;
  delete clips.sleep_cue;
  const legacy = {
    status: "PASS",
    character: "miyabi",
    canvas_size: [160, 144],
    anchor: { right: [64, 120] },
    clips,
  };
  const payload = buildCharacterRuntimePayload({
    character: "miyabi",
    manifest: legacy,
    requiredClips: [...REQUIRED, "spirit_tail"],
    frameUrlFor: (clipId, index) => "legacy://" + clipId + "/" + index,
  });
  assert.equal(payload.clips.idle.id, "idle");
  assert.equal(payload.clips.hunger_cue.id, "hunger_cue");
  assert.equal(payload.clips.sleep_cue.id, "sleep_cue");
});

test("test_m1_runtime_reference_clip_uses_approved_timing_when_frame_count_is_absent", () => {
  const manifest = stableManifest("firefly", "module_sword");
  manifest.clips.module_sword = {
    type: "approved_reference_clip",
    clip: "module_sword",
    loop_mode: "reference",
  };
  const referenceManifest = {
    status: "PASS",
    human_module_sword_idle: {
      logical_frame_count: 3,
      frame_durations_ms: [67, 67, 66],
    },
  };
  const payload = buildCharacterRuntimePayload({
    character: "firefly",
    manifest,
    referenceManifest,
    requiredClips: [...REQUIRED, "module_sword"],
    frameUrlFor: (clipId, index) => "pet-asset://firefly/" + clipId + "/" + index,
    referenceFrameUrlFor: (index) => "pet-asset://firefly/module_sword/" + index,
  });
  assert.equal(payload.clips.module_sword.frameCount, 3);
  assert.deepEqual(payload.clips.module_sword.durationsMs, [67, 67, 66]);
  assert.equal(payload.clips.module_sword.reference, true);
});

test("test_m1_runtime_reference_clip_without_approved_source_fails_closed", () => {
  const manifest = stableManifest("firefly", "module_sword");
  manifest.clips.module_sword = { type: "approved_reference_clip" };
  assert.throws(() => buildCharacterRuntimePayload({
    character: "firefly",
    manifest,
    requiredClips: [...REQUIRED, "module_sword"],
    frameUrlFor: () => "blocked",
  }), /approved source manifest and frame resolver/);
});

test("test_m1_runtime_behavior_cycle_walks_then_returns_to_random_action", () => {
  let now = 0;
  const engine = new BehaviorEngine({
    character: "miyabi",
    clock: () => now,
    rng: () => 0,
    config: {
      ordinaryActions: ["walk", "pause", "idle"],
      movement: {
        workArea: { minX: 100, maxX: 500 },
        minDistance: 100,
        maxDistance: 100,
        speedDipPerSecond: 100,
      },
      actions: {
        walk: { weight: 1, durationMs: 0 },
        pause: { weight: 1, durationMs: 1 },
        idle: { weight: 1, durationMs: 1 },
      },
    },
    initialAnchorX: 300,
  });
  const first = engine.tick(now);
  assert.equal(first.action, "walk");
  now = 500;
  const moving = engine.tick(now);
  assert.notEqual(moving.anchorX, first.anchorX);
  now = 1200;
  const afterWalk = engine.tick(now);
  assert.equal(afterWalk.action, "walk");
  assert.notEqual(afterWalk.anchorX, first.anchorX);
});

test("test_m1_runtime_behavior_sleep_phases_keep_authored_one_shot_durations", () => {
  let now = 0;
  const engine = new BehaviorEngine({
    character: "firefly",
    clock: () => now,
    rng: () => 0,
    initialNeeds: { sleepiness: 0.9 },
    config: {
      ordinaryActions: ["idle"],
      actions: {
        idle: { weight: 1, durationMs: 1 },
        sleep_cue: { durationMs: 1200 },
        sleep_enter: { durationMs: 800 },
        sleep_loop: { durationMs: 0 },
        wake: { durationMs: 400 },
      },
      sleep: {
        cueAction: "sleep_cue",
        enterAction: "sleep_enter",
        sleepAction: "sleep_loop",
        wakeAction: "wake",
        minDurationMs: 8000,
        maxDurationMs: 8000,
        forcedAt: 0.9,
      },
    },
  });
  assert.equal(engine.tick(now).action, "sleep_cue");
  now = 1199;
  assert.equal(engine.tick(now).action, "sleep_cue");
  now = 1200;
  assert.equal(engine.tick(now).action, "sleep_enter");
  now = 2000;
  assert.equal(engine.tick(now).action, "sleep_loop");
  assert.equal(engine.snapshot(now).deadline, 10000);
});

test("test_m1_runtime_feed_resets_hunger_and_plays_eat_one_shot", () => {
  const engine = new BehaviorEngine({
    character: "miyabi",
    clock: () => 0,
    initialNeeds: { hunger: 1 },
    config: {
      ordinaryActions: ["idle"],
      actions: {
        idle: { weight: 1, durationMs: 1000 },
        hungry_notice: { durationMs: 300 },
        eat: { durationMs: 320 },
      },
      hunger: { noticeAction: "hungry_notice", urgentAt: 0.6 },
    },
  });
  assert.equal(engine.tick(0).action, "hungry_notice");
  const fed = engine.feed(10);
  assert.equal(fed.action, "eat");
  assert.equal(fed.needs.hunger, 0);
  assert.equal(fed.deadline, 330);
});

test("test_m1_runtime_module_sword_action_uses_complete_authored_duration", () => {
  const actions = resolveActionDurations([{
    id: "module_sword",
    clip: "module_sword",
    durationSource: "clip-pack-frameDurationsMs",
    atomic: true,
  }], {
    module_sword: { durationsMs: [67, 67, 66] },
  });
  assert.equal(actions[0].durationMs, 200);
  assert.equal(actions[0].atomic, true);
});

function withAnchorY(manifest, y) {
  for (const clip of Object.values(manifest.clips)) clip.right_anchor = { x: 64, y };
  return manifest;
}

test("test_m1_runtime_pack_anchor_row_sets_payload_baseline", () => {
  // Arrange: a pack authored with the feet on row 142 (full headroom above)
  const manifest = withAnchorY(stableManifest("miyabi"), 142);
  // Act
  const payload = buildCharacterRuntimePayload({
    character: "miyabi",
    manifest,
    requiredClips: [...REQUIRED, "signature"],
    strictManifest: true,
    frameUrlFor: (clipId, index) => "pet-asset://miyabi/" + clipId + "/frame-" + index + ".png",
  });
  // Assert
  assert.deepEqual(payload.anchor, { x: 64, y: 142 });
});

test("test_m1_runtime_pack_anchor_row_outside_canvas_or_mixed_is_rejected", () => {
  // Arrange
  const outside = withAnchorY(stableManifest("miyabi"), 150);
  const mixed = withAnchorY(stableManifest("miyabi"), 142);
  mixed.clips.walk.right_anchor = { x: 64, y: 120 };
  // Act
  const outsideReport = validateBehaviorPackManifest(outside, "miyabi", [...REQUIRED, "signature"]);
  const mixedReport = validateBehaviorPackManifest(mixed, "miyabi", [...REQUIRED, "signature"]);
  // Assert
  assert.equal(outsideReport.ok, false);
  assert.equal(mixedReport.ok, false);
  assert.ok(mixedReport.errors.some((error) => error.includes("must match the other clips")));
});
