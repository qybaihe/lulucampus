# Lulu's Fridge · Lulu Motion System V2

## 1. Product decision

Lulu should not be decorative artwork pasted onto existing pages. Lulu is the visible body of Hermes and the emotional presentation layer of the kitchen agent.

The user should understand the current system state by looking at Lulu before reading text:

- calm breathing = ready;
- leaning in = listening;
- looking upward = reasoning;
- waving or speaking = replying;
- magnifier at the fridge = scanning;
- clipboard = reviewing trusted inventory;
- recipe card and chef hat = planning a meal;
- pan, spatula or timer = guiding cooking;
- concerned expression = recovery or an error;
- celebration = a confirmed or completed result.

This gives Lulu three simultaneous roles:

1. **Hermes avatar** on the home conversation screen;
2. **task narrator** on inventory, recipe, shopping, cooking and device screens;
3. **system status indicator** for long-running work, confirmations, success and recovery.

## 2. What the Codex Pets reference actually does

The referenced Capybara Lulu package uses:

- one `pet.json` metadata file;
- one transparent `spritesheet.webp`;
- a fixed atlas of 1536×1872 pixels;
- 8 columns × 9 rows;
- a fixed 192×208 cell;
- implicit row semantics: idle, run right, run left, wave, jump, fail, wait, work and review;
- different frame counts per row;
- sprite cropping by atlas coordinates and periodic frame replacement.

The useful idea is **one renderer + one manifest + deterministic named states**. The exact fixed-row format should not be copied because Lulu's Fridge needs page-specific kitchen states, variable frame timing, a stable baseline, reduced-motion behavior and future versioning.

## 3. Our improved asset model

### 3.1 Generation unit

Each ImageGen request produces a 2×2 sheet.

- A **style sheet** may contain four different poses for visual approval.
- A **production animation sheet** must contain four sequential frames of one clip.
- Do not mix unrelated semantic states in one production animation clip.
- Every sheet uses the same camera, body scale, ground baseline and flat magenta key background.

The pipeline is:

1. generate a 2×2 magenta-key source sheet;
2. remove the key color to alpha;
3. split the four cells;
4. register the orange-muzzle anchor and foot baseline with `Tools/register_lulu_frames.py`;
5. rebuild a normalized transparent atlas;
6. declare frame order and per-frame duration in JSON;
7. render a contact sheet and animated preview for review.

### 3.2 Runtime format

The runtime manifest lives at `Manifest/lulu-motion.v1.json`.

It explicitly defines:

- character and design versions;
- atlas paths and grid dimensions;
- global frame canvas and anchor;
- named clips;
- frame order and duration;
- loop mode;
- poster frame for Reduce Motion;
- transition timing.

The JSON, rather than Swift code, owns timing and atlas coordinates. Swift owns only state resolution and rendering.

## 4. Canonical Lulu design lock

All future generation prompts must preserve these invariants.

### Identity

- golden-yellow round head and body;
- very large soft orange muzzle;
- tiny rounded ears;
- glossy dark eyes with blue-white highlights;
- one friendly visible tooth only when the mouth is open;
- short limbs and brown fingertips;
- orange shorts;
- tiny orange fruit with a green stem on the head;
- deep leaf-green bow tie in steward and Hermes states.

### Proportion and camera

- full body, front-facing or a very mild three-quarter angle;
- head and muzzle dominate the silhouette;
- body occupies roughly 76% of the cell height for core states;
- fixed 627×627 transparent cell in V1;
- normalized foot baseline at y=590–600;
- no camera zoom, perspective change or arbitrary body reshaping between frames.

### Rendering

- smooth semi-matte premium 3D mascot finish;
- warm soft studio light;
- no cast shadow or contact shadow in production frames;
- no white sticker outline;
- no particles, smoke, steam or translucent effects in the first asset version;
- props remain attached to or close to Lulu so each frame has one readable silhouette.

### Costume hierarchy

1. Hermes / inventory: green bow tie;
2. recipe planning: soft white chef toque plus green neck detail;
3. cooking guide: chef toque and green neckerchief;
4. device states: bow tie plus compact signal/listening prop;
5. the orange fruit remains visible unless a hat intentionally overlaps it.

## 5. Home-screen experience

The first screen should initially contain only:

1. animated Lulu in the visual center;
2. the Hermes conversation field at the bottom.

No permanent quick-action grid, conversation card, metrics, inventory cards or full navigation header should compete with Lulu.

### Initial state

- Lulu runs `home.idle`, a slow breathing and blinking loop;
- the background is the existing warm canvas with a very soft leaf-green halo;
- the bottom Hermes field says `今晚吃什么？`;
- empty input shows the microphone action;
- tapping Lulu can trigger a one-shot wave without navigating.

### Conversation state changes

- field focus or voice capture → `home.listening`;
- submit → `home.thinking`;
- response arrival → `home.reply`;
- successful routed action → `system.celebrate`;
- operation failure → `system.concern`;
- after the one-shot clip completes → return to `home.idle`.

The conversation answer can appear temporarily above Lulu as a compact bubble. It should not turn the first screen into a conventional chat transcript unless the user explicitly opens conversation history.

## 6. Deep page integration

### Inventory

- header companion: Lulu peeks around the refrigerator edge;
- active scan: magnifier/viewfinder animation tied to `ScanStatus`;
- analyzing: eyes move between fridge and clipboard;
- unresolved changes: inventory-steward Lulu holds the checklist;
- empty state: Lulu opens an empty fridge and invites a scan;
- scan complete: one-shot leaf-check celebration.

### Recipes

- loading recommendations: recipe-planner Lulu studies a card;
- ready-now recipes: Lulu points at the leading recipe;
- missing ingredients: Lulu compares recipe card and inventory list;
- recipe detail: a compact chef Lulu sits beside the ingredient summary;
- start cooking: transition into the cooking-guide costume.

### Shopping

- calculating gaps: clipboard or basket-planning clip;
- quote ready: Lulu presents the basket;
- final confirmation: Lulu holds the leaf-check shield, never a payment card;
- merchant redirect: Lulu opens a small door/arrow gesture;
- offline: concerned Lulu protects the pending list rather than showing failure drama.

### Cooking

- map recipe step keywords to a small reusable action family: prep, chop, stir, heat, timer and plate;
- show one 120–160 pt Lulu beside the current-step card, not inside every card;
- a running timer uses a calm watchful loop, not a fast animation;
- pause uses a resting pose;
- completion uses a short pancake/plate celebration.

### Device and onboarding

- discovery: Lulu listens with a compact signal motif;
- pairing: Lulu holds a key/check badge;
- online: calm steward pose;
- recovering: searching/concerned pose;
- offline cache: sleeping or protective pose, without implying lost data.

## 7. Motion-state resolver

Only one high-priority Lulu clip should control a viewport at a time.

Priority order:

1. blocking error or explicit failure;
2. pending user confirmation;
3. active cooking timer or step transition;
4. active refrigerator scan;
5. loading, reasoning or quote generation;
6. device recovery or offline state;
7. recent success event;
8. page-specific idle;
9. global `home.idle` fallback.

This avoids conflicting animations when, for example, the device is recovering while a stale recipe screen is visible.

## 8. SwiftUI architecture

Implemented components:

- `LuluMotionManifest`: Codable representation of the JSON;
- `LuluMotionLibrary`: loads each atlas lazily, crops cells once and caches `UIImage` frames;
- `LuluMotionClip`: strongly typed semantic clip identifiers;
- `LuluMotionView`: cancellable async frame playback with authored per-frame delays;
- `HomeView`: home-specific state resolver, temporary Hermes bubble and bottom composer;
- `LuluCompanionCard`: compact page-header integration for the task screens.

Use explicit per-frame duration rather than a universal FPS. The renderer should:

- pause when the scene is inactive;
- stop when off-screen;
- cache only decoded frames needed by visible clips;
- crossfade clips for 100–140 ms while keeping the same anchor;
- use the manifest poster frame when Reduce Motion is enabled;
- preserve layout dimensions during every frame change.

Target rates:

- idle and waiting: 4–8 visible changes per second at most;
- short actions: 8–12 changes per second;
- no reason to render generated raster animation at 60 fps.

## 9. Asset scope

The current iOS package exposes ten continuously animated semantic clips. Every state is a four-step loop, for 40 authored playback frames in the manifest:

1. `home.idle`
2. `home.listening`
3. `home.thinking`
4. `home.reply`
5. `inventory.scan`
6. `inventory.review`
7. `recipes.plan`
8. `shopping.organize`
9. `cooking.guide`
10. `device.connect`

`home.listening` keeps the ear gesture, eye tracking and blink moving for as long as the composer is focused. `home.reply` repeats a readable wave while a Hermes answer is visible and also runs for several cycles whenever Lulu is tapped. `inventory.review` continuously moves the gaze and checking fingertip. The remaining seven clips keep their original task loops. The procedural breathing layer is now only a subtle secondary motion, never the sole animation for a product state.

All production atlases are registered after generation. The registration pass detects Lulu's large orange muzzle instead of the whole composition, so moving recipe cards, baskets, pans and vegetables cannot drag the character sideways. It separately locks the detected foot baseline and rejects any shift that clips visible alpha.

## 10. Quality gates

Every generated sheet must pass:

- same face geometry and muzzle size in every frame;
- identical costume colors;
- no extra fingers or duplicate limbs;
- no crop at the fruit, ears, hands, props or feet;
- transparent corners and no magenta fringe;
- fixed foot baseline;
- orange-muzzle drift no more than 4 px (0.64% of the 627 px cell) after registration;
- foot-baseline drift exactly 0 px inside a clip after registration;
- frame-to-frame scale drift used only when intentionally describing breathing;
- readable silhouette at 60 pt;
- acceptable poster frame with Reduce Motion enabled.

## 11. Current production assets

- `Previews/lulu-core-states-preview.png`
- `Previews/lulu-kitchen-roles-preview.png`
- `Previews/lulu-home-idle-frames-preview.png`
- `Previews/lulu-home-idle-preview.gif`
- `Previews/lulus-fridge-home-motion-concept.gif`
- `Previews/App/lulus-fridge-ios-pages-overview.png`
- `Previews/App/lulus-fridge-home-motion-preview.mp4`
- `Animations/HomeIdle/lulu-home-idle-atlas.png`
- `Animations/HomeListening/lulu-home-listening-atlas.png`
- `Animations/HomeThinking/lulu-home-thinking-atlas.png`
- `Animations/HomeReply/lulu-home-reply-atlas.png`
- `Animations/InventoryScan/lulu-inventory-scan-atlas.png`
- `Animations/InventoryReview/lulu-inventory-review-atlas.png`
- `Animations/RecipePlan/lulu-recipe-plan-atlas.png`
- `Animations/ShoppingOrganize/lulu-shopping-organize-atlas.png`
- `Animations/CookingGuide/lulu-cooking-guide-atlas.png`
- `Animations/DeviceConnect/lulu-device-connect-atlas.png`
- `Tools/register_lulu_frames.py`
- `Tools/validate_motion_assets.py`
- `Animations/ShoppingOrganize/lulu-shopping-organize-atlas.png`
- `Animations/CookingGuide/lulu-cooking-guide-atlas.png`
- `Animations/DeviceConnect/lulu-device-connect-atlas.png`
- `Manifest/lulu-motion.v1.json`

All nine atlases and the manifest are installed in `ShiguangKitchen/Resources/Assets.xcassets`. The renderer lives in `Core/DesignSystem/KitchenDesign.swift`; feature screens consume semantic clip names and never crop atlases directly. The home, inventory, recipes, recipe detail, shopping, cooking, device, onboarding and loading experiences are wired to Lulu. App call sites remain unchanged when a poster clip is later replaced with another four-frame atlas.
