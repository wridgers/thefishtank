# Printing

An `[a]_` prefix shows a part in the accent colour. An `_xN` suffix shows the quantity to print.
Print the other parts in the primary colour. Print the `tpu_` parts in TPU.

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
| `tpu_foot_short_x4.stl` | 4 | TPU, for the standing position |
| `tpu_foot_tall_x4.stl` | 4 | TPU, for the lying position |

- **Orientation.** Print each STL file in the orientation that it has. The case halves stand on
  their end faces. The grills print with their outer face on the bed. This gives the outer face
  the smoothest surface.
- **Material.** The shrouds and the clamps touch the heatsink. Print them in a material that is
  resistant to heat, for example PETG, ASA, or ABS. Do not use PLA. For the case, use PETG or ASA.
- **Size.** The front half is approximately 210 mm high. The back half is approximately 196 mm
  high. Each half has a footprint of approximately 198 × 125 mm.
- **Fit.** Each grill has 0.3 mm of clearance on each side. Attach the grills with glue. The rear
  grill goes across the seam. Attach it to the back half only, so that you can remove the front
  half.

For the parts to buy, refer to [`BOM.md`](../BOM.md). For the assembly procedure, refer to
[`ASSEMBLY.md`](ASSEMBLY.md).
