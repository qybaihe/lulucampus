# Lulu Motion · ImageGen Production Notes

## Mode

- Generator: built-in Codex ImageGen
- Use case: `stylized-concept`
- Output unit: one exact 2×2 production sprite sheet per semantic clip
- Key background: flat `#ff00ff`
- Alpha conversion: local `remove_chroma_key.py` with explicit `#ff00ff`, soft matte, thresholds 40/160 and despill
- Registration: `Tools/register_lulu_frames.py`

## Prompt set added in V3

### Home listening

Preserve the canonical golden-yellow Lulu identity, green bow tie, orange shorts and head fruit. Generate four sequential listening frames in an exact 2×2 sheet: paw beside one ear, subtle gaze shift, quick blink, and return. Lock body scale, torso, feet and orange-muzzle center. Use a perfectly flat `#ff00ff` background with no floor, shadow, text, props or extra characters.

Source: `Animations/HomeListening/source/lulu-home-listening-chroma.png`

### Home reply / wave

Preserve the canonical Lulu identity. Generate one seamless repeated wave in an exact 2×2 sheet: raised paw inward, paw outward, return inward with blink, outward with open smile. Lock torso, feet, fruit, bow tie and orange-muzzle center. Make the paw arc readable at 140 pt. Use a perfectly flat `#ff00ff` background with no floor, shadow, text, props or extra characters.

Source: `Animations/HomeReply/source/lulu-home-reply-chroma.png`

### Inventory review

Preserve the canonical Lulu identity and kitchen-steward styling. Generate four sequential inventory-review frames in an exact 2×2 sheet: look at first clipboard line, tap the first check, move gaze/fingertip down with a blink, then present the completed checklist. Keep the cream clipboard, green clip and tomato anchored. Lock body scale, torso, feet and orange-muzzle center. Use a perfectly flat `#ff00ff` background with no floor, shadow, words, logos or extra characters.

Source: `Animations/InventoryReview/source/lulu-inventory-review-chroma.png`
