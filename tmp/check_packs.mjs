import { readFileSync } from "node:fs";
import { validateBehaviorPackManifest, buildCharacterRuntimePayload } from "../src/taskbar-pet/m1-runtime.js";
const cfg = JSON.parse(readFileSync("assets/data/taskbar_pet_behavior_v1.json", "utf8"));
for (const [c, cc] of Object.entries(cfg.characters)) {
  const m = JSON.parse(readFileSync(cc.clipPackManifest, "utf8"));
  const r = validateBehaviorPackManifest(m, c, cc.requiredClips, { strictStable: true });
  let anchor = "-";
  if (r.ok) anchor = JSON.stringify(buildCharacterRuntimePayload({ character: c, manifest: m, requiredClips: cc.requiredClips, strictManifest: true, frameUrlFor: () => "x" }).anchor);
  console.log(c.padEnd(24), r.ok ? "OK" : "FAIL " + r.errors.join("; "), anchor);
}
