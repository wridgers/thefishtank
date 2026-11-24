# Printing

> [!WARNING]
> **Work in progress.** The board parts are printed. The enclosure parts are not printed or
> assembled yet. Examine the fit of each part before you use this design.

An `[a]_` prefix shows a part in the accent colour. An `_xN` suffix shows the quantity to print.
Print the other parts in the primary colour. Print the `tpu_` parts in TPU.

## Board parts

These parts attach to the BC-250 and hold its fans.

| STL | Qty | Colour / material |
|---|---|---|
| `fan_shroud_push.stl`, `fan_shroud_pull.stl` | 1 each | Primary |
| `pcb_clamp_x7.stl` | 7 | Primary |
| `backfan_mount.stl` | 1 | Primary |
| `fan_hub_frame.stl` | 1 | Primary |
| `tpu_fan_gasket_x5.stl` | 5 | TPU |
| `tpu_fan_washer_x4.stl` | 4 | TPU |

## Enclosure parts

| STL | Qty | Colour / material |
|---|---|---|
| `panel_left_back.stl`, `panel_left_front.stl` | 1 each | Primary |
| `panel_right_back.stl`, `panel_right_middle.stl`, `panel_right_front.stl` | 1 each | Primary |
| `panel_top_back.stl`, `panel_top_front.stl` | 1 each | Primary |
| `panel_bottom_back.stl`, `panel_bottom_front.stl` | 1 each | Primary |
| `panel_front.stl`, `panel_back_bottom.stl`, `panel_back_top.stl` | 1 each | Primary |
| `splice_side_x3.stl` | 3 | Primary. One for the left panel, two for the right panel. |
| `splice_top_bottom_x2.stl` | 2 | Primary. One for the top panel, one for the bottom panel. |
| `back_brace.stl` | 1 | Primary |
| `tab_bar.stl` | 1 | Primary |
| `psu_mount.stl` | 1 | Primary |
| `hub_cradle.stl` | 1 | Primary |
| `tpu_foot_short_x4.stl` | 4 | TPU, for the standing position |
| `tpu_foot_tall_x4.stl` | 4 | TPU, for the lying position |
| `[a]_blind_joint_drill_jig.stl` | 1 | Accent. A tool to drill the frame (5 mm access holes and 3.4 mm brace screw holes). You do not install it. |

## Notes

- **Bed size.** All the parts fit on a 250 × 250 mm bed. The largest parts are
  `backfan_mount.stl` (206.7 × 140.6 mm), `panel_left_back.stl` (186.8 × 204.9 mm), and
  `panel_bottom_back.stl` (201.8 × 130.9 mm).
- **Orientation.** Print each STL file in the orientation that it has. Each part that you can see
  prints with its visible face on the bed. Thus you can use a textured build plate, or a special
  pattern for the first layer (for example, a Hilbert curve).
- **Material.** The shrouds and the clamps touch the heatsink. Print them in a material that is
  resistant to heat, for example PETG, ASA, or ABS. Do not use PLA. Use PETG or ASA for the panels
  and the other parts that are not TPU.
- **Edges.** The panel edges are 45° mitres, so the panels meet at sharp square corners. The mitres
  lean in from the bed, so they print without supports. There is a 0.3 mm gap between the mitres of
  two panels, and between the pieces of a split panel.
- **Bed chamfers.** The bed edges of each part have a 0.5 mm chamfer against elephant's foot.
  Between two panels, the chamfers make a small V-groove along the edge of the case.
- **Warping.** Each panel piece has a screw at each of its corners. This holds the corners flat if
  the part warps a small amount (for example, in ASA).
- **Grills.** The grills are hex holes in the panels. The grills of each panel are symmetrical on
  that panel, thus they do not align fully with the fans behind them. Each fan screw in a grill goes
  through a small solid area.
- **Pattern.** The front panel has a hex pattern in its outer face. The grooves are on the bed
  face. Their 45° walls print without supports.
- **Slot bumps.** Each face of a part that touches a slot of the frame has a low, round bump along
  the slot. The bump goes into the slot and aligns the part. It has a 0.3 mm gap to each side of
  the slot, so it does not grip.

For the parts to buy, refer to [`BOM.md`](../BOM.md). For the assembly procedure, refer to
[`ASSEMBLY.md`](ASSEMBLY.md).
