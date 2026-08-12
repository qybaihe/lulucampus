# Lulu Motion · App State Matrix

## Implemented iOS wiring

| Screen / signal | Active clip | Result |
|---|---|---|
| Home initial | `home.idle` | authored breathing/blink loop |
| Hermes composer focused | `home.listening` | continuous ear gesture, gaze shift and blink loop |
| Hermes prompt submitted | `home.thinking` | four-frame thinking loop |
| Hermes answer shown | `home.reply` | repeated four-step wave + temporary answer bubble |
| Inventory scan active | `inventory.scan` | four-frame magnifier sweep |
| Inventory idle / confirmation | `inventory.review` | continuous checklist gaze and fingertip loop |
| Recipes list and detail | `recipes.plan` | four-frame planning loop |
| Shopping | `shopping.organize` | four-frame basket loop |
| Cooking | `cooking.guide` | four-frame pancake-flip loop |
| Loading, device and pairing | `device.connect` | four-frame signal loop |

## Target priority matrix

| Priority | Existing app signal | Lulu clip | Placement | Behavior |
|---:|---|---|---|---|
| 100 | `lastError != nil` | `system.concern` | current page status area | one-shot concern, then hold poster |
| 95 | unresolved inventory or checkout confirmation | `inventory.review` | confirmation card/header | hold checklist pose |
| 90 | cooking timer running | `cooking.timer` | cooking step card edge | calm watch loop |
| 88 | cooking step changes | `cooking.guide` | cooking header | short action, then task idle |
| 85 | `activeScan.status == .capturing` | `inventory.scan` | fridge overview | active scan loop |
| 84 | `activeScan.status == .analyzing` | `home.thinking` | fridge overview | thinking loop |
| 83 | `activeScan.status == .reconciling` | `inventory.review` | fridge overview | checklist loop |
| 82 | scan completed / inventory updated event | `system.celebrate` | fridge overview | one-shot success |
| 80 | scan failed | `system.concern` | fridge overview | one-shot concern |
| 75 | `isLoading`, `isRefreshing` or `isRecipeLoading` | `home.thinking` | active page hero | thinking loop |
| 72 | refreshing retail quotes | `shopping.organize` | shopping header | basket/clipboard loop |
| 70 | `connectionState == .recovering` | `device.connect` | page header/device page | searching loop |
| 68 | `connectionState == .offlineCached` | `system.concern` | page header/device page | quiet protective hold |
| 60 | home composer focused or voice capture | `home.listening` | home hero | listening loop |
| 58 | home message submitted | `home.thinking` | home hero | thinking loop |
| 56 | Hermes response arrives | `home.reply` | home hero | one-shot reply/wave |
| 40 | inventory tab idle | `inventory.review` | inventory header | slow page idle |
| 40 | recipes tab idle | `recipes.plan` | recipe header | slow page idle |
| 40 | shopping tab idle | `shopping.organize` | shopping header | slow page idle |
| 40 | cooking screen idle | `cooking.guide` | cooking header | slow page idle |
| 40 | device screen idle | `device.connect` | device header | slow page idle |
| 0 | no higher-priority state | `home.idle` | home hero | breathing/blink loop |

## Placement scale

| Context | Suggested size | Rule |
|---|---:|---|
| Home hero | 240–300 pt | primary visual, initial screen |
| Page header | 96–140 pt | one Lulu only |
| Empty/error state | 140–190 pt | replaces generic SF Symbol art |
| Confirmation card | 72–96 pt | supports, does not obscure content |
| Hermes message avatar | 36–48 pt | poster frame only by default |

## Interaction rules

- Tapping home Lulu keeps the wave loop active for several cycles, then returns to the relevant idle/listening state.
- Every visible semantic state has authored frame motion; procedural breathing is only a secondary layer.
- Each clip is muzzle-registered and foot-baseline-registered, so moving props do not translate Lulu.
- Long-running loops never block scrolling or input.
- A one-shot result clip returns to the relevant page idle after completion.
- New higher-priority states interrupt current clips with a short anchored crossfade.
- Lower-priority state changes wait until a one-shot clip reaches its final frame.
- Do not show two animated Lulu instances in the same viewport.
