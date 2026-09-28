"""Firefly signature v3: henshin keeps the arm pose (h1 -> a1h), crossed-swords guard, back-and-forth flight,
land first, then the swords dissolve on the ground."""
import json, math
P = 'assets/generated/pixel-chibi/imagegen-v1/firefly/clips.json'
old = json.load(open('tmp/firefly_clips_v2_backup.json', encoding='utf-8'))['clips']['signature']['frames']
S = 'signature/'
F = lambda pose, ms, **k: {'pose': pose, 'ms': ms, **k}
HILTS2 = [[44, 91], [100, 89]]
thr = lambda seed, n=8: [{'type': 'thrust', 'x': 61, 'y': 125, 'length': n, 'seed': seed},
                         {'type': 'thrust', 'x': 71, 'y': 123, 'length': n, 'seed': seed}]
fr = []
fr += old[0:3]                                                     # idle -> henshin pose, module glows
for f in old[3:22]:                                                # flame climbs, armor keeps the held-out arm
    fr.append({**f, 'wipe_to': S + 'a1h.png'})
fr += [F(S + 'a1h.png', 450), F(S + 'a1h.png', 150, fx=[{'type': 'poof', 'x': 104, 'y': 60, 'progress': 0.3}])]
# arms cross over the chest, green flame gathers at the fists, then a decisive fling to both sides summons two swords
fr += [F(S + 'a1xe.png', 500), F(S + 'a1xe.png', 300, bob=1)]
fr += [F(S + 'a1xe.png', 120, bob=1, fx=[{'type': 'poof', 'x': 70, 'y': 72, 'progress': p}]) for p in (0.1, 0.25, 0.4)]
fr += [F(S + 'a1xe.png', 250, bob=1),
       F(S + 'a2_hover.png', 70, fx=[{'type': 'poof', 'x': 44, 'y': 91, 'progress': 0.1}, {'type': 'poof', 'x': 100, 'y': 89, 'progress': 0.1}]),
       F(S + 'a2_hover.png', 90, fx=[{'type': 'poof', 'x': 44, 'y': 91, 'progress': 0.45}, {'type': 'poof', 'x': 100, 'y': 89, 'progress': 0.45}]),
       F(S + 'a2_hover.png', 110, fx=[{'type': 'poof', 'x': 44, 'y': 91, 'progress': 0.8}, {'type': 'poof', 'x': 100, 'y': 89, 'progress': 0.8}]),
       F(S + 'a2_hover.png', 900)]
# take-off
for k, l in enumerate((1, 2, 3, 4, 6, 7, 8, 9, 10, 11)):
    fr.append(F(S + 'a2_hover.png', 200, lift=-l, fx=thr(k, 6)))
# back-and-forth flight: two slow passes across the canvas with a gentle bob
N = 40
for k in range(N):
    t = k / N
    sx = int(round(14 * math.sin(2 * math.pi * 2 * t)))            # +-14 px, two round trips
    fr.append(F(S + 'a2_hover.png', 200, lift=-11 - (k // 2) % 2, shift_x=sx, fx=thr(20 + k)))
# descend and land still holding both swords
for k, l in enumerate((10, 9, 8, 7, 6, 4, 2, 1)):
    fr.append(F(S + 'a2_hover.png', 200, lift=-l, fx=thr(90 + k, 6)))
fr += [F(S + 'a2_hover.png', 120, bob=1, fx=[{'type': 'poof', 'x': 56, 'y': 128, 'progress': 0.3}, {'type': 'poof', 'x': 76, 'y': 128, 'progress': 0.3}]),
       F(S + 'a2_hover.png', 150, fx=[{'type': 'poof', 'x': 56, 'y': 128, 'progress': 0.7}, {'type': 'poof', 'x': 76, 'y': 128, 'progress': 0.7}]),
       F(S + 'a2_hover.png', 800)]
# on the ground the blades fade from tip to hilt
for k in range(1, 17):
    fr.append(F(S + 'a2_hover.png', 150, dissolve={'bare': S + 'a2_bare.png', 'hilts': HILTS2, 'progress': k / 16}))
fr += [F(S + 'a2_bare.png', 400), F(S + 'a2_landed.png', 300)]
fr += old[107:]                                                    # vortex strips the armor, module summons the sword
json_all = json.load(open(P, encoding='utf-8'))
json_all['clips']['signature']['frames'] = fr
open(P, 'w', encoding='utf-8').write(json.dumps(json_all, indent=2, ensure_ascii=False) + '\n')
print(len(fr), 'frames', sum(f['ms'] for f in fr), 'ms')
