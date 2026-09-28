import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { buildCharacterRuntimePayload, validateBehaviorPackManifest } from "../../../../../src/taskbar-pet/m1-runtime.js";

const manifestPath = "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/full-pack/clip-packs/miyabi/v1/manifest.json";
const candidate = JSON.parse(await readFile(manifestPath, "utf8"));
const validationManifest = structuredClone(candidate);
validationManifest.status = "PASS";
const required = validationManifest.required_clips;
const report = validateBehaviorPackManifest(validationManifest, "miyabi", required, { strictStable: true });
assert.equal(report.ok, true, report.errors.join("; "));
const payload = buildCharacterRuntimePayload({
  character: "miyabi",
  manifest: validationManifest,
  requiredClips: required,
  strictManifest: true,
  frameUrlFor: (clipId, index) => `candidate://${clipId}/frame-${String(index).padStart(3, "0")}.png`,
});
assert.equal(payload.canvasSize.width, 160);
assert.equal(payload.canvasSize.height, 144);
assert.deepEqual(payload.anchor, { x: 64, y: 120 });
assert.equal(payload.clips.spirit_tail.frameCount, 32);
assert.equal(payload.clips.spirit_tail.durationsMs.length, 32);
assert.equal(payload.clips.spirit_tail.loopMode, "segmented-enter-loop-exit");
assert.deepEqual(payload.clips.spirit_tail.segments, { enter: { start: 0, end: 12 }, loop: { start: 13, end: 24 }, exit: { start: 25, end: 31 } });
assert.equal(payload.clips.sleep_cue.frameCount, 8);
assert.equal(payload.clips.sleep_cue.durationsMs.reduce((a, b) => a + b, 0), 1200);
assert.equal(payload.clips.sleep_cue.loopMode, "once");
assert.equal(payload.clips.hunger_cue.frameCount, 8);
assert.equal(payload.clips.hunger_cue.durationsMs.reduce((a, b) => a + b, 0), 1200);
assert.equal(payload.clips.hunger_cue.loopMode, "once");
assert.equal(payload.clips.walk.frameCount, 8);
assert.equal(payload.clips.walk.durationsMs.reduce((a, b) => a + b, 0), 800);
assert.equal(payload.clips.walk.loopMode, "loop");
assert.equal(payload.clips.sleep_loop.frameCount, 12);
assert.equal(payload.clips.sleep_loop.durationsMs.reduce((a, b) => a + b, 0), 3000);
assert.equal(payload.clips.sleep_loop.loopMode, "loop");
console.log(JSON.stringify({ status: "PASS", candidateManifest: manifestPath, spiritTail: { frameCount: payload.clips.spirit_tail.frameCount, durationMs: payload.clips.spirit_tail.durationsMs.reduce((a,b)=>a+b,0), loopMode: payload.clips.spirit_tail.loopMode, segments: payload.clips.spirit_tail.segments }, note: "status PASS was used only in memory to exercise the existing runtime contract; candidate file remains pending" }, null, 2));

