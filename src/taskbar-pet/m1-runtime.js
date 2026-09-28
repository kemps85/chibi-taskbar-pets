import { totalDurationMs } from "./timeline.js";
import { DEFAULT_CHARACTER, normalizeCharacter, signatureClipId } from "./character-selection.js";

/**
 * Required M1 clip ids. Generated development packs may use the documented
 * legacy aliases; stable packs use these exact ids.
 * @type {readonly string[]}
 */
export const REQUIRED_M1_CLIPS = Object.freeze([
  "idle",
  "walk",
  "hunger_cue",
  "eat",
  "sleep_cue",
  "sleep_enter",
  "sleep_loop",
  "wake",
]);

/**
 * Legacy generated-pack aliases accepted only by the development fallback.
 * @type {Readonly<Record<string, string>>}
 */
export const DEVELOPMENT_CLIP_ALIASES = Object.freeze({
  idle: "stand",
  hunger_cue: "hungry_notice",
  sleep_cue: "sleepy_notice",
});

/**
 * Resolve a canonical behavior clip to the id present in a stable or legacy
 * manifest. Stable packs may call the character-specific signature clip
 * `signature`; generated packs retain their historical ids.
 * @param {Record<string, object>} clips manifest clip table
 * @param {string} clipId canonical behavior clip id
 * @returns {string|undefined} manifest clip id
 */
export function resolveManifestClipId(clips, clipId) {
  if (clips?.[clipId]) {
    return clipId;
  }
  if (clipId === "signature") {
    return clips?.spirit_tail ? "spirit_tail" : clips?.module_sword ? "module_sword" : undefined;
  }
  if (clipId === "spirit_tail" && clips?.signature) {
    return "signature";
  }
  if (clipId === "module_sword" && clips?.signature) {
    return "signature";
  }
  return DEVELOPMENT_CLIP_ALIASES[clipId];
}

/**
 * Validate a character behavior-pack manifest without filesystem access.
 * @param {unknown} manifest parsed character manifest
 * @param {string} character expected character id
 * @param {readonly string[]} [requiredClips=REQUIRED_M1_CLIPS] required clip ids
 * @param {{strictStable?: boolean}} [options] trusted source classification
 * @returns {{ok: boolean, errors: string[], clips: Record<string, object>}}
 */
export function validateBehaviorPackManifest(
  manifest,
  character,
  requiredClips = REQUIRED_M1_CLIPS,
  { strictStable = false } = {},
) {
  const errors = [];
  const clips = manifest?.clips;
  const stable = strictStable || manifest?.schema_version !== undefined || manifest?.character_id !== undefined;
  if (!manifest || typeof manifest !== "object") {
    errors.push("manifest is missing");
  }
  if (manifest?.status !== "PASS") {
    errors.push("manifest.status must be PASS");
  }
  if ((manifest?.character ?? manifest?.character_id) !== character) {
    errors.push("manifest.character_id must be " + character);
  }
  const canvas = manifest?.canvas ?? manifest?.canvas_size;
  const canvasSize = Array.isArray(canvas) ? canvas : [canvas?.width, canvas?.height];
  if (JSON.stringify(canvasSize) !== JSON.stringify([160, 144])) {
    errors.push("manifest.canvas must be 160x144");
  }
  if (!clips || typeof clips !== "object") {
    errors.push("manifest.clips is missing");
    return { ok: false, errors, clips: {} };
  }

  if (stable) {
    if (manifest.schema_version !== 1) errors.push("manifest.schema_version must be 1");
    if (manifest.master_direction !== "right") errors.push("manifest.master_direction must be right");
    if (manifest.left_rendering?.strategy !== "mirror-right-at-runtime") {
      errors.push("manifest.left_rendering.strategy must mirror right at runtime");
    }
    if (manifest.left_rendering?.anchor_formula !== "canvas.width-right_anchor.x") {
      errors.push("manifest.left_rendering.anchor_formula is invalid");
    }
    if (!Array.isArray(manifest.required_clips)
      || requiredClips.some((clipId) => !manifest.required_clips.includes(clipId))) {
      errors.push("manifest.required_clips must contain the complete runtime contract");
    }
  }

  if (manifest?.anchor) {
    const packAnchor = normalizeAnchor(manifest.anchor.right);
    if (!packAnchor || packAnchor.x !== 64 || !isValidAnchorY(packAnchor.y)) {
      errors.push("manifest.anchor.right must be [64, y] with y in 100..143");
    }
  }
  let packAnchorY;
  if (manifest?.master_direction && manifest.master_direction !== "right") {
    errors.push("manifest.master_direction must be right");
  }
  for (const clipId of requiredClips) {
    const actualId = resolveManifestClipId(clips, clipId);
    if (!actualId || !clips[actualId]) {
      errors.push(`required clip ${clipId} is missing`);
      continue;
    }
    const clip = clips[actualId];
    if (clip.type === "approved_reference_clip") {
      if (clipId !== "module_sword" && clipId !== "signature") {
        errors.push(`clip ${clipId} cannot be an unresolved reference clip`);
      }
      continue;
    }
    const rightAnchor = normalizeAnchor(clip.right_anchor ?? manifest?.anchor?.right);
    if (!rightAnchor || rightAnchor.x !== 64 || !isValidAnchorY(rightAnchor.y)) {
      errors.push("clip " + clipId + " right_anchor must be [64, y] with y in 100..143");
    } else if (packAnchorY === undefined) {
      packAnchorY = rightAnchor.y;
    } else if (rightAnchor.y !== packAnchorY) {
      errors.push("clip " + clipId + " right_anchor.y must match the other clips");
    }
    if (stable) {
      if (clip.frame_name_pattern !== "frame-{index:000}.png") {
        errors.push(`clip ${clipId} frame_name_pattern is invalid`);
      }
      if (clip.frames !== `clips/${actualId}/right/frames`) {
        errors.push(`clip ${clipId} must use its contained right-master frame path`);
      }
      if (!["once", "loop", "segmented-enter-loop-exit"].includes(clip.loop_policy)) {
        errors.push(`clip ${clipId} loop_policy is invalid`);
      }
      // v1 packs used a segmented spirit_tail; the v2 crescent unsheath is a one-shot.
      if (character === "miyabi" && ["signature", "spirit_tail"].includes(clipId)
        && !["segmented-enter-loop-exit", "once"].includes(clip.loop_policy)) {
        errors.push("Miyabi spirit_tail must use segmented-enter-loop-exit or once");
      }
      if (character === "firefly" && ["signature", "module_sword"].includes(clipId)
        && clip.loop_policy !== "once") {
        errors.push("Firefly module_sword must use once");
      }
    }
    const frameCount = Number(clip.frame_count);
    const durations = clip.frame_durations_ms;
    if (!Number.isInteger(frameCount) || frameCount <= 0) {
      errors.push(`clip ${clipId} frame_count must be a positive integer`);
    }
    if (!Array.isArray(durations) || durations.length !== frameCount || durations.some((duration) => !Number.isInteger(duration) || duration <= 0)) {
      errors.push(`clip ${clipId} frame_durations_ms must match frame_count with positive integers`);
    }
    if (typeof clip.frames !== "string" || clip.frames.length === 0) {
      errors.push(`clip ${clipId} frames path is missing`);
    }
    if (clip.loop_policy === "segmented-enter-loop-exit") {
      const segments = clip.segments;
      const ranges = [segments?.enter, segments?.loop, segments?.exit];
      const validSegments = ranges.every((range) => Number.isInteger(range?.start)
        && Number.isInteger(range?.end) && range.start >= 0 && range.end >= range.start
        && range.end < frameCount)
        && ranges[0].start === 0
        && ranges[0].end < ranges[1].start
        && ranges[1].end < ranges[2].start
        && ranges[2].end === frameCount - 1;
      if (!validSegments) errors.push(`clip ${clipId} segmented ranges are invalid`);
    }
  }
  return { ok: errors.length === 0, errors, clips, anchorY: packAnchorY ?? DEFAULT_ANCHOR_Y };
}

/** Default baseline row: the taskbar's top edge sits on canvas row 120 unless a pack declares its own. */
const DEFAULT_ANCHOR_Y = 120;

/**
 * Normalize a right anchor given as [x, y] or {x, y}.
 * @param {unknown} anchor manifest anchor value
 * @returns {{x: number, y: number}|null} normalized anchor, or null when malformed
 */
function normalizeAnchor(anchor) {
  if (Array.isArray(anchor) && anchor.length === 2) return { x: anchor[0], y: anchor[1] };
  if (anchor && typeof anchor === "object" && "x" in anchor && "y" in anchor) return { x: anchor.x, y: anchor.y };
  return null;
}

/**
 * A pack may put its feet on any row that leaves headroom inside the 144-row canvas.
 * @param {unknown} y anchor row
 * @returns {boolean} whether the row is an allowed baseline
 */
function isValidAnchorY(y) {
  return Number.isInteger(y) && y >= 100 && y <= 143;
}

/**
 * Convert stable or development manifest data into renderer-safe clip data.
 * Every frame URL is supplied by the trusted main-process resolver; this
 * function never accepts arbitrary filesystem paths from the renderer.
 *
 * @param {object} options payload inputs
 * @param {string} options.character character id
 * @param {object} options.manifest validated character behavior manifest
 * @param {object} [options.referenceManifest] approved Firefly reference manifest
 * @param {(clipId: string, frameIndex: number) => string} options.frameUrlFor allowlisted URL factory
 * @param {(frameIndex: number) => string} [options.referenceFrameUrlFor] allowlisted reference URL factory
 * @param {readonly string[]} [options.requiredClips] required clip ids
 * @param {boolean} [options.strictManifest=false] require the stable self-contained contract
 * @returns {{character: string, canvasSize: {width: number, height: number}, anchor: {x: number, y: number}, clips: Record<string, object>, actionClips: Record<string, string>}}
 */
export function buildCharacterRuntimePayload({
  character = DEFAULT_CHARACTER,
  manifest,
  referenceManifest,
  frameUrlFor,
  referenceFrameUrlFor,
  requiredClips = REQUIRED_M1_CLIPS,
  strictManifest = false,
}) {
  const normalizedCharacter = normalizeCharacter(character);
  const report = validateBehaviorPackManifest(
    manifest,
    normalizedCharacter,
    requiredClips,
    { strictStable: strictManifest },
  );
  if (!report.ok) {
    throw new Error(`Behavior pack rejected for ${normalizedCharacter}: ${report.errors.join("; ")}`);
  }
  if (typeof frameUrlFor !== "function") {
    throw new TypeError("frameUrlFor must be a function");
  }

  const clipPayload = {};
  const actionClips = {
    idle: "idle",
    pause: "idle",
    walk: "walk",
    hungry_notice: "hunger_cue",
    hunger_cue: "hunger_cue",
    feed: "eat",
    eat: "eat",
    sleep_cue: "sleep_cue",
    sleepy_notice: "sleep_cue",
    sleep_enter: "sleep_enter",
    sleep: "sleep_loop",
    sleep_loop: "sleep_loop",
    wake: "wake",
    signature: signatureClipId(normalizedCharacter),
    spirit_tail: "spirit_tail",
    module_sword: "module_sword",
  };

  for (const requiredId of requiredClips) {
    const actualId = resolveManifestClipId(report.clips, requiredId);
    if (!actualId) {
      continue;
    }
    const sourceClip = report.clips[actualId];
    const outputId = requiredId === "signature" ? signatureClipId(normalizedCharacter) : requiredId;
    if (sourceClip.type === "approved_reference_clip") {
      if (!referenceManifest?.human_module_sword_idle || typeof referenceFrameUrlFor !== "function") {
        throw new Error("Firefly module_sword reference clip has no frame_count; approved source manifest and frame resolver are required");
      }
      const reference = referenceManifest.human_module_sword_idle;
      const frameCount = Number(reference.logical_frame_count);
      const durationsMs = [...reference.frame_durations_ms];
      if (!Number.isInteger(frameCount) || durationsMs.length !== frameCount || totalDurationMs(durationsMs) <= 0) {
        throw new Error("Firefly module_sword reference manifest has no valid frame_count/timing");
      }
      clipPayload[outputId] = {
        id: outputId,
        frameCount,
        durationsMs,
        loopMode: "once",
        frames: Array.from({ length: frameCount }, (_, index) => referenceFrameUrlFor(index)),
        reference: true,
      };
      continue;
    }
    const frameCount = Number(sourceClip.frame_count);
    const durationsMs = [...sourceClip.frame_durations_ms];
    const loopPolicy = sourceClip.loop_mode ?? sourceClip.loop_policy;
    clipPayload[outputId] = {
      id: outputId,
      frameCount,
      durationsMs,
      loopMode: loopPolicy === "segmented-enter-loop-exit"
        ? "segmented-enter-loop-exit"
        : loopPolicy === "one_shot"
        ? "once"
        : loopPolicy === "loop" ? "loop" : "once",
      ...(sourceClip.segments ? { segments: structuredClone(sourceClip.segments) } : {}),
      frames: Array.from({ length: frameCount }, (_, index) => frameUrlFor(actualId, index)),
    };
  }

  const miyabiSignatureId = normalizedCharacter === "miyabi"
    ? resolveManifestClipId(report.clips, "spirit_tail")
    : undefined;
  if (miyabiSignatureId) {
    clipPayload.spirit_tail ??= buildSimpleClip(report.clips[miyabiSignatureId], "spirit_tail", frameUrlFor, miyabiSignatureId);
  }
  const eatId = resolveManifestClipId(report.clips, "eat");
  if (eatId && report.clips[eatId]?.type !== "approved_reference_clip") {
    clipPayload.eat ??= buildSimpleClip(report.clips[eatId], "eat", frameUrlFor, eatId);
  }
  if (normalizedCharacter === "firefly" && report.clips.module_sword?.type === "approved_reference_clip") {
    actionClips.module_sword = "module_sword";
  }
  return {
    character: normalizedCharacter,
    canvasSize: { width: 160, height: 144 },
    anchor: { x: 64, y: report.anchorY },
    clips: clipPayload,
    actionClips,
  };
}

/**
 * Fill action durations that explicitly come from authored clip timing.
 * Looping actions keep their configured random duration range, while a
 * one-shot such as Firefly's module sword remains active until its last frame.
 *
 * @param {readonly object[]} actions character action definitions
 * @param {Record<string, {durationsMs?: number[]}>} clips renderer clip table
 * @returns {object[]} cloned action definitions with resolved durations
 */
export function resolveActionDurations(actions, clips) {
  return (actions ?? []).map((action) => {
    if (!action || typeof action !== "object") {
      throw new TypeError("action definitions must be objects");
    }
    if (action.durationSource !== "clip-pack-frameDurationsMs") {
      return { ...action };
    }
    const clipId = action.clip ?? action.id;
    const durations = clips?.[clipId]?.durationsMs;
    if (!Array.isArray(durations) || durations.length === 0) {
      throw new Error(`Action ${action.id ?? clipId} requires authored clip timing`);
    }
    return { ...action, durationMs: totalDurationMs(durations) };
  });
}

/**
 * Build a non-required signature clip from a generated manifest.
 * @param {object} sourceClip source clip descriptor
 * @param {string} clipId output id
 * @param {(clipId: string, frameIndex: number) => string} frameUrlFor URL factory
 * @returns {object} renderer clip descriptor
 */
function buildSimpleClip(sourceClip, clipId, frameUrlFor, sourceClipId = clipId) {
  const frameCount = Number(sourceClip.frame_count);
  const loopPolicy = sourceClip.loop_mode ?? sourceClip.loop_policy;
  return {
    id: clipId,
    frameCount,
    durationsMs: [...sourceClip.frame_durations_ms],
    loopMode: loopPolicy === "segmented-enter-loop-exit"
      ? "segmented-enter-loop-exit"
      : loopPolicy === "loop" ? "loop" : "once",
    ...(sourceClip.segments ? { segments: structuredClone(sourceClip.segments) } : {}),
    frames: Array.from({ length: frameCount }, (_, index) => frameUrlFor(sourceClipId, index)),
  };
}
