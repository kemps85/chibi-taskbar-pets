/**
 * Supported facing directions. Direction is render state only; the renderer
 * decides how to mirror the approved right-facing master art.
 * @type {Readonly<{LEFT: string, RIGHT: string}>}
 */
export const DIRECTIONS = Object.freeze({ LEFT: "left", RIGHT: "right" });

/**
 * Replacement for an injected zero xorshift seed.
 * @type {number}
 */
export const ZERO_SEED_REPLACEMENT = 1831565813;

/**
 * Create the serializable xorshift32 random stream used by behavior tests and
 * safe defaults. Hosts may inject its `nextFloat01` method into controllers.
 * @param {number} [seed=ZERO_SEED_REPLACEMENT] unsigned 32-bit seed
 * @returns {{nextUint32: () => number, nextFloat01: () => number, uniformInt: (minimum: number, maximum: number) => number, uniformFloat: (minimum: number, maximum: number) => number, state: () => {algorithm: string, stateUint32: number, drawCount: number}}} random stream
 */
export function createXorshift32(seed = ZERO_SEED_REPLACEMENT) {
  let state = (Number(seed) >>> 0) || ZERO_SEED_REPLACEMENT;
  let drawCount = 0;
  const nextUint32 = () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    state >>>= 0;
    drawCount = (drawCount + 1) >>> 0;
    return state;
  };
  return {
    nextUint32,
    nextFloat01: () => nextUint32() / 0x100000000,
    uniformInt: (minimum, maximum) => {
      if (!Number.isInteger(minimum) || !Number.isInteger(maximum) || maximum < minimum) {
        throw new RangeError("uniformInt bounds must be ordered integers");
      }
      return minimum + Math.floor((nextUint32() / 0x100000000) * (maximum - minimum + 1));
    },
    uniformFloat: (minimum, maximum) => {
      if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || maximum < minimum) {
        throw new RangeError("uniformFloat bounds must be ordered finite numbers");
      }
      return minimum + (nextUint32() / 0x100000000) * (maximum - minimum);
    },
    state: () => ({ algorithm: "xorshift32", stateUint32: state, drawCount }),
  };
}

/**
 * Create a function-shaped default random dependency without Math.random.
 * @returns {() => number} random float source
 */
function createDefaultRng() {
  const stream = createXorshift32();
  return () => stream.nextFloat01();
}

/**
 * Convert a delta into a facing direction while preserving the current
 * direction when the actor is stationary.
 * @param {number} deltaX target minus current horizontal anchor
 * @param {"left"|"right"} [fallback="right"] direction used for zero delta
 * @returns {"left"|"right"} derived direction
 */
export function directionForDelta(deltaX, fallback = DIRECTIONS.RIGHT) {
  if (!Number.isFinite(deltaX)) {
    throw new TypeError("deltaX must be finite");
  }
  if (deltaX < 0) {
    return DIRECTIONS.LEFT;
  }
  if (deltaX > 0) {
    return DIRECTIONS.RIGHT;
  }
  if (fallback !== DIRECTIONS.LEFT && fallback !== DIRECTIONS.RIGHT) {
    throw new RangeError("fallback must be left or right");
  }
  return fallback;
}

/**
 * Normalize the accepted work-area shapes to inclusive horizontal bounds.
 * @param {{minX?: number, maxX?: number, left?: number, right?: number, x?: number, width?: number}} workArea work-area configuration
 * @returns {{minX: number, maxX: number}} normalized horizontal bounds
 */
export function normalizeWorkArea(workArea) {
  if (!workArea || typeof workArea !== "object") {
    throw new TypeError("workArea must be an object");
  }
  let minX = workArea.minX ?? workArea.left ?? workArea.x;
  let maxX = workArea.maxX ?? workArea.right;
  if (maxX === undefined && Number.isFinite(workArea.x) && Number.isFinite(workArea.width)) {
    maxX = workArea.x + workArea.width;
  }
  if (!Number.isFinite(minX) || !Number.isFinite(maxX)) {
    throw new TypeError("workArea must define finite minX/maxX or x/width");
  }
  if (maxX < minX) {
    throw new RangeError("workArea.maxX must be greater than or equal to minX");
  }
  return { minX, maxX };
}

/**
 * Choose a random horizontal walking target within the work-area bounds.
 * Randomness is injected so behavior tests can remain deterministic.
 *
 * The RNG is sampled once for direction and once for distance. If the chosen
 * direction has no room, the other direction is used; the final distance is
 * clamped to the available room, so a walk can never cross a work-area edge.
 *
 * @param {object} options target-selection inputs
 * @param {number} options.anchorX current horizontal anchor
 * @param {object} options.workArea horizontal work-area bounds
 * @param {number} [options.minDistance=0] minimum requested distance
 * @param {number} [options.maxDistance=options.minDistance] maximum requested distance
 * @param {number} [options.edgeInset=0] inset from each horizontal edge
 * @param {() => number} [options.rng] injected random source in [0, 1)
 * @returns {number} bounded target anchor
 */
export function chooseWalkTarget({
  anchorX,
  workArea,
  minDistance = 0,
  maxDistance = minDistance,
  edgeInset = 0,
  rng = createDefaultRng(),
}) {
  rng = normalizeRandomSource(rng);
  const rawBounds = normalizeWorkArea(workArea);
  assertNonNegativeNumber(edgeInset, "edgeInset");
  const effectiveInset = Math.min(edgeInset, (rawBounds.maxX - rawBounds.minX) / 2);
  const bounds = {
    minX: rawBounds.minX + effectiveInset,
    maxX: rawBounds.maxX - effectiveInset,
  };
  assertFiniteNumber(anchorX, "anchorX");
  assertNonNegativeNumber(minDistance, "minDistance");
  assertNonNegativeNumber(maxDistance, "maxDistance");
  if (maxDistance < minDistance) {
    throw new RangeError("maxDistance must be greater than or equal to minDistance");
  }

  const current = clamp(anchorX, bounds.minX, bounds.maxX);
  const leftRoom = current - bounds.minX;
  const rightRoom = bounds.maxX - current;
  const requestedDirection = randomUnit(rng) < 0.5 ? DIRECTIONS.LEFT : DIRECTIONS.RIGHT;
  const requestedDistance = minDistance + randomUnit(rng) * (maxDistance - minDistance);

  let direction = requestedDirection;
  if (direction === DIRECTIONS.LEFT && leftRoom <= 0 && rightRoom > 0) {
    direction = DIRECTIONS.RIGHT;
  } else if (direction === DIRECTIONS.RIGHT && rightRoom <= 0 && leftRoom > 0) {
    direction = DIRECTIONS.LEFT;
  }

  const availableRoom = direction === DIRECTIONS.LEFT ? leftRoom : rightRoom;
  const distance = Math.min(requestedDistance, availableRoom);
  return clamp(
    current + (direction === DIRECTIONS.LEFT ? -distance : distance),
    bounds.minX,
    bounds.maxX,
  );
}

/**
 * Delta-time movement controller for a taskbar anchor.
 */
export class MovementController {
  /**
   * @param {object} options movement configuration
   * @param {number} options.anchorX initial horizontal anchor
   * @param {object} options.workArea horizontal work-area bounds
   * @param {number} [options.minDistance=0] minimum random target distance
   * @param {number} [options.maxDistance=options.minDistance] maximum random target distance
   * @param {number} [options.speedPxPerSecond=0] movement speed
   * @param {() => number} [options.rng] injected random source
   * @param {number} [options.edgeInset=0] inset from each horizontal edge
   * @param {"left"|"right"} [options.direction="right"] initial direction
   */
  constructor({
    anchorX = 0,
    workArea,
    minDistance = 0,
    maxDistance = minDistance,
    speedPxPerSecond = 0,
    rng = createDefaultRng(),
    direction = DIRECTIONS.RIGHT,
    edgeInset = 0,
  }) {
    assertNonNegativeNumber(edgeInset, "edgeInset");
    const rawBounds = normalizeWorkArea(workArea);
    const effectiveInset = Math.min(edgeInset, (rawBounds.maxX - rawBounds.minX) / 2);
    this.edgeInset = edgeInset;
    this.workArea = {
      minX: rawBounds.minX + effectiveInset,
      maxX: rawBounds.maxX - effectiveInset,
    };
    assertFiniteNumber(anchorX, "anchorX");
    assertNonNegativeNumber(minDistance, "minDistance");
    assertNonNegativeNumber(maxDistance, "maxDistance");
    assertNonNegativeNumber(speedPxPerSecond, "speedPxPerSecond");
    if (maxDistance < minDistance) {
      throw new RangeError("maxDistance must be greater than or equal to minDistance");
    }
    this.rng = normalizeRandomSource(rng);
    if (direction !== DIRECTIONS.LEFT && direction !== DIRECTIONS.RIGHT) {
      throw new RangeError("direction must be left or right");
    }

    this.minDistance = minDistance;
    this.maxDistance = maxDistance;
    this.speedPxPerSecond = speedPxPerSecond;
    this.anchorX = clamp(anchorX, this.workArea.minX, this.workArea.maxX);
    this.targetX = this.anchorX;
    this.direction = direction;
  }

  /**
   * Choose and begin walking toward a bounded random target.
   * @returns {number} selected target anchor
   */
  startWalk() {
    this.targetX = chooseWalkTarget({
      anchorX: this.anchorX,
      workArea: this.workArea,
      minDistance: this.minDistance,
      maxDistance: this.maxDistance,
      rng: this.rng,
    });
    this.direction = directionForDelta(this.targetX - this.anchorX, this.direction);
    return this.targetX;
  }

  /**
   * Move toward the target by a non-negative elapsed time.
   * @param {number} deltaMs elapsed monotonic time in milliseconds
   * @returns {{anchorX: number, targetX: number, direction: "left"|"right", walking: boolean}} movement snapshot
   */
  update(deltaMs) {
    assertNonNegativeNumber(deltaMs, "deltaMs");
    const deltaX = this.targetX - this.anchorX;
    const step = this.speedPxPerSecond * (deltaMs / 1000);
    if (Math.abs(deltaX) <= step || step === 0 && deltaX === 0) {
      this.anchorX = this.targetX;
    } else if (deltaX !== 0) {
      this.direction = directionForDelta(deltaX, this.direction);
      this.anchorX += Math.sign(deltaX) * step;
    }
    this.anchorX = clamp(this.anchorX, this.workArea.minX, this.workArea.maxX);
    if (this.anchorX === this.targetX) {
      this.direction = directionForDelta(0, this.direction);
    }
    return this.snapshot();
  }

  /**
   * Set an externally restored anchor and cancel the current walk.
   * @param {number} anchorX new horizontal anchor
   * @returns {void}
   */
  setAnchorX(anchorX) {
    assertFiniteNumber(anchorX, "anchorX");
    this.anchorX = clamp(anchorX, this.workArea.minX, this.workArea.maxX);
    this.targetX = this.anchorX;
  }

  /**
   * Update bounds while preserving a valid current anchor. A changed work area
   * cancels an in-flight walk so the next decision starts inside new bounds.
   * @param {object} workArea new horizontal work-area bounds
   * @returns {void}
   */
  setWorkArea(workArea) {
    const rawBounds = normalizeWorkArea(workArea);
    const effectiveInset = Math.min(this.edgeInset, (rawBounds.maxX - rawBounds.minX) / 2);
    const nextWorkArea = {
      minX: rawBounds.minX + effectiveInset,
      maxX: rawBounds.maxX - effectiveInset,
    };
    const changed = nextWorkArea.minX !== this.workArea.minX || nextWorkArea.maxX !== this.workArea.maxX;
    this.workArea = nextWorkArea;
    this.anchorX = clamp(this.anchorX, this.workArea.minX, this.workArea.maxX);
    this.targetX = changed
      ? this.anchorX
      : clamp(this.targetX, this.workArea.minX, this.workArea.maxX);
  }

  /**
   * Return the movement state consumed by the behavior snapshot.
   * @returns {{anchorX: number, targetX: number, direction: "left"|"right", walking: boolean}}
   */
  snapshot() {
    return {
      anchorX: this.anchorX,
      targetX: this.targetX,
      direction: this.direction,
      walking: this.anchorX !== this.targetX,
    };
  }
}

/**
 * Convert a source value into a bounded unit-random sample.
 * @param {() => number} rng random source
 * @returns {number} value in [0, 1)
 */
function randomUnit(rng) {
  const value = Number(rng());
  if (!Number.isFinite(value)) {
    throw new TypeError("rng must return a finite number");
  }
  return clamp(value, 0, 0.9999999999999999);
}

/**
 * Accept either a function RNG or the behavior random stream object.
 * @param {(() => number)|{nextFloat01: () => number}} rng random dependency
 * @returns {() => number} function-shaped random source
 */
function normalizeRandomSource(rng) {
  if (typeof rng === "function") {
    return rng;
  }
  if (rng && typeof rng.nextFloat01 === "function") {
    return () => rng.nextFloat01();
  }
  throw new TypeError("rng must be a function or expose nextFloat01");
}

/**
 * Clamp a number to an inclusive range.
 * @param {number} value value to clamp
 * @param {number} min lower bound
 * @param {number} max upper bound
 * @returns {number} bounded value
 */
function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Assert a finite number.
 * @param {unknown} value candidate number
 * @param {string} name field name
 * @returns {void}
 */
function assertFiniteNumber(value, name) {
  if (!Number.isFinite(value)) {
    throw new TypeError(`${name} must be finite`);
  }
}

/**
 * Assert a finite non-negative number.
 * @param {unknown} value candidate number
 * @param {string} name field name
 * @returns {void}
 */
function assertNonNegativeNumber(value, name) {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative finite number`);
  }
}
