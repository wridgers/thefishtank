# Printing

An `[a]_` prefix marks an accent-colour part, and `_xN` means print N of it. Everything else
prints in the primary colour, apart from the TPU parts.

| STL | Qty | Colour / material |
|---|---|---|
| `case_front.stl`, `case_back.stl` | 1 each | Primary |
| `[a]_fan_grill_x2.stl` | 2 | Accent |
| `[a]_rear_grill.stl` | 1 | Accent |
| `[a]_top_vent_grill_x2.stl` | 2 | Accent |
| `fan_shroud_push.stl`, `fan_shroud_pull.stl` | 1 each | Primary |
| `backfan_mount.stl` | 1 | Primary |
| `pcb_clamp_x7.stl` | 7 | Primary |
| `hub_retainer.stl` | 1 | Primary |
| `tpu_fan_gasket_x5.stl` | 5 | TPU |
| `tpu_fan_washer_x4.stl` | 4 | TPU |
| `tpu_foot_short_x4.stl` | 4 | TPU, for standing |
| `tpu_foot_tall_x4.stl` | 4 | TPU, for lying flat |

- **Orientation.** Print every STL as it is. The case halves stand on their end faces, and
  the grills print with their outside face on the bed for the smoothest finish.
- **Material.** The shrouds and clamps sit against the heatsink, so print them in something
  that copes with heat (PETG, ASA, or ABS), not PLA. PETG or ASA is a good choice for the case.
- **Size.** The front half prints about 210 mm tall and the back half about 196 mm, on a
  footprint of about 198 × 125 mm.
- **Fit.** The grills have 0.3 mm of clearance per side and are glued in. The rear grill
  spans the seam: glue it into the back half only, so the front half can still slide off.

Everything to buy is in [`BOM.md`](../BOM.md), and how to put it together is in
[`ASSEMBLY.md`](ASSEMBLY.md).
