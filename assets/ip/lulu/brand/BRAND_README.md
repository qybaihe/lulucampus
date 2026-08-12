# Lulu's Fridge · Brand Direction V1

## Product translation

The iOS app is primarily an inventory and household decision product: it maintains a trusted fridge state, recommends meals from available ingredients, and prepares shopping gaps. The identity therefore centers **Lulu + refrigerator stewardship + freshness**, rather than a generic chef or recipe symbol.

## Selected direction: Concept B

Concept B is the production recommendation because Lulu's face, the refrigerator door, and the leaf-check remain recognizable at 40–60 px.

- **Lulu's large face:** emotional recognition and companionship.
- **Mint refrigerator arch/door:** communicates the product category immediately.
- **Green bow tie:** makes Lulu read as a friendly household steward.
- **Leaf-shaped check badge:** combines freshness with trustworthy inventory management.
- **Tomato and green vegetable:** signal food inventory without overloading the icon.

Concept A is retained as a richer storytelling alternative for posters, onboarding, and presentation materials.

## Visual hierarchy

1. Lulu's eyes, orange muzzle, and smile.
2. Refrigerator arch and open door.
3. Leaf-check inventory badge.
4. Food color accents.

The app icon contains no wordmark. The horizontal brand lockup uses the exact name `Lulu's Fridge` in SF Pro Rounded.

## Palette

- Leaf green `#33964F`
- Soft leaf `#E8F7EB`
- Citrus orange `#F5992E`
- Tomato red `#E64538`
- Warm canvas `#F5F7F0`
- Deep ink `#1A261F`

This maps directly to `KitchenPalette` in the existing SwiftUI project and keeps the new identity visually native to the current app.

## iOS usage

- Use `Final/lulus-fridge-app-icon-1024.png` as the unrounded, opaque App Icon master.
- Do not add transparency or manually round the production App Icon; iOS applies its own mask.
- Use `Final/lulus-fridge-logo-lockup-transparent.png` for decks, onboarding, and documentation.
- Concept B is optimized for small icon sizes; Concept A is optimized for richer storytelling.

## Generation workflow

Built-in ImageGen was used with the supplied Lulu reference and the project's ingredient catalog. The selected output was resized locally with high-quality Lanczos resampling and validated as an opaque RGB 1024×1024 PNG.
