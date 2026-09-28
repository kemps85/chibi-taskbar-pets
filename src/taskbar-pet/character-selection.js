/**
 * Characters enabled by the M1 taskbar-pet behavior contract.
 * @type {ReadonlySet<string>}
 */
export const SUPPORTED_CHARACTERS = new Set([
  "miyabi", "firefly", "evanescia", "robin", "remielle-dan",
  "ye-shunguang", "ye-shunguang-white", "ye-shunguang-red", "ye-shunguang-red-white",
]);

/**
 * Tray labels, in menu order.
 * @type {ReadonlyArray<[string, string]>}
 */
export const CHARACTER_LABELS = Object.freeze([
  ["miyabi", "Miyabi"],
  ["firefly", "Firefly"],
  ["evanescia", "Evanescia"],
  ["robin", "Robin"],
  ["remielle-dan", "Remielle"],
  ["ye-shunguang", "Ye Shunguang"],
  ["ye-shunguang-white", "Ye Shunguang (white form)"],
  ["ye-shunguang-red", "Ye Shunguang (red outfit)"],
  ["ye-shunguang-red-white", "Ye Shunguang (red outfit, white form)"],
]);

/**
 * Runtime clip id of a character's signature action. Miyabi and Firefly keep their
 * historical ids; newer characters publish it as `signature`.
 * @param {string} character supported character id
 * @returns {string} signature clip id
 */
export function signatureClipId(character) {
  if (character === "miyabi") return "spirit_tail";
  if (character === "firefly") return "module_sword";
  return "signature";
}

/**
 * M1's first-launch character.
 * @type {string}
 */
export const DEFAULT_CHARACTER = "miyabi";

/**
 * Normalize a persisted or user-provided character selection.
 * @param {unknown} value candidate character id
 * @param {string} [fallback=DEFAULT_CHARACTER] fallback id
 * @returns {string} supported character id
 */
export function normalizeCharacter(value, fallback = DEFAULT_CHARACTER) {
  if (SUPPORTED_CHARACTERS.has(value)) {
    return value;
  }
  if (!SUPPORTED_CHARACTERS.has(fallback)) {
    return DEFAULT_CHARACTER;
  }
  return fallback;
}

/**
 * Resolve the first-launch or persisted selection without touching storage.
 * @param {{savedCharacter?: unknown, fallback?: string}} options selection inputs
 * @returns {string} selected character id
 */
export function resolveInitialCharacter({ savedCharacter, fallback = DEFAULT_CHARACTER } = {}) {
  return normalizeCharacter(savedCharacter, normalizeCharacter(fallback));
}

/**
 * Validate a character command before it reaches the main process.
 * @param {unknown} value requested character id
 * @returns {boolean} true when the id is supported
 */
export function isSupportedCharacter(value) {
  return SUPPORTED_CHARACTERS.has(value);
}
