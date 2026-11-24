# Assembly

> [!WARNING]
> **Work in progress.** Examine each step before you do it. This procedure comes from the CAD
> model. The case is not assembled yet. The steps can change after the first assembly.

Before you start, make sure that you have the printed parts ([`README.md`](README.md)) and all
the items in [`BOM.md`](../BOM.md).

1. **Frame parts.**
   1. Cut the extrusions to length: four long rails, four uprights, and three cross rails. Make the
      ends square.
   2. Tap the centre hole M5 at the two ends of each upright and each cross rail.
   3. Drill the access holes in the long rails with the drill jig. Refer to
      [Access holes](#access-holes).
2. **Inserts.** Install the heat-set inserts.
   1. Install the splice strip inserts from the face that does not touch the panel.
   2. Install the tab insert in the tab bar, from its top face.
   3. Install the fan inserts and the clamp inserts in the shrouds, and the fan inserts in the
      backplate fan mount.
   4. Install the four fan hub inserts in the plate extension of the backplate fan mount, from the
      side of its feet.
3. **Side frames.**
   1. Install a BHCS M5x10 in each end of the uprights. Keep 2 mm between the head and the end of
      the upright.
   2. Make the left side frame: two long rails and two uprights. Slide the screw heads into the
      slots of the long rails from the ends. Align the outer face of each upright with the end of
      the long rail. The screw head is then below its access hole.
   3. Align the ends. Tighten the screws through the access holes with a 3 mm hex key.
   4. Make the right side frame in the same way.
4. **Box.**
   1. Install a BHCS M5x10 in each end of the three cross rails, as in step 3.
   2. Put a T-nut into the inner slot of each back upright, near the bottom.
   3. Put the back brace between the two back uprights. Put the bumps on its ends into the inner slots
      of the uprights. Move the two side frames together on the bumps.
   4. Slide two cross rails in from the front: one at the top and one at the bottom. The screw heads
      go into the inner slots of the long rails.
   5. Tighten the screws through the access holes in the outer faces of the long rails.
   6. Install a BHCS M3x10 through each end wall of the back brace, from its window, into the
      T-nut. Do not tighten the screws yet.
   7. Keep the third cross rail for step 11. It goes at the top of the back.
5. **T-nuts.** Put the M3 T-nuts into the slots below the screw holes of each panel. Use the panel
   as a template. The T-nuts go in from the front of the slot, so you can install them at any time.
6. **Bottom panel.** Join the two pieces of the bottom panel with a top and bottom splice strip and
   two FHCS M3x10. Install the bottom panel with FHCS M3x10.
7. **USB hub, front panel, and power button.**
   1. Install the hub cradle behind the front right upright. Install two FHCS M3x16 through its block
      into the T-nuts in the back slot of the upright.
   2. Put the USB hub into the cradle from the front, with the ports to the front and the cable end
      down. The cable goes down through the slot in the floor of the cradle. The floor and the cap of
      the cradle hold the ends of the hub. The back wall of the cradle holds the hub when you push a
      plug in.
   3. Install the front panel with FHCS M3x10. The hub is behind the panel, so the panel holds it when
      you pull a plug out.
   4. Install the power button.
8. **PSU.**
   1. Install the PSU mount on the top faces of the bottom long rails, with two FHCS M3x16 into
      T-nuts. Its plate goes toward the back.
   2. Lift the back brace. Slide the PSU in from the back, below the back brace, with its modular
      sockets first. It goes on the bottom panel, between the bottom rails. Push it until the lip in
      front of the sockets touches the plate of the PSU mount.
   3. Install two FHCS #6-32 x 3/8" through the plate into the lip.
   4. Lower the back brace onto the PSU. Tighten the two brace screws through the windows with a
      ball-end hex key. The PSU sets the height of the brace.
   5. Install the bottom piece of the back panel with FHCS M3x10, and the two PSU screws through it.
      The PSU is then held at both ends. This piece stays on when you remove the top piece.
9. **Tab bar.**
   1. Put a T-nut into the inner slot of each back upright, near the top.
   2. Put the tab bar between the back uprights, at the top. Put the bumps on its ends into the inner
      slots of the uprights.
   3. Install a BHCS M3x10 through each end wall of the tab bar, from the inner side, into the
      T-nut. Use a ball-end hex key. Do not tighten the screws yet.
   4. Push the tab bar up until the bumps touch the top long rails. Tighten the two screws.
10. **Board.**
    1. Attach the shrouds to the BC-250 with the clamps. Install the backplate fan mount. Do not
       install the slim fan or the fan hub yet.
    2. Lower the board in from the top, at the back. Put the I/O bracket between the back uprights.
       Make sure that the tab of the I/O bracket goes onto the tab bar, and that the bottom of the
       bracket goes into the slot on the top of the back brace.
    3. Install the BHCS M3x10 through the tab into the tab insert.
    4. From the right side, install the slim fan on the backplate fan mount.
    5. Put the fan hub against the plate extension of the mount, between the four fan hub inserts.
       Put its SATA input toward the edge of the board that has the power extension.
    6. Put the fan hub frame on the fan hub. Make sure that the fan hub is inside the wall of the
       frame. Install the four FHCS M3x25 through the frame legs into the inserts.
11. **Top back cross rail.** Slide the screw heads of the third cross rail into the inner slots of
    the top long rails, from the back ends. Align the back face of the cross rail with the ends of
    the long rails. Tighten the screws through the access holes in the outer faces of the long rails.
12. **Back panel, top piece.** Install the top piece of the back panel with FHCS M3x10.
13. **Cables.**
    1. Connect the PSU to the board and to the SATA input of the fan hub.
    2. Connect the slim fan and CPU_FAN1 to the fan hub. Attach the cables to the zip tie mounts on
       the shrouds.
    3. Put the USB hub cable along the floor, toward the back. Put it up into the I/O opening and
       connect it to a rear USB port through the right-angle adapter.
14. **Left panel.**
    1. Join the two pieces of the left panel with a side splice strip.
    2. Assemble the push and pull fan stacks on the inner side of the left panel. For each stack, put
       the wall gasket, the fan, and the fan gasket against the panel. Push the four FHCS M3x40
       through the panel from the outer side. Stop when the tips of the screws are flush with the
       stack. The screws then hold the stack in position.
    3. Connect the push and pull fans to the fan hub.
    4. Put the left panel on the frame. Turn the fan screws into the shroud inserts, but do not
       tighten them.
    5. Install the panel screws.
    6. Tighten all eight fan screws. This pulls the board against the left panel.
15. **Top panel.** Join the two pieces with a top and bottom splice strip. Install the top panel.
16. **Right panel.** Join the three pieces with two side splice strips. Install the right panel.
17. **Feet.** Install the feet for the position that you want. Each foot has an FHCS M3x16 that goes
    through the panel into a T-nut.
    - To stand the case upright, install the short feet on the bottom.
    - To put the case on its right side, install the tall feet on the right side.

## Removing the board

The frame holds the board and the PSU, so you can remove the top piece of the back panel without
other work. To remove the board:

1. Remove the top panel, the top piece of the back panel, and the left panel. Disconnect the cables.
2. Loosen the two screws of the top back cross rail through their access holes. Slide the cross
   rail out of the back.
3. Remove the screw of the bracket tab. Lift the board out from the top.

## Access holes

Each blind joint has a BHCS M5x10 in the tapped end of an upright or a cross rail. The head of the
screw is in the slot of a long rail. You tighten it with a hex key through an access hole. The
access hole goes through the opposite face of the long rail, on the axis of the screw.

Drill these holes in each long rail. All the holes are 10 mm from the end of the rail, on the
centre line of the slot.

| Face | Position | Joint |
|---|---|---|
| Outer horizontal face: the top of a top rail, or the bottom of a bottom rail | Both ends | Uprights |
| Outer side face (the left face of a left rail, or the right face of a right rail) of a top rail | Both ends | Cross rails |
| Outer side face of a bottom rail | Front end only | Cross rail |

To drill a hole:

1. Put the jig on the end of the rail. Put the bump of the jig into the slot of the face that you
   drill.
2. Push the jig until the end of the rail touches the end stop.
3. Hold the jig. Drill a 5 mm hole through the guide bore. Drill through the slot and the centre of
   the rail until the drill goes into the opposite slot. Do not cut the lips of the opposite slot.
4. Remove the burrs and the chips.
