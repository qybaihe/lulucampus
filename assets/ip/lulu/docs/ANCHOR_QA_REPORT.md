# Lulu Motion · Anchor QA

All values are measured in the 627×627 production cell. The face anchor is the centroid of Lulu's large orange muzzle; the vertical anchor is the detected foot baseline.

| Clip | Raw muzzle drift | Registered drift | Foot drift after registration |
|---|---:|---:|---:|
| `home.idle` | 1.43 px | 0.64 px | 0 px |
| `home.listening` | 110.73 px | 1.33 px in playback sequence | 0 px |
| `home.thinking` | 3.28 px | 0.83 px | 0 px |
| `home.reply` | 80.26 px | 2.27 px | 0 px |
| `inventory.scan` | 50.58 px | 1.12 px | 0 px |
| `inventory.review` | 90.90 px | 3.33 px | 0 px |
| `recipes.plan` | 84.58 px | 0.78 px | 0 px |
| `shopping.organize` | 60.07 px | 0.36 px | 0 px |
| `cooking.guide` | 54.78 px | 0.82 px | 0 px |
| `device.connect` | 1.97 px | 0.41 px | 0 px |

Quality gate:

```bash
python Design/LuluMotion/Tools/validate_motion_assets.py \
  Design/LuluMotion/Manifest/lulu-motion.v1.json
```

The validator requires muzzle drift ≤4 px and foot drift =0 px for every multi-frame clip, in addition to atlas geometry, alpha, timing and frame-cell validation.
