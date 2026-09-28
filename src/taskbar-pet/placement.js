/**
 * The approved logical human animation canvas size.
 * @type {Readonly<{width: number, height: number}>}
 */
export const HUMAN_CANVAS_SIZE = Object.freeze({ width: 160, height: 144 });

/**
 * The approved right-facing human baseline anchor in logical pixels.
 * @type {Readonly<{x: number, y: number}>}
 */
export const HUMAN_RIGHT_ANCHOR = Object.freeze({ x: 64, y: 120 });

/**
 * The runtime scale for the pixel-art taskbar overlay.
 * @type {number}
 */
export const PIXEL_SCALE = 1;

/**
 * Calculate the window bounds for a pet whose authored anchor is at a requested
 * work-area coordinate. When no anchor position is supplied, the anchor is
 * centred on the primary display for the initial placement. The work area
 * excludes the Windows taskbar,
 * so the approved baseline anchor lands exactly on the taskbar's top edge.
 *
 * The transparent overscan below the baseline remains inside the window. It
 * lets the animation use its authored 160x144 canvas without cropping while
 * the visible feet stay at the taskbar edge.
 *
 * @param {object} options placement inputs
 * @param {{x: number, y: number, width: number, height: number}} options.workArea primary display work area in Electron DIP coordinates
 * @param {{width: number, height: number}} [options.canvasSize] logical animation canvas size
 * @param {{x: number, y: number}} [options.anchor] logical baseline anchor
 * @param {number} [options.anchorX] world-space x coordinate for the authored anchor
 * @param {number} [options.scale] logical-to-physical pixel scale
 * @returns {{x: number, y: number, width: number, height: number}} window bounds in DIP coordinates
 */
export function calculateTaskbarPlacement({
  workArea,
  canvasSize = HUMAN_CANVAS_SIZE,
  anchor = HUMAN_RIGHT_ANCHOR,
  anchorX,
  scale = PIXEL_SCALE,
}) {
  assertFiniteRect(workArea, "workArea");
  assertFiniteSize(canvasSize, "canvasSize");
  assertFinitePoint(anchor, "anchor");
  if (!Number.isFinite(scale) || scale <= 0) {
    throw new RangeError("scale must be a positive finite number");
  }

  const width = Math.round(canvasSize.width * scale);
  const height = Math.round(canvasSize.height * scale);

  const anchorWorldX = Number.isFinite(anchorX) ? anchorX : workArea.x + workArea.width / 2;
  const unclampedX = Math.round(anchorWorldX - anchor.x * scale);
  const maximumX = workArea.x + Math.max(0, workArea.width - width);
  const x = Math.min(maximumX, Math.max(workArea.x, unclampedX));
  const y = Math.round(workArea.y + workArea.height - anchor.y * scale);

  return { x, y, width, height };
}

/**
 * Confirm that the primary display has the bottom, non-auto-hidden taskbar
 * layout supported by M0.
 *
 * @param {{x: number, y: number, width: number, height: number}} bounds full display bounds
 * @param {{x: number, y: number, width: number, height: number}} workArea taskbar-excluded work area
 * @returns {boolean} true only for a bottom taskbar that reduces work-area height
 */
export function isSupportedBottomTaskbar(bounds, workArea) {
  assertFiniteRect(bounds, "bounds");
  assertFiniteRect(workArea, "workArea");
  return workArea.x === bounds.x
    && workArea.y === bounds.y
    && workArea.width === bounds.width
    && workArea.height > 0
    && workArea.height < bounds.height;
}

/**
 * Validate a physical display rectangle.
 * @param {unknown} value candidate rectangle
 * @param {string} name field name for the error
 * @returns {void}
 */
function assertFiniteRect(value, name) {
  if (!value || typeof value !== "object") {
    throw new TypeError(`${name} must be an object`);
  }
  for (const field of ["x", "y", "width", "height"]) {
    if (!Number.isFinite(value[field])) {
      throw new TypeError(`${name}.${field} must be finite`);
    }
  }
  if (value.width < 0 || value.height < 0) {
    throw new RangeError(`${name}.width and ${name}.height must be non-negative`);
  }
}

/**
 * Validate a logical size.
 * @param {unknown} value candidate size
 * @param {string} name field name for the error
 * @returns {void}
 */
function assertFiniteSize(value, name) {
  if (!value || typeof value !== "object") {
    throw new TypeError(`${name} must be an object`);
  }
  for (const field of ["width", "height"]) {
    if (!Number.isFinite(value[field]) || value[field] <= 0) {
      throw new RangeError(`${name}.${field} must be a positive finite number`);
    }
  }
}

/**
 * Validate a logical point.
 * @param {unknown} value candidate point
 * @param {string} name field name for the error
 * @returns {void}
 */
function assertFinitePoint(value, name) {
  if (!value || typeof value !== "object") {
    throw new TypeError(`${name} must be an object`);
  }
  for (const field of ["x", "y"]) {
    if (!Number.isFinite(value[field])) {
      throw new TypeError(`${name}.${field} must be finite`);
    }
  }
}
