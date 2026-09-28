import json,hashlib
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
manifest=json.loads((run/'00-baseline/baseline-manifest.json').read_text(encoding='utf-8'))
expected_renderer='71b179f07d3eb4852027e821b63f17ed91a512e8f316bb05c94a6677a87550b4'
changed=[]; errors=[]; checked=0
for e in manifest['paths']:
 p=Path(e['path']); rel=e['relativePath'].replace('\\','/')
 if not p.exists(): errors.append(f'MISSING {rel}'); continue
 h=hashlib.sha256(p.read_bytes()).hexdigest(); checked+=1
 if rel=='src/taskbar-pet/renderer.js':
  if h!=expected_renderer: errors.append(f'RENDERER_HASH {h} != {expected_renderer}')
  else: changed.append(rel)
 elif h!=e['sha256']:
  errors.append(f'CHANGED {rel}: {e["sha256"]} -> {h}')
firefly=[e for e in manifest['paths'] if e['relativePath'].replace('\\','/').startswith('assets/runtime/taskbar-pet/clip-packs/firefly/')]
firefly_bad=[]
for e in firefly:
 p=Path(e['path']); h=hashlib.sha256(p.read_bytes()).hexdigest()
 if h!=e['sha256']: firefly_bad.append(e['relativePath'])
out=run/'00-baseline/post-candidate-integrity-recheck.txt'
text=f'run={run.name}\nchecked={checked}/{len(manifest["paths"])}\nrenderer_expected_current={expected_renderer}\nrenderer_current={changed}\nfirefly_entries={len(firefly)}\nfirefly_changed={firefly_bad}\nstatus={"PASS" if not errors and not firefly_bad else "FAIL"}\n'
if errors: text+='errors:\n'+'\n'.join(errors)+'\n'
out.write_text(text,encoding='utf-8'); print(text)
