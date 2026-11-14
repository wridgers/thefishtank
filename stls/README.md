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

Everything to buy is in [`BOM.md`](../BOM.md).

## Assembly

1. **Inserts.** Fit all the heat-set inserts.
   - The joint inserts in the front half's tongues go in from the inside face of the ribs.
   - The foot inserts go in from outside, flush with the wall.
2. **Front half.**
   1. Fit the hub into its pocket and screw on the retainer.
   2. Fit the power button.
   3. Lay the hub cable along the floor toward the back.
3. **Back half.**
   1. Slide the PSU against the back wall and fit its two screws.
   2. Glue in the grills; the rear grill goes in the back half only.
4. **Board.** Clamp the shrouds onto the BC-250, then fit the backplate fan mount and the
   slim fan.
5. **Pull fan stack.**
   1. Lay the wall gasket, fan, and fan gasket against the back half's left wall.
   2. Push the four FHCS M3x40 in from outside, only until their tips are flush with the
      stack, to hold it in place.
6. **Board into the back half.** Slide the board in, nudged slightly toward the right wall,
   with the I/O bracket tab riding over its ledge. Don't tighten anything yet.
7. **Cables.**
   - Connect the PSU to the board.
   - Route the hub cable up behind the pull shroud's end wall and round the I/O bracket into
     the I/O recess. Plug it into a rear USB port there through the right-angle adapter.
8. **Front half.** Set up the push fan stack on its wall the same way, then slide the front
   half on. The tongues engage before the zigzag seam does. Fit the four FHCS M3x12 joint screws.
9. **Tighten.** Tighten all eight fan screws; this pulls the board against the left wall.
   Then fit the bracket-tab screw through the access hole in the top.
10. **Feet.** Screw on the feet for the orientation you want.
