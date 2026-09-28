import { totalDurationMs } from "./timeline.js";

/**
 * Validate the fixed M0 runtime configuration before it can influence paths or
 * native window behavior.
 * @param {unknown} runtimeConfig parsed external runtime configuration
 * @returns {{ok: boolean, errors: string[]}}
 */
export function validateRuntimeConfig(runtimeConfig) {
  const errors = [];
  const expected = [
    [runtimeConfig?.schemaVersion, 1, "schemaVersion"],
    [runtimeConfig?.milestone, "M0", "milestone"],
    [runtimeConfig?.runtime?.framework, "electron", "runtime.framework"],
    [runtimeConfig?.runtime?.frameworkVersion, "43.2.0", "runtime.frameworkVersion"],
    [runtimeConfig?.runtime?.platform, "win32", "runtime.platform"],
    [runtimeConfig?.source?.clip, "human_module_sword_idle", "source.clip"],
    [runtimeConfig?.source?.direction, "right", "source.direction"],
    [runtimeConfig?.timeline?.frameCount, 164, "timeline.frameCount"],
    [runtimeConfig?.timeline?.durationMs, 10950, "timeline.durationMs"],
    [runtimeConfig?.timeline?.restDurationMs, 60000, "timeline.restDurationMs"],
    [runtimeConfig?.timeline?.initialState, "resting-on-frame-000", "timeline.initialState"],
    [runtimeConfig?.timeline?.interpolation, "none", "timeline.interpolation"],
    [runtimeConfig?.display?.targetDisplay, "primary", "display.targetDisplay"],
    [runtimeConfig?.display?.taskbarEdge, "bottom", "display.taskbarEdge"],
    [runtimeConfig?.display?.renderScale, 1, "display.renderScale"],
    [runtimeConfig?.display?.canvas?.width, 160, "display.canvas.width"],
    [runtimeConfig?.display?.canvas?.height, 144, "display.canvas.height"],
    [runtimeConfig?.display?.anchor?.x, 64, "display.anchor.x"],
    [runtimeConfig?.display?.anchor?.y, 120, "display.anchor.y"],
    [runtimeConfig?.packaging?.resourceRoot, "pet-assets/firefly/m0-human-right", "packaging.resourceRoot"],
  ];
  for (const [actual, required, field] of expected) {
    if (actual !== required) {
      errors.push(`${field} must be ${required}`);
    }
  }
  for (const field of ["manifestPath", "framesDirectory"]) {
    const value = runtimeConfig?.source?.[field];
    if (typeof value !== "string" || value.length === 0 || pathLooksAbsoluteOrTraversing(value)) {
      errors.push(`source.${field} must be a safe repository-relative path`);
    }
  }
  return { ok: errors.length === 0, errors };
}

/**
 * Reject absolute or parent-traversing configuration paths on every platform.
 * @param {string} value candidate path
 * @returns {boolean} true when unsafe
 */
function pathLooksAbsoluteOrTraversing(value) {
  const normalized = value.replaceAll("\\", "/");
  return normalized.startsWith("/")
    || /^[A-Za-z]:\//u.test(normalized)
    || normalized.split("/").includes("..");
}

/**
 * Validate the approved human animation contract without touching the
 * filesystem. The caller supplies the manifest object and discovered frame
 * names so this function stays deterministic and easy to unit test.
 *
 * @param {unknown} manifest parsed animation manifest
 * @param {readonly string[]} frameNames names in the right-facing frame directory
 * @param {object} runtimeConfig validated M0 runtime configuration
 * @returns {{ok: boolean, errors: string[], frameCount: number, durationsMs: number[]}}
 */
export function validateHumanAnimationContract(manifest, frameNames, runtimeConfig) {
  const errors = [];
  const human = manifest?.human_module_sword_idle;
  const durationsMs = Array.isArray(human?.frame_durations_ms)
    ? [...human.frame_durations_ms]
    : [];
  const frameCount = Number(human?.logical_frame_count);

  const expectedFrameCount = Number(runtimeConfig?.timeline?.frameCount);
  const expectedDurationMs = Number(runtimeConfig?.timeline?.durationMs);
  const expectedFps = Number(runtimeConfig?.timeline?.nominalLogicalFps);
  const expectedCanvas = runtimeConfig?.display?.canvas;
  const expectedAnchor = runtimeConfig?.display?.anchor;

  if (!human || typeof human !== "object") {
    errors.push("manifest.human_module_sword_idle is missing");
  }
  if (manifest?.status !== runtimeConfig?.source?.requiredManifestStatus) {
    errors.push(`manifest.status must be ${runtimeConfig?.source?.requiredManifestStatus}`);
  }
  if (frameCount !== expectedFrameCount) {
    errors.push(`logical_frame_count must be ${expectedFrameCount} (received ${frameCount})`);
  }
  if (human?.logical_fps !== expectedFps) {
    errors.push(`logical_fps must be ${expectedFps} (received ${human?.logical_fps})`);
  }
  if (JSON.stringify(human?.canvas_size) !== JSON.stringify([expectedCanvas?.width, expectedCanvas?.height])) {
    errors.push("canvas_size must match runtime configuration");
  }
  if (JSON.stringify(human?.directional_anchors?.right) !== JSON.stringify([expectedAnchor?.x, expectedAnchor?.y])) {
    errors.push("directional_anchors.right must match runtime configuration");
  }
  if (durationsMs.length !== expectedFrameCount || durationsMs.some((duration) => !Number.isFinite(duration) || duration <= 0)) {
    errors.push(`frame_durations_ms must contain ${expectedFrameCount} positive finite durations`);
  } else if (totalDurationMs(durationsMs) !== expectedDurationMs) {
    errors.push(`frame_durations_ms must total ${expectedDurationMs} (received ${totalDurationMs(durationsMs)})`);
  }

  const expectedFrames = Array.from(
    { length: expectedFrameCount },
    (_, index) => `frame-${String(index).padStart(3, "0")}.png`,
  );
  const actual = new Set(frameNames ?? []);
  const missing = expectedFrames.filter((name) => !actual.has(name));
  const unexpected = [...actual].filter((name) => !expectedFrames.includes(name));
  if (missing.length > 0) {
    errors.push(`missing right-facing frames: ${missing.join(", ")}`);
  }
  if (unexpected.length > 0) {
    errors.push(`unexpected right-facing frame names: ${unexpected.join(", ")}`);
  }

  return {
    ok: errors.length === 0,
    errors,
    frameCount,
    durationsMs,
  };
}

/**
 * Build the renderer-safe animation payload after validating the contract.
 * @param {object} input animation source data
 * @param {unknown} input.manifest parsed approved manifest
 * @param {readonly string[]} input.frameUrls safe frame URLs in frame order
 * @param {object} input.runtimeConfig validated M0 runtime configuration
 * @returns {{canvasSize: {width: number, height: number}, anchor: {x: number, y: number}, scale: number, frameDurationsMs: number[], restDurationMs: number, frames: string[]}}
 */
export function buildAnimationPayload({ manifest, frameUrls, runtimeConfig }) {
  const frameNames = (frameUrls ?? []).map((url) => decodeURIComponent(url).split(/[\\/]/).pop());
  const report = validateHumanAnimationContract(manifest, frameNames, runtimeConfig);
  if (!report.ok) {
    throw new Error(`Approved taskbar-pet asset contract failed: ${report.errors.join("; ")}`);
  }
  return {
    canvasSize: { ...runtimeConfig.display.canvas },
    anchor: { ...runtimeConfig.display.anchor },
    scale: runtimeConfig.display.renderScale,
    frameDurationsMs: report.durationsMs,
    restDurationMs: runtimeConfig.timeline.restDurationMs,
    frames: [...frameUrls],
  };
}
