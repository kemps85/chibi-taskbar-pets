import { app, BrowserWindow, Menu, Tray, ipcMain, nativeImage, protocol, screen } from "electron";
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { BehaviorEngine } from "./behavior-engine.js";
import { buildCharacterRuntimePayload, resolveActionDurations, resolveManifestClipId } from "./m1-runtime.js";
import { createXorshift32 } from "./movement.js";
import { CHARACTER_LABELS, DEFAULT_CHARACTER, normalizeCharacter, resolveInitialCharacter, signatureClipId, SUPPORTED_CHARACTERS } from "./character-selection.js";
import { validateRuntimeConfig } from "./asset-contract.js";
import { calculateTaskbarPlacement, isSupportedBottomTaskbar } from "./placement.js";

const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(moduleDirectory, "../..");
const rendererPath = path.join(moduleDirectory, "renderer.html");
const preloadPath = path.join(moduleDirectory, "preload.cjs");
const runtimeConfigDevelopmentPath = path.join(repositoryRoot, "assets/data/taskbar_pet_runtime_v1.json");
const behaviorConfigDevelopmentPath = path.join(repositoryRoot, "assets/data/taskbar_pet_behavior_v1.json");
const rendererUrl = "pet-app://renderer/renderer.html";
const characterSelectionFileName = "taskbar-pet-character.json";

let petWindow = null;
let petWindowReady = false;
let tray = null;
let runtimeConfig = null;
let behaviorConfig = null;
let animationPayload = null;
let activeCharacter = DEFAULT_CHARACTER;
let activeFrameDirectories = new Map();
let activeClipPaths = new Map();
let behaviorEngine = null;
let latestSnapshot = null;
let behaviorTimer = null;
let shuttingDown = false;
let smokeTimeout = null;

const qaCharacterArgument = process.argv.find((argument) => argument.startsWith("--qa-character="));
const qaCharacter = qaCharacterArgument ? normalizeCharacter(qaCharacterArgument.split("=")[1]) : null;
const qaSeedArgument = process.argv.find((argument) => argument.startsWith("--qa-seed="));
const qaSeed = qaSeedArgument ? Number(qaSeedArgument.split("=")[1]) : null;
const qaExitArgument = process.argv.find((argument) => argument.startsWith("--qa-exit-after-ms="));
const qaExitAfterMs = qaExitArgument ? Number(qaExitArgument.split("=")[1]) : null;
const qaActionArgument = process.argv.find((argument) => argument.startsWith("--qa-action="));
const qaAction = qaActionArgument ? qaActionArgument.split("=")[1] : null;
const qaDirectionArgument = process.argv.find((argument) => argument.startsWith("--qa-direction="));
const qaDirection = qaDirectionArgument?.split("=")[1] === "left" ? "left" : "right";
const sessionRandom = createXorshift32(Number.isInteger(qaSeed) ? qaSeed : randomBytes(4).readUInt32LE(0));

protocol.registerSchemesAsPrivileged([
  { scheme: "pet-asset", privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
  { scheme: "pet-app", privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
]);

/**
 * Return a monotonic host timestamp for behavior and movement decisions.
 * @returns {number} elapsed milliseconds from the process monotonic clock
 */
function monotonicNow() {
  return Number(process.hrtime.bigint()) / 1000000;
}

/**
 * Read and validate the external M0 display/runtime configuration.
 * @returns {object} parsed runtime configuration
 */
function loadRuntimeConfig() {
  if (runtimeConfig) return runtimeConfig;
  const configPath = app.isPackaged
    ? path.join(process.resourcesPath, "pet-assets/config/taskbar_pet_runtime_v1.json")
    : runtimeConfigDevelopmentPath;
  runtimeConfig = JSON.parse(readFileSync(configPath, "utf8"));
  const report = validateRuntimeConfig(runtimeConfig);
  if (!report.ok) throw new Error("Runtime configuration rejected: " + report.errors.join("; "));
  return runtimeConfig;
}

/**
 * Read the data-driven M1 behavior configuration.
 * @returns {object} parsed behavior configuration
 */
function loadBehaviorConfig() {
  if (behaviorConfig) return behaviorConfig;
  const configPath = app.isPackaged
    ? path.join(process.resourcesPath, "pet-assets/config/taskbar_pet_behavior_v1.json")
    : behaviorConfigDevelopmentPath;
  behaviorConfig = JSON.parse(readFileSync(configPath, "utf8"));
  if (behaviorConfig.milestone !== "M1" || !behaviorConfig.characters) {
    throw new Error("M1 behavior configuration is missing its character contract");
  }
  return behaviorConfig;
}

/**
 * Resolve a relative path below an allowlisted root.
 * @param {string} root allowlisted absolute root
 * @param {string} relativePath configured relative path
 * @returns {string} contained absolute path
 */
function resolveContainedPath(root, relativePath) {
  const resolvedRoot = path.resolve(root);
  const candidate = path.resolve(resolvedRoot, relativePath);
  if (candidate !== resolvedRoot && !candidate.startsWith(resolvedRoot + path.sep)) {
    throw new Error("Configured path escapes allowlisted root: " + relativePath);
  }
  return candidate;
}

/**
 * Return the packaged equivalent of a source-relative stable clip-pack path.
 * @param {string} configuredPath path from the behavior config
 * @returns {string} absolute packaged path
 */
function resolvePackagedConfiguredPath(configuredPath) {
  const prefix = "assets/runtime/taskbar-pet/";
  if (!configuredPath.startsWith(prefix)) throw new Error("Stable clip-pack path must start with " + prefix);
  return resolveContainedPath(process.resourcesPath, "pet-assets/" + configuredPath.slice(prefix.length));
}

/**
 * Resolve a character manifest, preferring the stable runtime pack and using
 * generated manifests only as an explicit development fallback.
 * @param {string} character supported character id
 * @returns {{path: string, fallback: boolean}} manifest path and fallback flag
 */
function resolveCharacterManifest(character) {
  const characterConfig = loadBehaviorConfig().characters?.[character];
  if (!characterConfig) throw new Error("Unsupported M1 character: " + character);
  const configuredPath = app.isPackaged
    ? resolvePackagedConfiguredPath(characterConfig.clipPackManifest)
    : resolveContainedPath(repositoryRoot, characterConfig.clipPackManifest);
  if (existsSync(configuredPath)) return { path: configuredPath, fallback: false };
  if (app.isPackaged) throw new Error("Stable " + character + " clip pack is missing: " + configuredPath);
  const generatedName = character === "miyabi" ? "hoshimi-miyabi" : "firefly";
  const fallbackPath = resolveContainedPath(repositoryRoot,
    "assets/generated/pixel-chibi/production-v2/" + generatedName + "/behavior-pack-v1/manifest.json");
  if (!existsSync(fallbackPath)) throw new Error("Stable " + character + " clip pack and development fallback are missing");
  console.warn("Using development-only generated fallback for " + character + ": " + fallbackPath);
  return { path: fallbackPath, fallback: true };
}

/**
 * Resolve a manifest's frame directory without allowing path traversal.
 * @param {string} manifestPath absolute manifest path
 * @param {string} configuredPath manifest frame-directory value
 * @returns {string} existing frame directory path
 */
function resolveFramesDirectory(manifestPath, configuredPath) {
  if (typeof configuredPath !== "string" || configuredPath.length === 0) {
    throw new Error("Clip frames path is missing in " + manifestPath);
  }
  const candidates = [];
  if (app.isPackaged) {
    const prefix = "assets/runtime/taskbar-pet/";
    if (configuredPath.startsWith(prefix)) {
      candidates.push(resolveContainedPath(process.resourcesPath, "pet-assets/" + configuredPath.slice(prefix.length)));
    }
    candidates.push(resolveContainedPath(path.dirname(manifestPath), configuredPath));
  } else {
    const generatedPrefix = "assets/generated/pixel-chibi/production-v2/";
    const stablePrefix = "assets/runtime/taskbar-pet/";
    if (configuredPath.startsWith(generatedPrefix) || configuredPath.startsWith(stablePrefix)) {
      candidates.push(resolveContainedPath(repositoryRoot, configuredPath));
    } else if (!configuredPath.includes("/") || !configuredPath.startsWith("..")) {
      candidates.push(resolveContainedPath(path.dirname(manifestPath), configuredPath));
    } else {
      throw new Error("Clip frames path must remain inside its approved pack: " + configuredPath);
    }
  }
  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) throw new Error("Clip frames directory is missing: " + configuredPath);
  return found;
}

/**
 * Validate and register a right-authored frame directory.
 * @param {Map<string,string>} directoryMap URL-keyed allowlist being built
 * @param {string} key character/clip key
 * @param {string} directory absolute frame directory
 * @param {number} frameCount expected number of authored frames
 * @returns {void}
 */
function registerFrameDirectory(directoryMap, key, directory, frameCount) {
  const frameNames = readdirSync(directory).filter((name) => /^frame-\d{3}\.png$/u.test(name)).sort();
  const expected = Array.from({ length: frameCount }, (_, index) => "frame-" + String(index).padStart(3, "0") + ".png");
  if (frameNames.length !== expected.length || frameNames.some((name, index) => name !== expected[index])) {
    throw new Error("Frame directory contract failed for " + key + ": expected " + expected.length + " contiguous frames");
  }
  directoryMap.set(key, directory);
}

/**
 * Load the approved Firefly reference manifest used by module_sword when the
 * behavior manifest intentionally omits frame_count.
 * @returns {object} approved M0 reference manifest
 */
function loadReferenceManifest() {
  const config = loadRuntimeConfig();
  const manifestPath = app.isPackaged
    ? path.join(process.resourcesPath, "pet-assets/firefly/m0-human-right/firefly-idle-animation-manifest.json")
    : resolveContainedPath(repositoryRoot, config.source.manifestPath);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  if (manifest.status !== "PASS" || !manifest.human_module_sword_idle) {
    throw new Error("Approved Firefly module_sword reference manifest is invalid");
  }
  return manifest;
}

/**
 * Build renderer-safe clips and the corresponding main-process allowlist.
 * @param {string} character active character id
 * @returns {{payload: object, directories: Map<string,string>, clipPaths: Map<string,string>}} runtime assets
 */
function loadCharacterAssets(character) {
  const characterConfig = loadBehaviorConfig().characters[character];
  const manifestInfo = resolveCharacterManifest(character);
  const manifest = JSON.parse(readFileSync(manifestInfo.path, "utf8"));
  const requiredClips = characterConfig.requiredClips;
  const directories = new Map();
  const clipPaths = new Map();
  for (const requiredId of [...requiredClips, "eat"]) {
    const actualId = resolveManifestClipId(manifest.clips, requiredId);
    const clip = actualId ? manifest.clips[actualId] : null;
    if (!clip || clip.type === "approved_reference_clip") continue;
    const directory = resolveFramesDirectory(manifestInfo.path, clip.frames);
    registerFrameDirectory(directories, character + "/" + actualId, directory, Number(clip.frame_count));
    const outputId = requiredId === "signature" ? signatureClipId(character) : requiredId;
    clipPaths.set(outputId, directory);
  }
  const moduleReference = character === "firefly"
    && (manifest.clips.module_sword?.type === "approved_reference_clip"
      || manifest.clips.signature?.type === "approved_reference_clip");
  if (moduleReference) {
    const runtime = loadRuntimeConfig();
    const referenceDirectory = app.isPackaged
      ? resolveContainedPath(process.resourcesPath, "pet-assets/firefly/m0-human-right/frames")
      : resolveContainedPath(repositoryRoot, runtime.source.framesDirectory);
    const reference = loadReferenceManifest().human_module_sword_idle;
    registerFrameDirectory(directories, character + "/module_sword", referenceDirectory, Number(reference.logical_frame_count));
    clipPaths.set("module_sword", referenceDirectory);
  }
  const payload = buildCharacterRuntimePayload({
    character,
    manifest,
    referenceManifest: moduleReference ? loadReferenceManifest() : undefined,
    requiredClips,
    frameUrlFor: (clipId, frameIndex) => "pet-asset://" + character + "/" + clipId + "/frame-" + String(frameIndex).padStart(3, "0") + ".png",
    referenceFrameUrlFor: (frameIndex) => "pet-asset://" + character + "/module_sword/frame-" + String(frameIndex).padStart(3, "0") + ".png",
    strictManifest: !manifestInfo.fallback,
  });
  return { payload, directories, clipPaths };
}

/**
 * Create movement bounds that keep the full canvas inside the primary work
 * area for both right-authored and runtime-mirrored directions.
 * @param {object} display Electron display descriptor
 * @param {object} payload active renderer payload
 * @returns {{minX:number,maxX:number}} valid world anchor range
 */
function calculateMovementBounds(display, payload) {
  const edgeInset = Number(loadBehaviorConfig().locomotion?.edgeInsetDip ?? 0);
  const maximumDirectionalOffset = Math.max(payload.anchor.x, payload.canvasSize.width - payload.anchor.x);
  return {
    minX: display.workArea.x + maximumDirectionalOffset + Math.max(0, edgeInset),
    maxX: display.workArea.x + display.workArea.width - maximumDirectionalOffset - Math.max(0, edgeInset),
  };
}

/**
 * Adapt the character-specific config to the behavior engine's generic action
 * model while retaining tuning in the external M1 config.
 * @param {string} character active character
 * @param {object} display active display descriptor
 * @param {object} payload active renderer payload
 * @returns {object} engine options
 */
function makeBehaviorEngineOptions(character, display, payload) {
  const config = loadBehaviorConfig();
  const characterConfig = config.characters[character];
  const clipDuration = (clipId) => {
    const durations = payload.clips[clipId]?.durationsMs;
    return Array.isArray(durations) ? durations.reduce((sum, duration) => sum + duration, 0) : 0;
  };
  const phaseActions = [
    { id: "hungry_notice", clip: "hunger_cue", durationMs: config.needs.hunger.cueVisibleMs },
    { id: "sleep_cue", clip: "sleep_cue" },
    { id: "sleep_enter", clip: "sleep_enter" },
    { id: "sleep_loop", clip: "sleep_loop" },
    { id: "wake", clip: "wake" },
    { id: "eat", clip: "eat" },
  ].filter((phase) => payload.clips[phase.clip])
    .map((phase) => ({ id: phase.id, durationMs: phase.durationMs ?? clipDuration(phase.clip) }));
  const characterActions = resolveActionDurations(characterConfig.actions ?? [], payload.clips);
  const actions = [
    { id: "walk", baseWeight: 1, durationMs: 0 },
    { id: "pause", baseWeight: 1, loopDurationMs: config.locomotion.pauseDurationMs },
    ...phaseActions,
    ...characterActions,
  ];
  const movementBounds = calculateMovementBounds(display, payload);
  return {
    character,
    config: {
      ...config,
      movement: { ...config.locomotion, workArea: movementBounds,
        initialAnchorX: latestSnapshot?.anchorX ?? (movementBounds.minX + movementBounds.maxX) / 2 },
      ordinaryActions: ["walk", "pause", ...characterActions.map((action) => action.id)],
      characters: { [character]: { actions } },
    },
    rng: sessionRandom,
    clock: monotonicNow,
  };
}

/**
 * Switch active character after validating its complete asset contract.
 * @param {string} requestedCharacter character selected by QA or tray
 * @returns {object} initial behavior snapshot
 */
function selectCharacter(requestedCharacter) {
  const character = normalizeCharacter(requestedCharacter);
  const assets = loadCharacterAssets(character);
  if (qaAction) {
    const qaClipId = assets.payload.actionClips?.[qaAction]
      ?? (assets.payload.clips?.[qaAction] ? qaAction : null);
    if (!qaClipId || !assets.payload.clips?.[qaClipId]) {
      throw new Error("Unsupported QA action for " + character + ": " + qaAction);
    }
    // Visual-QA mode repeats even one-shot clips so a screen recorder can
    // capture every authored frame without racing application startup.
    assets.payload.clips[qaClipId] = {
      ...assets.payload.clips[qaClipId],
      loopPolicy: "loop",
      segments: undefined,
    };
  }
  const nextEngine = new BehaviorEngine(makeBehaviorEngineOptions(character, screen.getPrimaryDisplay(), assets.payload));
  activeCharacter = character;
  animationPayload = assets.payload;
  activeFrameDirectories = assets.directories;
  activeClipPaths = assets.clipPaths;
  behaviorEngine = nextEngine;
  latestSnapshot = applyQaOverrides(behaviorEngine.tick(monotonicNow()));
  persistSelectedCharacter(character);
  if (tray) {
    const idleDirectory = activeClipPaths.get("idle");
    if (idleDirectory) tray.setImage(nativeImage.createFromPath(path.join(idleDirectory, "frame-000.png")));
    tray.setToolTip(character[0].toUpperCase() + character.slice(1) + " Taskbar Pet");
  }
  updateTrayMenu();
  if (petWindow && !petWindow.isDestroyed()) {
    petWindow.webContents.send("taskbar-pet:runtime-config", animationPayload);
    petWindow.webContents.send("taskbar-pet:runtime-state", latestSnapshot);
    repositionPetWindow();
  }
  return latestSnapshot;
}

/**
 * Pin character/action/direction only when the explicit visual-QA CLI surface
 * is active. Production behavior never passes these arguments.
 * @param {object} snapshot ordinary engine snapshot
 * @returns {object} production snapshot or deterministic QA snapshot
 */
function applyQaOverrides(snapshot) {
  if (!qaAction || !animationPayload) return snapshot;
  const display = screen.getPrimaryDisplay();
  const bounds = calculateMovementBounds(display, animationPayload);
  return {
    ...snapshot,
    character: activeCharacter,
    action: qaAction,
    direction: qaDirection,
    anchorX: (bounds.minX + bounds.maxX) / 2,
    remainingMs: Number.POSITIVE_INFINITY,
  };
}

/**
 * Return the selected-character persistence file under Electron userData.
 * @returns {string} app-owned persistence path
 */
function selectedCharacterPath() {
  return path.join(app.getPath("userData"), characterSelectionFileName);
}

/**
 * Load the saved character id without allowing persisted data to escape the
 * supported enum or crash startup.
 * @returns {string} saved or default character id
 */
function readSelectedCharacter() {
  try {
    const saved = JSON.parse(readFileSync(selectedCharacterPath(), "utf8"));
    return resolveInitialCharacter({ savedCharacter: saved.character });
  } catch {
    return DEFAULT_CHARACTER;
  }
}

/**
 * Persist the selected character in an app-owned JSON file.
 * @param {string} character supported character id
 * @returns {void}
 */
function persistSelectedCharacter(character) {
  const filePath = selectedCharacterPath();
  mkdirSync(path.dirname(filePath), { recursive: true });
  writeFileSync(filePath, JSON.stringify({ character }, null, 2) + "\n", "utf8");
}

/**
 * Serve only allowlisted authored PNG frames to the sandboxed renderer.
 * @returns {void}
 */
function registerAssetProtocol() {
  protocol.handle("pet-asset", async (request) => {
    const url = new URL(request.url);
    const character = url.hostname;
    const parts = decodeURIComponent(url.pathname).replace(/^\//u, "").split("/");
    const clipId = parts.length === 2 ? parts[0] : "";
    const name = parts.length === 2 ? parts[1] : "";
    if (!SUPPORTED_CHARACTERS.has(character) || !/^frame-\d{3}\.png$/u.test(name)) return new Response("Not found", { status: 404 });
    const root = activeFrameDirectories.get(character + "/" + clipId);
    if (!root) return new Response("Not found", { status: 404 });
    const candidate = path.resolve(root, name);
    if (!candidate.startsWith(path.resolve(root) + path.sep)) return new Response("Forbidden", { status: 403 });
    try {
      return new Response(await readFile(candidate), {
        status: 200,
        headers: { "content-type": "image/png", "cache-control": "public, max-age=31536000, immutable" },
      });
    } catch {
      return new Response("Not found", { status: 404 });
    }
  });
  const rendererFiles = new Map([
    ["renderer.html", { path: rendererPath, type: "text/html; charset=utf-8" }],
    ["renderer.css", { path: path.join(moduleDirectory, "renderer.css"), type: "text/css; charset=utf-8" }],
    ["renderer.js", { path: path.join(moduleDirectory, "renderer.js"), type: "text/javascript; charset=utf-8" }],
    ["timeline.js", { path: path.join(moduleDirectory, "timeline.js"), type: "text/javascript; charset=utf-8" }],
  ]);
  protocol.handle("pet-app", async (request) => {
    const url = new URL(request.url);
    const name = decodeURIComponent(url.pathname).replace(/^\//u, "");
    const entry = url.hostname === "renderer" ? rendererFiles.get(name) : null;
    if (!entry) return new Response("Not found", { status: 404 });
    return new Response(await readFile(entry.path), {
      status: 200,
      headers: { "content-type": entry.type, "cache-control": "no-store" },
    });
  });
}

/**
 * Reposition the overlay against current primary-display metrics and behavior.
 * @returns {boolean|undefined} false when the supported layout gate hides it
 */
function repositionPetWindow() {
  if (!petWindow || petWindow.isDestroyed() || !animationPayload) return;
  const display = screen.getPrimaryDisplay();
  if (!isSupportedBottomTaskbar(display.bounds, display.workArea)) {
    console.error("M1 supports only a visible bottom taskbar on the primary display.");
    petWindow.hide();
    return false;
  }
  if (behaviorEngine) {
    behaviorEngine.movement.setWorkArea(calculateMovementBounds(display, animationPayload));
    latestSnapshot = applyQaOverrides(behaviorEngine.snapshot(monotonicNow()));
  }
  const snapshot = latestSnapshot ?? behaviorEngine?.snapshot(monotonicNow());
  const anchor = snapshot?.direction === "left"
    ? { x: animationPayload.canvasSize.width - animationPayload.anchor.x, y: animationPayload.anchor.y }
    : animationPayload.anchor;
  const bounds = calculateTaskbarPlacement({
    workArea: display.workArea, canvasSize: animationPayload.canvasSize, anchor,
    anchorX: snapshot?.anchorX, scale: loadRuntimeConfig().display.renderScale,
  });
  petWindow.setBounds(bounds, false);
  if (petWindowReady && !petWindow.isVisible()) petWindow.showInactive();
  return true;
}

/**
 * Send behavior state and move the host window on a small monotonic tick.
 * @returns {void}
 */
function tickBehavior() {
  if (!behaviorEngine || shuttingDown) return;
  latestSnapshot = applyQaOverrides(qaAction
    ? behaviorEngine.snapshot(monotonicNow())
    : behaviorEngine.tick(monotonicNow()));
  repositionPetWindow();
  if (petWindow && !petWindow.isDestroyed()) petWindow.webContents.send("taskbar-pet:runtime-state", latestSnapshot);
}

/**
 * Build the tray menu, including character selection and Feed command.
 * @returns {void}
 */
function updateTrayMenu() {
  if (!tray) return;
  tray.setContextMenu(Menu.buildFromTemplate([
    ...CHARACTER_LABELS.map(([id, label]) => ({
      label, type: "radio", checked: activeCharacter === id, click: () => switchCharacterFromTray(id),
    })),
    { type: "separator" },
    { label: "Feed", click: () => { latestSnapshot = behaviorEngine?.feed(monotonicNow()) ?? latestSnapshot; tickBehavior(); } },
    { type: "separator" },
    { label: "Quit", click: shutdown },
  ]));
}

/**
 * Change character from a user tray command, retaining the previous pet when
 * the selected pack fails closed.
 * @param {string} character requested character id
 * @returns {void}
 */
function switchCharacterFromTray(character) {
  try {
    selectCharacter(character);
  } catch (error) {
    console.error("Unable to switch to " + character + ":", error);
  }
}

/**
 * Create the transparent, click-through taskbar overlay window.
 * @returns {BrowserWindow} configured pet window
 */
function createPetWindow() {
  const config = animationPayload;
  const scale = loadRuntimeConfig().display.renderScale;
  petWindow = new BrowserWindow({
    width: config.canvasSize.width * scale, height: config.canvasSize.height * scale,
    frame: false, transparent: true, resizable: false, movable: false, focusable: false,
    skipTaskbar: true, alwaysOnTop: true, hasShadow: false, show: false, backgroundColor: "#00000000",
    webPreferences: { preload: preloadPath, contextIsolation: true, nodeIntegration: false, sandbox: true, devTools: false },
  });
  petWindow.setAlwaysOnTop(true, "pop-up-menu");
  petWindow.setIgnoreMouseEvents(true, { forward: true });
  petWindow.on("closed", () => { petWindow = null; petWindowReady = false; });
  petWindow.webContents.on("will-navigate", (event, targetUrl) => { if (targetUrl !== rendererUrl) event.preventDefault(); });
  petWindow.webContents.on("did-fail-load", (_event, code, description, validatedUrl) => console.error("Renderer failed to load " + validatedUrl + ": " + code + " " + description));
  petWindow.webContents.on("console-message", (event) => console.error("Renderer: " + event.message));
  petWindow.webContents.on("render-process-gone", (_event, details) => console.error("Renderer process exited: " + details.reason));
  petWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  petWindow.loadURL(rendererUrl);
  repositionPetWindow();
  petWindow.once("ready-to-show", () => {
    if (!petWindow || petWindow.isDestroyed()) return;
    petWindowReady = true;
    if (repositionPetWindow()) petWindow.showInactive();
  });
  return petWindow;
}

/**
 * Create the tray icon from the active idle frame and install its menu.
 * @returns {void}
 */
function createTray() {
  const idleDirectory = activeClipPaths.get("idle");
  if (!idleDirectory) throw new Error("Active " + activeCharacter + " payload has no idle frame directory");
  tray = new Tray(nativeImage.createFromPath(path.join(idleDirectory, "frame-000.png")));
  tray.setToolTip(activeCharacter[0].toUpperCase() + activeCharacter.slice(1) + " Taskbar Pet");
  updateTrayMenu();
}

/**
 * Remove listeners and close tray/window exactly once.
 * @returns {void}
 */
function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  if (behaviorTimer) { clearInterval(behaviorTimer); behaviorTimer = null; }
  screen.removeListener("display-added", repositionPetWindow);
  screen.removeListener("display-removed", repositionPetWindow);
  screen.removeListener("display-metrics-changed", repositionPetWindow);
  if (tray) { tray.destroy(); tray = null; }
  if (petWindow && !petWindow.isDestroyed()) { petWindow.destroy(); petWindow = null; }
  if (app.isReady()) app.quit();
}

/**
 * Restrict renderer IPC to the exact trusted app URL.
 * @param {object} event IPC event
 * @returns {boolean} whether the sender is trusted
 */
function isTrustedRenderer(event) {
  return event.senderFrame?.url === rendererUrl;
}

ipcMain.handle("taskbar-pet:get-animation-config", (event) => {
  if (!isTrustedRenderer(event)) throw new Error("Rejected IPC request from an untrusted renderer.");
  return animationPayload;
});
ipcMain.on("taskbar-pet:first-frame", (event) => {
  if (!isTrustedRenderer(event)) return;
  if (process.argv.includes("--smoke")) {
    if (smokeTimeout) { clearTimeout(smokeTimeout); smokeTimeout = null; }
    console.log("Taskbar pet smoke passed: first " + activeCharacter + " frame rendered.");
    shutdown();
    return;
  }
  if (Number.isFinite(qaExitAfterMs) && qaExitAfterMs > 0) setTimeout(shutdown, qaExitAfterMs);
});

// A 160x144 sprite canvas does not need the GPU process; software compositing keeps the pet's
// memory footprint small. The renderer only holds decoded frames, so a small V8 heap is enough.
app.disableHardwareAcceleration();
app.commandLine.appendSwitch("js-flags", "--max-old-space-size=96");

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on("window-all-closed", (event) => { if (!shuttingDown) event.preventDefault(); });
  app.on("second-instance", () => { if (petWindow && !petWindow.isDestroyed()) repositionPetWindow(); });
  app.whenReady().then(() => {
    loadRuntimeConfig();
    loadBehaviorConfig();
    selectCharacter(qaCharacter ?? readSelectedCharacter());
    registerAssetProtocol();
    createPetWindow();
    createTray();
    behaviorTimer = setInterval(tickBehavior, 50);
    screen.on("display-added", repositionPetWindow);
    screen.on("display-removed", repositionPetWindow);
    screen.on("display-metrics-changed", repositionPetWindow);
    app.on("before-quit", shutdown);
    if (process.argv.includes("--smoke")) {
      smokeTimeout = setTimeout(() => {
        console.error("Taskbar pet smoke failed: first frame did not render within 8 seconds.");
        app.exit(1);
      }, 8000);
    }
  }).catch((error) => { console.error(error); app.exit(1); });
}
