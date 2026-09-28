import { frameIndexForClip, totalDurationMs } from "./timeline.js";

const petCanvas = document.querySelector("#pet");
const petContext = petCanvas.getContext("2d", { alpha: true });

let activeConfig = null;
let activeState = { character: "miyabi", action: "idle", direction: "right" };
let decodedClips = new Map();
let activeClipId = null;
let activeClipStartedAt = null;
let animationTimer = null;
let reportedFirstFrame = false;

/**
 * Fetch and decode every frame of one allowlisted clip before playback starts.
 * @param {object} clip renderer-safe clip descriptor
 * @returns {Promise<ImageBitmap[]>} decoded authored frames
 */
async function decodeClip(clip) {
  return Promise.all(clip.frames.map(async (url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Unable to load authored frame: " + url);
    return createImageBitmap(await response.blob(), {
      premultiplyAlpha: "premultiply",
      colorSpaceConversion: "none",
    });
  }));
}

/**
 * Decode the complete active character payload without accepting filesystem
 * paths from the page.
 * @param {object} config main-process clip payload
 * @returns {Promise<void>} resolves once all clips are ready
 */
async function loadConfig(config) {
  const clips = new Map();
  for (const [clipId, clip] of Object.entries(config.clips ?? {})) {
    if (!Array.isArray(clip.frames) || clip.frames.length !== clip.frameCount) {
      throw new Error("Clip " + clipId + " has an invalid frame contract");
    }
    if (totalDurationMs(clip.durationsMs) <= 0) {
      throw new Error("Clip " + clipId + " has invalid timing");
    }
    clips.set(clipId, { descriptor: clip, frames: await decodeClip(clip) });
  }
  activeConfig = config;
  const deviceScale = Math.max(1, Number(window.devicePixelRatio) || 1);
  petCanvas.width = Math.max(1, Math.round(config.canvasSize.width * deviceScale));
  petCanvas.height = Math.max(1, Math.round(config.canvasSize.height * deviceScale));
  petCanvas.style.width = config.canvasSize.width + "px";
  petCanvas.style.height = config.canvasSize.height + "px";
  // Miyabi's dense dark hair/coat palette develops visible pinholes and edge
  // crawl when a 1x backing store is nearest-neighbour scaled by Windows at
  // 125%. A DPI-matched backing store plus high-quality resampling keeps the
  // authored silhouette intact. Firefly retains the approved pixel mode.
  petContext.imageSmoothingEnabled = false;
  petContext.imageSmoothingQuality = "low";
  decodedClips = clips;
  activeClipId = null;
  activeClipStartedAt = null;
  reportedFirstFrame = false;
}

/**
 * Resolve an engine action to the clip id selected by the trusted payload.
 * @param {string} action behavior action id
 * @returns {string} clip id
 */
function clipForAction(action) {
  return activeConfig?.actionClips?.[action]
    ?? (decodedClips.has(action) ? action : "idle");
}

/**
 * Switch clip timelines only at action boundaries; no cross-fade is used.
 * @param {number} nowMs renderer monotonic timestamp
 * @returns {void}
 */
function syncClip(nowMs) {
  const nextClipId = clipForAction(activeState.action);
  if (nextClipId === activeClipId && activeClipStartedAt !== null) return;
  const entry = decodedClips.get(nextClipId) ?? decodedClips.get("idle");
  if (!entry) return;
  activeClipId = entry.descriptor.id;
  activeClipStartedAt = nowMs;
}

/**
 * Draw one authored frame and mirror it at runtime for left-facing movement.
 * The canvas remains fixed, so the main-process anchor does not move when the
 * renderer changes direction.
 * @param {ImageBitmap} bitmap decoded right-master frame
 * @param {"left"|"right"} direction current facing direction
 * @returns {void}
 */
function drawFrame(bitmap, direction) {
  petContext.clearRect(0, 0, petCanvas.width, petCanvas.height);
  petContext.save();
  if (direction === "left") {
    petContext.translate(petCanvas.width, 0);
    petContext.scale(-1, 1);
  }
  petContext.drawImage(bitmap, 0, 0, petCanvas.width, petCanvas.height);
  petContext.restore();
}

/**
 * Render the active state from exact frame durations.
 * @returns {void}
 */
function render() {
  const nowMs = performance.now();
  syncClip(nowMs);
  const entry = decodedClips.get(activeClipId);
  if (entry && activeClipStartedAt !== null) {
    const frameIndex = frameIndexForClip(
      entry.descriptor,
      nowMs - activeClipStartedAt,
      activeState.remainingMs,
    );
    drawFrame(entry.frames[frameIndex], activeState.direction);
    if (!reportedFirstFrame) {
      reportedFirstFrame = true;
      window.taskbarPet.reportFirstFrame();
    }
  }
  animationTimer = window.requestAnimationFrame(render);
}

/**
 * Accept a behavior snapshot from the main process.
 * @param {object} snapshot trusted behavior snapshot
 * @returns {void}
 */
function updateState(snapshot) {
  if (!snapshot || typeof snapshot !== "object") return;
  activeState = { ...activeState, ...snapshot };
}

/**
 * Start the secure renderer bridge and deterministic frame loop.
 * @returns {Promise<void>} resolves after payload and listeners are ready
 */
async function boot() {
  window.taskbarPet.onRuntimeConfig(async (config) => {
    await loadConfig(config);
    updateState({ character: config.character, action: "idle", direction: "right" });
  });
  window.taskbarPet.onRuntimeState(updateState);
  await loadConfig(await window.taskbarPet.getAnimationConfig());
  render();
}

boot().catch((error) => {
  if (animationTimer !== null) window.cancelAnimationFrame(animationTimer);
  console.error("Taskbar pet animation failed to start", error);
});
