/**
 * Return the total duration of a frame timeline.
 * @param {readonly number[]} durationsMs positive frame durations
 * @returns {number} total duration in milliseconds
 */
export function totalDurationMs(durationsMs) {
  validateDurations(durationsMs);
  return durationsMs.reduce((total, duration) => total + duration, 0);
}

/**
 * Find the frame shown at an elapsed time in a looping timeline.
 *
 * At a boundary the next frame is selected. This keeps frame changes crisp
 * and makes the authored duration contract observable without interpolation.
 *
 * @param {number} elapsedMs elapsed time in milliseconds
 * @param {readonly number[]} durationsMs positive frame durations
 * @returns {number} zero-based frame index
 */
export function frameIndexAt(elapsedMs, durationsMs) {
  validateDurations(durationsMs);
  const boundaries = buildCumulativeBoundaries(durationsMs);
  return frameIndexAtBoundaries(elapsedMs, boundaries);
}

/**
 * Select a frame while respecting a clip's once, loop, or segmented policy.
 * Segmented clips play their entry once, repeat only the declared middle
 * range, and reserve the final range for the action's remaining time.
 *
 * @param {{durationsMs:number[], loopMode?:string, segments?:object}} clip clip descriptor
 * @param {number} elapsedMs elapsed time since this action became active
 * @param {number|null} [remainingMs=null] host-reported time until action exit
 * @returns {number} zero-based authored frame index
 */
export function frameIndexForClip(clip, elapsedMs, remainingMs = null) {
  if (!clip || typeof clip !== "object") throw new TypeError("clip is required");
  validateDurations(clip.durationsMs);
  if (!Number.isFinite(elapsedMs)) throw new TypeError("elapsedMs must be finite");
  const elapsed = Math.max(0, elapsedMs);
  if (clip.loopMode === "loop") return frameIndexAt(elapsed, clip.durationsMs);
  if (clip.loopMode !== "segmented-enter-loop-exit") {
    const total = totalDurationMs(clip.durationsMs);
    return frameIndexAt(Math.min(elapsed, Math.max(0, total - 0.0001)), clip.durationsMs);
  }

  const { enter, loop, exit } = clip.segments ?? {};
  const ranges = [enter, loop, exit];
  if (!ranges.every((range) => Number.isInteger(range?.start) && Number.isInteger(range?.end)
    && range.start >= 0 && range.end >= range.start && range.end < clip.durationsMs.length)) {
    throw new RangeError("segmented clip ranges are invalid");
  }
  const enterDurations = clip.durationsMs.slice(enter.start, enter.end + 1);
  const loopDurations = clip.durationsMs.slice(loop.start, loop.end + 1);
  const exitDurations = clip.durationsMs.slice(exit.start, exit.end + 1);
  const enterDuration = totalDurationMs(enterDurations);
  const exitDuration = totalDurationMs(exitDurations);
  if (elapsed < enterDuration) return enter.start + frameIndexAt(elapsed, enterDurations);
  if (Number.isFinite(remainingMs) && remainingMs <= exitDuration) {
    const exitElapsed = Math.max(0, exitDuration - Math.max(0, remainingMs));
    return exit.start + frameIndexAt(Math.min(exitElapsed, exitDuration - 0.0001), exitDurations);
  }
  return loop.start + frameIndexAt(elapsed - enterDuration, loopDurations);
}

/**
 * Select a frame from precomputed cumulative boundaries without allocating in
 * the renderer's animation loop.
 * @param {number} elapsedMs elapsed time in milliseconds
 * @param {readonly number[]} boundaries cumulative exclusive frame ends
 * @returns {number} zero-based frame index
 */
function frameIndexAtBoundaries(elapsedMs, boundaries) {
  const total = boundaries.at(-1);
  if (!Number.isFinite(elapsedMs)) {
    throw new TypeError("elapsedMs must be finite");
  }

  const wrapped = ((elapsedMs % total) + total) % total;
  let low = 0;
  let high = boundaries.length - 1;

  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (wrapped < boundaries[middle]) {
      high = middle - 1;
    } else {
      low = middle + 1;
    }
  }

  return Math.min(low, boundaries.length - 1);
}

/**
 * Return the delay until the next authored frame boundary.
 * @param {number} elapsedMs elapsed time in milliseconds
 * @param {readonly number[]} durationsMs positive frame durations
 * @returns {number} delay in milliseconds, never less than zero
 */
export function millisecondsUntilNextFrame(elapsedMs, durationsMs) {
  const total = totalDurationMs(durationsMs);
  if (!Number.isFinite(elapsedMs)) {
    throw new TypeError("elapsedMs must be finite");
  }
  const wrapped = ((elapsedMs % total) + total) % total;
  let boundary = 0;
  for (const duration of durationsMs) {
    boundary += duration;
    if (wrapped < boundary) {
      return Math.max(0, boundary - wrapped);
    }
  }
  return total;
}

/**
 * Small clock-driven timeline helper for the renderer.
 */
export class FrameTimeline {
  /**
   * @param {readonly number[]} durationsMs positive frame durations
   * @param {() => number} [clock] monotonic clock returning milliseconds
   */
  constructor(durationsMs, clock = () => performance.now()) {
    validateDurations(durationsMs);
    if (typeof clock !== "function") {
      throw new TypeError("clock must be a function");
    }
    this.durationsMs = Object.freeze([...durationsMs]);
    this.boundaries = Object.freeze(buildCumulativeBoundaries(this.durationsMs));
    this.clock = clock;
    this.startedAt = null;
  }

  /**
   * Start or restart the looping timeline.
   * @param {number} [nowMs] optional clock value used as the start
   * @returns {void}
   */
  start(nowMs = this.clock()) {
    if (!Number.isFinite(nowMs)) {
      throw new TypeError("nowMs must be finite");
    }
    this.startedAt = nowMs;
  }

  /**
   * Read the current authored frame.
   * @param {number} [nowMs] optional clock value
   * @returns {number} zero-based frame index
   */
  frameAt(nowMs = this.clock()) {
    if (this.startedAt === null) {
      this.start(nowMs);
    }
    return frameIndexAtBoundaries(nowMs - this.startedAt, this.boundaries);
  }

  /**
   * Read the delay until the current frame expires.
   * @param {number} [nowMs] optional clock value
   * @returns {number} delay in milliseconds
   */
  delayUntilNextFrame(nowMs = this.clock()) {
    if (this.startedAt === null) {
      this.start(nowMs);
    }
    const elapsedMs = nowMs - this.startedAt;
    const total = this.boundaries.at(-1);
    const wrapped = ((elapsedMs % total) + total) % total;
    const frame = frameIndexAtBoundaries(elapsedMs, this.boundaries);
    return Math.max(0, this.boundaries[frame] - wrapped);
  }
}

/**
 * Absolute-clock schedule that rests on frame 000, plays one complete authored
 * idle animation, then rests again. This avoids drift across long sessions.
 */
export class IdleSequenceTimeline {
  /**
   * @param {readonly number[]} durationsMs authored animation durations
   * @param {number} restDurationMs gap between complete animation plays
   * @param {() => number} [clock] monotonic clock returning milliseconds
   */
  constructor(durationsMs, restDurationMs, clock = () => performance.now()) {
    validateDurations(durationsMs);
    if (!Number.isFinite(restDurationMs) || restDurationMs < 0) {
      throw new RangeError("restDurationMs must be a non-negative finite number");
    }
    if (typeof clock !== "function") {
      throw new TypeError("clock must be a function");
    }
    this.boundaries = Object.freeze(buildCumulativeBoundaries(durationsMs));
    this.animationDurationMs = this.boundaries.at(-1);
    this.restDurationMs = restDurationMs;
    this.cycleDurationMs = restDurationMs + this.animationDurationMs;
    this.clock = clock;
    this.startedAt = null;
  }

  /**
   * Start the schedule in its resting state.
   * @param {number} [nowMs] optional clock value used as the start
   * @returns {void}
   */
  start(nowMs = this.clock()) {
    if (!Number.isFinite(nowMs)) {
      throw new TypeError("nowMs must be finite");
    }
    this.startedAt = nowMs;
  }

  /**
   * Select the resting frame or authored animation frame for the current time.
   * @param {number} [nowMs] optional clock value
   * @returns {number} zero-based frame index
   */
  frameAt(nowMs = this.clock()) {
    if (this.startedAt === null) {
      this.start(nowMs);
    }
    const elapsed = nowMs - this.startedAt;
    const phase = ((elapsed % this.cycleDurationMs) + this.cycleDurationMs) % this.cycleDurationMs;
    if (phase < this.restDurationMs) {
      return 0;
    }
    return frameIndexAtBoundaries(phase - this.restDurationMs, this.boundaries);
  }
}

/**
 * Validate the manifest-provided frame duration array.
 * @param {unknown} durationsMs candidate durations
 * @returns {void}
 */
export function validateDurations(durationsMs) {
  if (!Array.isArray(durationsMs) || durationsMs.length === 0) {
    throw new TypeError("durationsMs must be a non-empty array");
  }
  if (!durationsMs.every((duration) => Number.isFinite(duration) && duration > 0)) {
    throw new RangeError("durationsMs must contain positive finite numbers");
  }
}

/**
 * Build exclusive frame-end boundaries once for binary search.
 * @param {readonly number[]} durationsMs validated frame durations
 * @returns {number[]} cumulative exclusive boundaries
 */
function buildCumulativeBoundaries(durationsMs) {
  const boundaries = new Array(durationsMs.length);
  let cumulative = 0;
  for (let index = 0; index < durationsMs.length; index += 1) {
    cumulative += durationsMs[index];
    boundaries[index] = cumulative;
  }
  return boundaries;
}
