# Imagegen Frame Protocol — Miyabi & Firefly

Mục tiêu: dùng GPT imagegen mà **không** để model tự ý cắt/đổi bộ phận giữa
các frame. Prompt chỉ là một nửa; nửa còn lại là script hậu kỳ
`scripts/imagegen_postprocess.py` khoá palette, căn lưới pixel, ghép vùng và QA.

## Luật vận hành

0. **Master luôn quay PHẢI thật** (mặt + thân hướng phải). Runtime lật gương
   khi đi sang trái. Mọi change list về chân phải nói "bước về phía nhân vật
   đang nhìn (bên phải ảnh)". Master Miyabi cũ thực ra quay trái — bản khoá
   hiện tại được lật từ `miyabi_source_facing_right.png`.

1. **Mỗi request = 1 frame.** Không xin sprite sheet — model vẽ lại từng ô độc lập.
2. **Luôn EDIT từ frame đã duyệt**, không generate từ chữ:
   - Frame đầu: `assets/references/imagegen-inputs/<char>/master_input_1024.png`
   - Frame sau: file `<frame>_next_input.png` do script xuất ra (bản đã khoá sạch,
     không phải ảnh raw của model — tránh lỗi tích luỹ).
3. **Chỉ xin key pose**, không xin frame trung gian.
4. **Mọi ảnh raw đều qua script.** FAIL → generate lại từ input đã duyệt,
   không "prompt vá" lên ảnh lỗi.
5. Frame nhỏ (chớp mắt, miệng, tay) **luôn dùng `--allow`** để ghép: ngoài vùng
   cho phép, pixel được lấy nguyên từ frame trước nên model không thể làm mất
   bộ phận nào.

## Script hậu kỳ

```bash
# 1 lần cho mỗi nhân vật (đã chạy): palette khoá, master khoá, input 1024, lưới toạ độ
python scripts/imagegen_postprocess.py init --character miyabi \
  --source assets/references/imagegen-inputs/miyabi_source_facing_right.png

# Mỗi frame imagegen trả về
python scripts/imagegen_postprocess.py process --character miyabi \
  --raw <ảnh raw từ imagegen> \
  --reference <frame đã duyệt trước đó, 160x144> \
  --out assets/generated/pixel-chibi/imagegen-v1/miyabi/idle/k2 \
  --allow 48,72,70,84
```

Đầu ra cạnh `--out`:

| File | Dùng để |
| --- | --- |
| `k2.png` | frame 160x144 đã khoá palette, dùng cho runtime |
| `k2_next_input.png` | Image đầu vào cho request imagegen kế tiếp |
| `k2_qa.png` | 4 ô: reference / imagegen / final / vùng trôi (đỏ mất, xanh thêm, vàng đổi màu) |
| `k2_qa.json` | kết quả từng check; exit code 1 khi FAIL |

Script tự xử lý: canvas trả về khác 1024 (imagegen hay trả 1254), lệch tỷ lệ,
lệch vị trí, viền hồng lẫn vào nét, pixel lạc. Các check chặn: nhân vật bị cắt
ở mép, bộ phận biến mất/vẽ lại ngoài vùng cho phép, mất cả nhóm màu (mắt, nơ,
kiếm…), diện tích thay đổi bất thường.

Toạ độ `--allow` là pixel trong canvas 160x144: `x0,y0,x1,y1` (bao gồm hai đầu).
Tra trên `assets/references/imagegen-inputs/<char>/master_grid.png`.
Key pose đổi cả dáng người (ngồi, nằm) dùng `--allow all`: không ghép, chỉ QA
cắt mép / mất nhóm màu.

### Vùng `--allow` đo sẵn

| Vùng | Miyabi | Firefly |
| --- | --- | --- |
| Mắt | `52,72,78,84` | `60,46,86,60` |
| Miệng | `58,82,72,90` | `66,58,78,64` |
| Chân (bước đi) | `38,123,96,143` | `54,93,96,143` (sát mép váy, tránh sót đùi master) |
| Tay cầm vũ khí + vũ khí | `80,88,106,128` | `20,85,58,143` |
| Tay còn lại | `40,106,58,124` | `86,62,106,88` |

## Prompt nền (dán nguyên văn, chỉ thay phần `<...>`)

```text
TASK: Pixel-art sprite EDIT. Produce exactly ONE animation frame.

INPUTS
- The input image is BOTH the LOCKED CHARACTER MASTER and the PREVIOUS APPROVED FRAME.
  It is the only source of truth for design, proportions, colors and pixel style.
  Start from this image and modify it.

CANVAS (hard rules)
- Output exactly 1024 x 1024 px. Flat solid background #FF00FF exactly like the input.
  No floor, no shadow, no gradient, no vignette, no border, no text, no watermark.
- The art is 160x144 pixel art shown at 6x: every art pixel is a crisp 6x6 block.
  No anti-aliasing, no blur, no soft edges, no painterly shading, no new colors.
  Use only colors that already appear in the input.
- Same camera, same 3/4 view, character faces RIGHT, same scale and same position
  on the canvas as the input. Head size, body height and limb thickness must match exactly.
- Feet stay on the same baseline as the input. Do not move the character.
- The WHOLE character must stay inside the canvas. Nothing may be cropped.

IDENTITY INVENTORY (every item must be present, same shape, same color, same side
of the body as in the input - do not remove, merge, shorten, or add any)
<paste the character inventory block>

CHANGE LIST (change ONLY these; everything else stays pixel-identical to the input)
<1-3 short bullet points describing the pose delta for this frame>

FORBIDDEN
- Redrawing or "cleaning up" parts that are not in the change list.
- Changing hairstyle length/volume, ear shape, face, outfit, weapon design,
  or which hand holds which item.
- Adding effects, motion lines, sparkles, letters, props, a second weapon,
  or a second character - unless the change list names them.
- Cropping ears, hair tips, weapon tip or feet.

OUTPUT: one 1024x1024 image only.
```

## Inventory — Hoshimi Miyabi

```text
- FACING: 3/4 view, face and body turned toward the RIGHT side of the image; her long back hair
  flows behind her toward the LEFT side of the image.
- Two tall dark fox ears with light-brown inner ear, pointing up; highest points of the silhouette.
- Black hair: blunt straight bangs, a thin braid on the side of the head,
  very long straight back hair reaching below the knees behind her back.
- Small calm RED eyes, pale face, small neutral mouth.
- White shirt collar with a RED ribbon tie at the neck.
- Muted TEAL cape over the shoulders with white emblem marks, draped asymmetrically,
  with a thin GOLD cord across the chest.
- Black top and black PLEATED skirt to above the knees; small gold tassel at the waist.
- Dark tights, dark brown/black boots.
- Dark mechanical sheathed katana with ornate hardware held at her viewer-right side (in front of
  her, the side she faces), angled down-right; it stays SHEATHED.
- Viewer-left hand small in a dark glove at the side of the skirt.
```

## Inventory — Firefly

```text
- FACING: near-front 3/4 view, turned slightly toward the RIGHT side of the image.
- Long wavy WHITE hair to mid-thigh, ends fading to pale TEAL, full volume on both sides.
- Black headband; small teal-green butterfly/leaf hair ornament on the viewer-right side.
- Large lilac-blue eyes, pale face, small gentle mouth.
- White long-sleeve shirt, dark grey sailor collar, TEAL-GREEN bow at the chest.
- Grey plaid PLEATED skirt.
- White thigh-high socks, black shoes.
- Slim long sword with cyan-grey blade and dark cross-guard, held in her viewer-left
  hand, blade pointing diagonally down-left to the ground.
- Small dark device with green glow held up in her viewer-right hand at chest height.
```

## Change list mẫu theo clip (key pose only)

Mỗi key pose là 1 request riêng; input là `_next_input.png` của key pose liền trước.

| Clip | Key | Change list | `--allow` |
| --- | --- | --- | --- |
| idle | K2 | `Eyes closed in a blink: each eye becomes a short 1-art-pixel dark curved line. Nothing else changes.` | Mắt |
| walk | WK1 | `Right leg steps forward (heel down in front), left leg behind on its toes. Skirt hem tilts 1 art-pixel back. Upper body and head unchanged.` | Chân |
| walk | WK2 | `Passing pose: both legs under the body, right leg straight, left knee slightly bent lifting the foot 2 art-pixels.` | Chân |
| walk | WK3 | `Left leg forward, right leg behind on toes (mirror of WK1 for the legs only).` | Chân |
| walk | WK2_other | **Không dùng imagegen** — imagegen không phân biệt chân trái/phải (WK3≈WK1, WK4≈WK2). Tạo bằng `scripts/pixel_leg_swap.py` từ WK2. | — |
| sleep | SK1 | `She sits down on the ground with knees bent to the side, upper body upright, eyes half-closed. The weapon lies on the ground beside her, fully visible. Feet/skirt touch the baseline.` | `all` |
| sleep | SK2 | `From SK1: eyes closed, head tilted down 2 art-pixels, shoulders slightly lowered.` | `all` (tham chiếu SK1) |
| wake | WAK1 | `From SK1: eyes open, ears/hair lifted, halfway standing up with one hand on the knee.` | `all` |
| hunger | HK1 | `One hand lightly touches the stomach. Expression mildly wistful (eyebrows raised, small open mouth).` | Tay còn lại + Miệng |
| eat | EK1 | `Holds a small rice ball in the free hand near the mouth. Mouth open small.` | Tay còn lại + Miệng |
| eat | EK2 | `Same as EK1 but mouth closed chewing, eyes softly closed in a happy curve.` | Mắt + Miệng |

`--allow` lặp được: `--allow 70,106,90,124 --allow 52,82,66,90`.

## Duyệt từng frame

- [ ] Script PASS.
- [ ] Nhìn `_qa.png` ô "final": đúng thay đổi yêu cầu, không có gì khác lạ.
- [ ] Vùng đỏ/vàng lớn trong ô "drift" nằm trong khung xanh (vùng cho phép).

## Dựng clip từ key pose

`scripts/build_pet_clip.py <char>/clips.json` dựng mọi clip từ key pose đã duyệt:

- Mỗi frame chọn 1 key pose + thời lượng (`ms`); pixel luôn lấy từ key pose, không vẽ mới.
- `bob` (-1 lên / +1 xuống): nhún/thở phần trên `pivot_y`; chân giữ nguyên.
- `trail_bob`, `trail_dx`: tóc/vạt áo phía sau trễ nhịp và hất về sau, tăng dần từ chỗ gắn ra ngọn.
- `rig.carried`: vùng vật cầm tay (kiếm Firefly) nhún cứng cùng thân, không gãy khúc.
- `fx`: hiệu ứng vẽ bằng code, palette cố định (`crescent` — vệt chém trăng khuyết Miyabi; `glint` — tia sáng dọc kiếm + đốm sáng Firefly). Hiệu ứng tự dịch theo `bob`.

Đầu ra: `<char>/clips-out/<clip>/frame-NNN.png`, `manifest.json` (số frame, timing, loop policy), `<clip>.mp4` preview (phải: bản lật gương khi đi sang trái).

Pose đổi toàn thân (ngồi, chiêu thức): imagegen hay giữ cỡ nhân vật nhưng vẽ lưới pixel mịn hơn; script lấy mẫu theo tỷ lệ đầu vào để nhân vật không đổi cỡ (cảnh báo `pixel_grid_preserved`). Không dùng `--allow` vùng khi một vật di chuyển qua ranh giới vùng (vd. kiếm từ dưới lên trên) — sẽ bị nhân đôi; dùng `all` hoặc tránh pose đó.

### Walk: chân luân phiên

Chu kỳ: `wk1` (bước) → `wk2_other` (nhấc chân trái) → `wk3` (bước) → `wk2` (nhấc chân phải).
Hai pose bước gần như giống nhau là bình thường với chibi 3/4; pose nhấc chân quyết định chân nào đang đi.

```bash
python scripts/pixel_leg_swap.py firefly/walk/wk2.png firefly/walk/wk2_other.png --region 54,97,96,143 --separate-y 114
python scripts/pixel_leg_swap.py miyabi/walk/wk2.png miyabi/walk/wk2_other.png --region 38,127,96,143 --separate-y 132 --lifted-behind
```

Vệt chém `crescent` phải quét cùng chiều với mũi kiếm và kết thúc ở mũi kiếm (Miyabi: `cx=96,cy=83,r=56,a0=70,a1=0`).
Không nối hai key pose có vật cầm tay khác vị trí (vd. vỏ kiếm đổi bên) — giữ pose trước đó.

### Walk hiện hành: chân vẽ theo IK

Walk không còn dùng key pose imagegen. `python scripts/build_painted_walk.py` vẽ chân theo IK 2 khớp (màu lấy từ master, giày giữ nguyên từ master), chân chạm đất lùi 4.8 px/frame để đứng yên khi runtime chạy 48 px/s, hai chân bắt chéo ở nhịp B. Chép `tmp/gait/painted-legs/<char>/frame-*.png` vào `clips-out/walk/`.

### Mặt đất và rig theo clip

- Firefly đứng: chân chạm y=130 (mũi kiếm xuống tới 143). Pose ngồi đã được dời lên cho khớp.
- `clips.json` cho phép clip ghi đè rig (`"rig": {...}`), ví dụ `sleep_loop` bỏ `carried` và hạ `pivot_y` xuống eo.
