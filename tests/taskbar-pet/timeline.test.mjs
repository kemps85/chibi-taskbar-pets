import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FrameTimeline, frameIndexAt, frameIndexForClip, IdleSequenceTimeline, millisecondsUntilNextFrame, totalDurationMs } from "../../src/taskbar-pet/timeline.js";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

test("test_timeline_manifest_durations_select_exact_boundary_without_blending", () => {
  // Arrange
  const durations = [67, 67, 66];

  // Act / Assert
  assert.equal(totalDurationMs(durations), 200);
  assert.equal(frameIndexAt(0, durations), 0);
  assert.equal(frameIndexAt(66, durations), 0);
  assert.equal(frameIndexAt(67, durations), 1);
  assert.equal(frameIndexAt(134, durations), 2);
  assert.equal(frameIndexAt(200, durations), 0);
  assert.equal(millisecondsUntilNextFrame(67, durations), 67);
});

test("test_timeline_long_elapsed_time_loops_to_authored_frame", () => {
  // Arrange
  const durations = [100, 200];
  const timeline = new FrameTimeline(durations, () => 0);

  // Act
  timeline.start(1000);

  // Assert
  assert.equal(timeline.frameAt(1099), 0);
  assert.equal(timeline.frameAt(1100), 1);
  assert.equal(timeline.frameAt(1300), 0);
});

test("test_timeline_rejects_empty_or_non_positive_duration_contract", () => {
  // Arrange / Act / Assert
  assert.throws(() => totalDurationMs([]), /non-empty/);
  assert.throws(() => totalDurationMs([67, 0]), /positive/);
});

test("test_timeline_once_clip_holds_last_frame_instead_of_looping", () => {
  const clip = { durationsMs: [100, 100], loopMode: "once" };
  assert.equal(frameIndexForClip(clip, 0), 0);
  assert.equal(frameIndexForClip(clip, 100), 1);
  assert.equal(frameIndexForClip(clip, 500), 1);
});

test("test_timeline_segmented_clip_enters_loops_then_exits", () => {
  const clip = {
    durationsMs: [100, 100, 100, 100],
    loopMode: "segmented-enter-loop-exit",
    segments: {
      enter: { start: 0, end: 0 },
      loop: { start: 1, end: 2 },
      exit: { start: 3, end: 3 },
    },
  };
  assert.equal(frameIndexForClip(clip, 50, 1000), 0);
  assert.equal(frameIndexForClip(clip, 100, 900), 1);
  assert.equal(frameIndexForClip(clip, 200, 800), 2);
  assert.equal(frameIndexForClip(clip, 300, 500), 1);
  assert.equal(frameIndexForClip(clip, 900, 50), 3);
});

test("test_timeline_real_manifest_matches_every_boundary_across_multiple_loops", () => {
  // Arrange
  const manifestPath = path.join(
    repositoryRoot,
    "assets/generated/pixel-chibi/production-v2/firefly/idle-sequences/production-v2-smooth/firefly-idle-animation-manifest.json",
  );
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const durations = manifest.human_module_sword_idle.frame_durations_ms;
  const total = totalDurationMs(durations);
  let boundary = 0;

  // Act / Assert
  for (let index = 0; index < durations.length; index += 1) {
    for (const loop of [0, 1, 10, 1000]) {
      const loopOffset = loop * total;
      assert.equal(frameIndexAt(loopOffset + boundary, durations), index);
      assert.equal(frameIndexAt(loopOffset + boundary + durations[index] - 0.001, durations), index);
    }
    boundary += durations[index];
  }
  assert.equal(boundary, 10950);
});

test("test_idle_schedule_waits_one_minute_between_complete_animations", () => {
  // Arrange
  const durations = [67, 67, 66];
  const timeline = new IdleSequenceTimeline(durations, 60000, () => 0);
  timeline.start(1000);

  // Act / Assert: frame 000 is the resting pose for a full minute.
  assert.equal(timeline.frameAt(1000), 0);
  assert.equal(timeline.frameAt(60999.999), 0);
  assert.equal(timeline.frameAt(61000), 0);
  assert.equal(timeline.frameAt(61067), 1);
  assert.equal(timeline.frameAt(61134), 2);
  assert.equal(timeline.frameAt(61200), 0);
  assert.equal(timeline.frameAt(121199.999), 0);
  assert.equal(timeline.frameAt(121267), 1);
});
