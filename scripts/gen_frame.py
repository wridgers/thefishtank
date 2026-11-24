# Generates the enclosure of The Fish Tank: a box of 2020 aluminium extrusions with blind joints and
# printed panels, holding the board module (board, shrouds, backplate fan mount, fan hub: gen_shrouds.py)
# in the board frame (X along the board from the I/O edge, Y up, Z toward the push-pull fans).
# Run with: GEN_MAIN=frame OUTDIR=<project dir> freecadcmd scripts/gen_frame.py
# (FCStd goes to OUTDIR/cad, printable STLs to OUTDIR/stls, laid out in print orientation.)
#
# Frame: four long rails (X) run the full length; four uprights (Y) and three cross rails (Z) stand
# between them, each joined at both ends by an M5 screw into its tapped end, with the head in the long
# rail's slot (reached through a drilled access hole). The bottom back cross rail is a printed brace
# instead, above the PSU, so the PSU stands on the floor, at the back. The top
# back cross rail slides out of the long rails' slots at the back (loosen its two joints), so the board
# can go in from the top. The board's I/O bracket tab screws into a printed tab bar between the back
# uprights: the board is held by the frame, and the back panel comes off on its own.
#
# Panels: 4 mm plates on the frame's outer faces, printed outer (visible) face down, each screwed (FHCS
# M3x10, flush) into T-nuts in the rail slots under its edges, with a screw at every corner of every
# piece. Their edges are 45 deg mitres, so neighbouring panels meet in a sharp square corner over the
# frame. The fan and vent grills are hex holes in the panels. Panels longer than the bed are split; a
# printed splice strip behind each split takes an FHCS M3x10 from each side.
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App, Part
from gen_shrouds import (CADDIR, Params, SK, feat, check, export_stl, stl_path, at_z, chamfer, check_lock,
                         teardrop, cut_through, seg_dist)

V = App.Vector
OUTDIR = os.environ.get('OUTDIR', '.')

FRAME = [
    # --- fixed by the board module
    ('PanelT', 4.0, 'Panel thickness: the fan screws (FHCS M3x40) go through it, flush'),
    ('ZLeftIn', 80.7, 'Left panel inner face (Z): the push/pull fan stacks press against it'),
    ('FanStackClear', 0.5, 'Fan stacks to the left panel, before the fan screws tighten (the TPU takes it up)'),
    ('XBackIn', -18.5, 'Back panel inner face (X): the I/O bracket sits against it'),
    ('YBotIn', -53.5, 'Bottom panel inner face (Y): the PSU stands on it'),
    # --- the extrusion box (inner faces of the panels = outer faces of the frame)
    ('ExtW', 20.0, '2020 extrusion size'),
    ('RailLX', 367.0, 'Long rails (X), back to front: the front rails clear the push shroud end (327.65)'),
    ('RailLY', 158.0, 'Uprights (Y), between the long rails: the top rails clear the 124 mm fan gaskets (122.75)'),
    ('RailLZ', 84.0, 'Cross rails (Z), between the long rails: the PSU (81.5 wide) fits between the bottom rails'),
    ('SlotC', '=ExtW / 2', 'Slot centre line from a rail edge'),
    ('XFrontIn', '=XBackIn + RailLX', 'Front panel inner face (X)'),
    ('YTopIn', '=YBotIn + RailLY + 2 * ExtW', 'Top panel inner face (Y)'),
    ('ZRightIn', '=ZLeftIn - RailLZ - 2 * ExtW', 'Right panel inner face (Z)'),
    # --- blind joints: M5 into the tapped rail end, head in the long rail's slot under its lip
    ('SlotLip', 1.8, '2020 slot lip thickness (the joint screw head bears under it)'),
    # --- slot bumps: every printed face on a 2020 slot has a smooth bump along it, in the slot opening (6.2),
    # that locates the part. A circular arc in section; loose, so it guides rather than grips
    ('SlotBumpW', 5.6, 'Slot bump: width at the rail face (0.3 clear of the slot opening each side)'),
    ('SlotBumpH', 1.2, '... and how far into the slot (under the 1.8 lip, so above the T-nuts)'),
    ('SlotBumpEnd', 1.0, '... ends this far short of a rail that crosses the slot'),
    # --- PSU (Enhance ENP-8345L, 165 x 40.5 x 81.5), on the floor against the back panel, between the bottom rails
    ('PsuL', 165.0, ''), ('PsuH', 40.5, ''), ('PsuW', 81.5, ''),
    # PSU front mount: the PSU's DC end has a sheet-metal lip with two screw holes (from a photo with a rule).
    # The modular sockets face up, behind the lip: their plugs go in from above, so nothing goes in front of
    # the lip. A printed plate against the lip, with a side each end across the bottom long rail (BHCS M3x16
    # into a T-nut); #6-32 flat heads through the plate into the lip
    ('PsuLipY', 5.6, 'PSU front lip holes: above the PSU bottom'), ('PsuLipZ', 14.5, '... in from each side'),
    ('PsuMountT', 10.0, 'Mount depth (X): one profile, plate, columns and wings'),
    ('PsuScrewL', 9.525, '#6-32 x 3/8" flat heads: the PSU screws, at the back and through the mount into the lip'),
    ('PsuScrewPast', 2.7, '... their tips this far past the mount\'s plate (through the lip)'),
    ('PsuMountCbore', '=PsuMountT + PsuScrewPast - PsuScrewL', 'Counterbore over the lip screws\' countersinks'),
    ('PsuMountChamfer', 1.0, 'Chamfer round the mount\'s front and back faces (the back one also against elephant\'s foot)'),
    ('PsuMountH', '=2 * PsuLipY', 'Mount plate height: the lip screws are in its middle'),
    ('PsuColIn', 8.5, 'Mount sides: their inner faces this far in from the PSU sides'),
    ('PsuMountWingT', 10.0, 'Sides: this far up past the rails\' top faces (BHCS M3x16 into the T-nuts)'), ('PsuMountClear', 0.3, 'Mount to the rails'),
    ('PsuX0', '=XBackIn', 'PSU AC end, against the back panel'), ('PsuY0', '=YBotIn', ''),
    ('PsuZ0', '=(ZRightIn + ZLeftIn) / 2 - PsuW / 2', 'PSU centred between the bottom rails'),
    # --- USB hub (108 x 31 x 10): its ports through the front panel, clear of the front-right upright
    ('HubT', 10.0, ''), ('HubPanelGap', 0.3, 'Hub port face to the front panel (the hub is held by the frame)'),
    ('HubFaceX', '=XFrontIn - HubPanelGap', 'Hub port face'),
    ('HubY0', -17.0, 'Hub cable end (Y): its cable (15 mm straight) clears the bottom front cross rail'),
    ('HubZ', '=ZRightIn + ExtW + 1 + HubT / 2', 'Hub centre (Z): 1 mm clear of the front-right upright'),
    # --- power button: in the front panel, clear of the bottom front cross rail (its nut is 19 mm across flats)
    ('ButtonY', -21.0, 'Power button centre (Y)'), ('ButtonZ', '=(ZRightIn + ZLeftIn) / 2', ''),
    # --- back brace: replaces the back-bottom cross rail, between the back uprights above the PSU
    ('BraceClear', 0.2, 'Back brace to each rail it fits between (its end screws pull it up to them)'),
    ('BraceL', '=RailLZ - 2 * BraceClear', 'Back brace length (Z), between the back uprights'),
    ('BraceD', 18.0, 'Back brace depth (X): from the back panel to just short of the PCB'),
    ('BraceH', 16.0, 'Back brace height (Y)'),
    ('BraceY0', -12.5, 'Back brace underside (Y): 0.5 above the PSU; its top is 1 under the I/O bracket'),
    ('BraceEndT', 6.0, 'Back brace end wall: carries the insert for the screw from outside the upright'),
    ('BraceWinL', 18.0, 'Window behind each end wall: room to press the insert in'),
    ('BraceWinW', 9.0, ''),
    ('BraceScrewY', '=SlotC', 'End screws from the brace back face: on the uprights\' slot centre'),
    ('BraceScrewZ', '=BraceH / 2', 'End screw height in the brace'),
    # a ridge on the brace top with a slot that the bottom of the I/O bracket drops into, the way a case
    # holds a PCIe card's bracket (the tab screw holds the top). Thick walls both sides: the plugs push the
    # bracket forward, and pull it back
    ('IoBackX', -3.35, 'I/O bracket: back face of its plate (X)'), ('IoFrontX', -2.25, '... front face'),
    ('IoBotY', 4.5, '... its bottom edge (Y)'), ('BracketZ1', 26.5, '... its far side (Z)'),
    ('BraceSlotClear', 0.3, 'Slot to the bracket (each side)'), ('BraceSlotUp', 4.5, 'Ridge top: this far up past the bracket bottom'),
    ('BraceSlotLead', 1.0, '45 deg lead-in on the slot mouth'),
    ('BraceRidgeBackT', 6.0, 'Ridge wall behind the bracket'),
    ('BraceRidgeFrontX', 4.0, 'Ridge front face (X): past the brace front, over a 45 deg underside (clear of the PCB edge)'),
    ('BraceRidgeZ0', 2.0, 'Ridge from here (Z): clear of the PCB (0..1.6) and the bracket\'s side flange'),
    ('BraceRidgeFillet', 4.0, 'Fillet at the root of the ridge\'s back wall: it spreads the load from the bracket'),
    ('BraceScrewUp', '=BraceY0 + BraceScrewZ - YBotIn - ExtW', 'End screws: hole through the back uprights, this far '
                     'from their bottom end (drilled with the jig, BHCS M3x20 from outside)'),
    # --- I/O bracket tab: screwed (from above, before the top back cross rail goes in) into an insert in a
    # printed tab bar across the full width between the back uprights, fixed at each end like the back brace
    # (a BHCS M3x20 from outside the upright, through a hole drilled 29 mm from its top end, into an insert)
    ('TabX', -12.35, 'I/O bracket tab screw (X)'), ('TabZ', 6.7, '... (Z)'), ('TabUnderY', 115.9, 'Tab underside (Y)'),
    ('MountBackGap', 0.3, 'Tab bar to the back panel (the panel comes off on its own)'),
    ('ArmH', 8.0, 'Tab bar height under the tab'),
    ('ArmX1', -5.0, 'Tab bar front face (X): nothing of the board but the tab is behind -5'),
    ('TabBarScrewY', '=YBotIn + ExtW + RailLY - BraceScrewUp', 'Tab bar end screws (Y): 29 mm from the uprights\' top end'),
    ('TabBarEndY0', '=TabBarScrewY - 6', 'Tab bar end blocks: down to here, round the end screws'),
    # --- panels

    # hex deboss pattern on the front panel's outer face (the panels print on their outer face, so the
    # grooves print upside down: their 45 deg walls need no supports)
    ('HexP', 35.3356, 'Pattern cell size across flats'),
    ('GrooveW', 1.6, 'Pattern V-groove width'), ('GrooveD', '=GrooveW / 2', 'Pattern V-groove depth (45 deg walls)'),
    ('PatternClear', 2.0, 'Grooves stop short of openings, countersinks, feet and the edge chamfers by this'),
    ('PatternMinRun', 5.0, 'Groove pieces left shorter than this by the masking are dropped'),
    ('ButtonBezelD', 19.0, 'Power button: its bezel and nut keep the grooves clear'),
    ('SeamGrooveW', 1.0, 'V-groove in the outer face over a split, so the joint line is not seen'),
    ('MitreGap', 0.3, 'Gap between the mitres of neighbouring panels (each bevel set back half, square to it)'),
    ('SplitGap', 0.3, 'Gap between the pieces of a split panel (in the V-groove)'),
    ('CsinkD', 6.9, 'M3 countersink diameter at the surface (ISO 10642 head: 6.72 max)'), ('CsinkA', 90.0, ''),
    ('CsinkRun', 0.1, 'Cone runs this far (radially) into the hole, so it leaves no ledge'),
    ('ClearD', 3.4, 'M3 clearance'), ('BedChamfer', 0.5, 'Chamfer on edges touching the print bed'),
    ('PullFanX', 79.55, 'Pull fan centre (X)'), ('PushFanX', 263.0, 'Push fan centre (X)'),
    ('RearFanX', 168.775, 'Backplate fan centre (X)'), ('FanY', 60.75, 'Fan centres (Y)'),
    ('FanHoleSpacing', 105.0, ''), ('FanScrewD', 3.6, 'Fan screw clearance'),
    # grills: hex holes through the panels. For the look, each panel's grills are symmetrical on it, not on the
    # fans behind them; a screw in a grill (the fan screws) stands in a small solid island
    ('GrillHole', 6.0, 'Grill hex hole size (across flats)'), ('GrillRib', 1.2, 'Grill rib width between hex holes'),
    ('PanelMidX', '=XBackIn + RailLX / 2', 'Side, top and bottom panels: centre (X)'),
    ('GrillDX', '=(PushFanX - PullFanX) / 2', 'Left panel grills and top vents: this far either side of the centre'),
    ('GrillMargin', 5.0, 'Grills: this far in from the rails under the panel'),
    ('GrillL', '=RailLX - 2 * (GrillDX + ExtW + GrillMargin)', 'Side grills (rounded rectangles): length (X)'),
    ('GrillW', '=RailLY - 2 * GrillMargin', '... height (Y): centred between the long rails'),
    ('GrillR', 15.0, '... corner radius'),
    ('PsuGrillR', 18.0, 'PSU fan grill radius (round the PSU fan)'),
    ('VentL', '=GrillL', 'Top grills (rounded rectangles, as the side grills): length (X), above the left ones'),
    ('VentW', '=RailLZ - 2 * GrillMargin', '... width (Z): between the long rails, as the side grills'),
    ('VentZ', '=(ZRightIn + ZLeftIn) / 2', 'Top grill centre (Z)'),
    ('SplitLX', '=PanelMidX', 'Left panel split (X): between its grills'),
    ('ScrewMaxGap', 100.0, 'Panel screws along a rail: at the piece corners and no further apart than this'),
    ('PanelScrewEdge', '=SlotC + PanelT - MitreGap / 2 * sqrt(2)', 'Panel screws: centre to the panel\'s outer edge (on '
                     'the rails\' slot centres). Every panel screw is this far from the edge of its piece'),
    ('SplitScrewOff', '=PanelScrewEdge + SplitGap / 2', 'Screws of the pieces either side of a split: this far from it'),
    ('CornerNutY', 25.5, 'Front and back panel corner screws: this far from the top and bottom (in the uprights) or '
                         'the sides (in a cross rail): a T-nut no nearer the long rails (their ends have no slot)'),
    ('SplitTX', '=PanelMidX', 'Top panel split (X): between the vents'), ('SplitBX', 180.0, 'Bottom panel split (X): its splice strip clears the PSU mount'),
    ('SpliceScrewOff', '=SplitScrewOff', 'Splice screws from the split'),
    ('SpliceW', '=2 * (SpliceScrewOff + 5)', 'Splice strip width: 5 past the screws (the inserts)'),
    ('SpliceL', 14.0, 'Splice strip length (along the split): round its two screws, at the middle of the split'),
    ('SpliceInsertDepth', 4.5, 'Splice insert hole depth (M3x5x4)'),
    ('SpliceT', '=SpliceInsertDepth + 1', 'Splice strip thickness: the insert and a 1 mm shoulder'),
    ('SplitRX', '=PanelMidX - GrillL / 2 - GrillMargin - SpliceW / 2', 'Right panel splits (X): either side of its '
                'grill, with the splice strips clear of it (one split would leave a piece longer than the bed)'),
    ('SplitRX2', '=2 * PanelMidX - SplitRX', ''),
    ('InsertD', 4.4, 'Heat-set insert hole (M3x5x4)'), ('InsertDepth', 5.0, ''), ('ScrewD', 3.2, 'Screw hole past an insert'),
    # --- PSU screws and exhaust in the back panel
    ('PsuHoleY1', 4.1, '#6-32 holes on the AC face, above the PSU bottom'), ('PsuHoleY2', 36.1, ''),
    ('BackSplitY', '=PsuY0 + PsuHoleY2 + PsuHoleY1 + PanelT + SplitGap / 2',
     'Back panel split (Y): the PSU screws as far below it as above the bottom edge'),
    ('PsuHoleIn', 5.6, '... and in from its left side'), ('PsuScrewD', 3.8, '#6-32 clearance'),
    ('PsuCsinkD', 6.9, '#6-32 flat head countersink'), ('PsuCsinkA', 82.0, ''),
    ('PsuOpenInset', -0.5, 'Inlet opening bottom, from the PSU bottom (the C14 plate reaches the bottom edge)'),
    # AC face as measured: C14 inlet plate, and the 40 mm fan blowing out beside it
    ('PsuC14Z', 16.0, 'C14 inlet plate centre, in from the PSU side it is on'), ('PsuC14W', 31.0, 'Inlet opening width (the plate is about 26; its corner chamfers clear the plate)'),
    ('PsuC14H', 31.0, 'Inlet opening top, above the PSU bottom'),
    ('PsuFanZ', 58.7, 'PSU fan centre, in from the C14 side'), ('PsuFanY', 20.25, '... and above the PSU bottom'),
    ('IoY0', 4.0, 'I/O opening (the bracket plate is 4.5..117 x -1.3..26.5)'), ('IoY1', 107.0, ''),
    ('IoZ0', -2.0, ''), ('IoZ1', 27.5, ''), ('IoChamfer', 2.0, ''),
    # --- USB hub: a pocket in the front panel, a rib on its inner side, the front right upright on its outer
    # side, and a retainer behind it (screwed to the rib and, through a boss, into the upright's back slot)
    ('HubL', 108.0, ''), ('HubW', 31.0, 'Hub depth (port face to back)'), ('HubClear', 0.3, ''),
    ('HubPort1', 37.6, 'First port centre from the cable end'), ('HubPortPitch', 19.95, ''),
    ('HubSlotMargin', 9.0, 'Port opening past the outer port centres (plug overmolds)'),
    # --- USB hub cradle: a C-channel round the hub, screwed to the front right upright (its back slot); the
    # upright's inner face guides the hub's outer side. The back wall takes the push of a plug going in, the
    # front panel the pull of one coming out.
    ('HubBackX', '=HubFaceX - HubW - HubClear', 'Back face of the hub (the cradle\'s back wall)'),
    ('CradleBackT', 5.0, 'Cradle back wall thickness'), ('CradleWallT', 4.0, 'Cradle inner wall thickness (it takes no plug force)'),
    ('HubStopH', 4.0, 'Floor under the hub cable end'),
    ('HubCableX', '=HubFaceX - 17.5', 'Hub cable: its back side (X)'), ('HubCableD', 4.0, '... its diameter'),
    ('HubCableClear', 0.5, 'Cable slot in the floor: clearance each side'),
    ('HubTopStop', 4.0, 'Cap over the hub top end'),
    ('CradleScrewIn', 5.0, 'Cradle screws (FHCS M3x16): their tips this far into the upright'),
    ('CradleScrewInset', 8.0, 'Cradle screws from the hub ends'),
    ('CradleY1', '=HubY0 + CradleScrewInset', ''), ('CradleY2', '=HubY0 + HubL - CradleScrewInset', ''),
    ('CradleScrewZ', '=ZRightIn + SlotC', 'Cradle screws (Z): on the upright\'s back slot'),
    ('CradleChamfer', 2.0, 'Chamfer on the back wall\'s outer corner (the push shroud\'s middle clamp screw head is 2 mm past it)'),
    ('CradleCboreD', '=CsinkD', 'Counterbores for the cradle screw heads, ending in a countersink'),
    ('ButtonHoleD', 16.2, 'Power button panel hole (16 mm cutout)'),
    # --- screw-on TPU feet, into T-nuts in the bottom rails (standing) or the right rails (lying)
    ('FootD', 18.0, 'Foot diameter: inside the rail under it'), ('FootChamfer', 1.0, 'Foot ground edge chamfer'),
    ('FootShortH', 9.0, 'Standing foot height'), ('FootShortRecess', 2.5, 'Screw head below the ground face (FHCS M3x16)'),
    ('FootTallH', 15.0, 'Lying foot height: room for the backplate fan intake'), ('FootTallRecess', 8.5, ''),
    ('EdgeChamfer', 0.5, ''),
    # --- drill jig for the blind-joint access holes: a cap over a rail end, keyed into the slot of the face
    # to drill, with a guide bore on the slot centre line, ExtW / 2 from the end (on the joining rail's axis)
    ('JigHoleD', 5.0, 'Access hole: room for a 3 mm hex key (BHCS M5 head)'), ('JigBoreClear', 0.15, 'Guide bore clearance (each side)'),
    ('JigHoleX', '=ExtW / 2', 'Access hole from the rail end'),
    ('JigGuideT', 10.0, 'Guide plate thickness (bore length)'), ('JigWallT', 4.0, ''), ('JigWallH', 14.0, 'Side walls down the rail'),
    ('JigHole2D', '=ClearD', 'Second bore: the back brace screw hole through the back uprights'),
    ('JigHole2X', '=BraceScrewUp', '... from the upright end'),
    ('JigClear', 0.2, 'Jig to rail clearance (each side)'), ('JigL', 40.0, 'Jig length along the rail, from the end stop'),
]


def profile_2020():
    """2020 cross-section (simplified): 20 x 20 with four T-slots (6.2 opening, 1.8 lip, cavity 11 wide
    under the lip narrowing to 7.3 at the core) and the 4.2 centre bore (tapped M5 at the ends)."""
    face = Part.Face(Part.makePolygon([V(-10, -10, 0), V(10, -10, 0), V(10, 10, 0), V(-10, 10, 0), V(-10, -10, 0)]))
    cut = []
    for a in (0, 90, 180, 270):
        pts = [(-3.1, 10.1), (3.1, 10.1), (3.1, 8.2), (5.5, 8.2), (3.65, 3.9), (-3.65, 3.9), (-5.5, 8.2), (-3.1, 8.2)]
        w = Part.makePolygon([V(x, y, 0) for x, y in pts] + [V(*pts[0], 0)])
        f = Part.Face(w)
        f.rotate(V(0, 0, 0), V(0, 0, 1), a)
        cut.append(f)
    cut.append(Part.Face(Part.Wire(Part.makeCircle(2.1))))
    for c in cut:
        face = face.cut(c)
    return face


def rail(doc, name, length):
    """A 2020 rail along +X from 0 to length, centred on Y/Z."""
    f = profile_2020()
    f.rotate(V(0, 0, 0), V(0, 1, 0), 90)  # profile plane -> YZ
    o = doc.addObject('Part::Feature', name)
    o.Shape = f.extrude(V(length, 0, 0))
    o.Label = f'2020 extrusion {length:g} mm'
    return o


def bhcs_m5(doc, length):
    """M5 button head (ISO 7380: head 9.5 x 2.75, 3 mm hex): bearing face at z=0, shank to -length."""
    head = Part.makeCylinder(4.75, 0.6).fuse(Part.makeCone(4.75, 2.6, 2.15, V(0, 0, 0.6)))
    r = 1.5 / math.cos(math.radians(30))
    hexw = Part.makePolygon([V(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0.9) for a in range(0, 361, 60)])
    s = head.cut(Part.Face(hexw).extrude(V(0, 0, 2))).fuse(Part.makeCylinder(2.5, length, V(0, 0, -length))).removeSplitter()
    o = doc.addObject('Part::Feature', f'BHCS_M5x{length}')
    o.Shape = s
    return o


def tnut_m3(doc):
    """M3 drop-in T-nut for a 2020 slot: top face at z=0 (under the lip), body to -4, along x."""
    s = Part.makeBox(10, 6, 4, V(-5, -3, -4)).cut(Part.makeCylinder(1.25, 4, V(0, 0, -4)))
    o = doc.addObject('Part::Feature', 'TNut_M3')
    o.Shape = s
    return o


def fillet(body, P, name, radius, pred, count=None):
    """PartDesign fillet on every edge of the current tip that satisfies pred(edge) (count: how many there must be)."""
    body.Document.recompute()
    prev = body.Tip
    names = [f'Edge{i}' for i, e in enumerate(prev.Shape.Edges, start=1) if pred(e)]
    assert count is None or len(names) == count, (name, names)
    f = body.newObject('PartDesign::Fillet', name)
    f.Base = (prev, names)
    f.Radius = P.py(radius)
    f.setExpression('Radius', P.fc(radius))
    prev.Visibility = False
    return f


def build_brace(doc, P):
    """Back brace, in print orientation lying on its back x length face: local x along it (case Z, from the
    right upright), y its depth (case X, from the back panel), z its height (case Y, from its underside).
    End screws run along x through teardrop holes (point up, +z) into T-nuts in the uprights."""
    body = doc.addObject('PartDesign::Body', 'BackBrace')
    s = SK(body, P, 'BraceSketch', 'XY_Plane')
    s.rect('0', 'BraceL', '0', 'BraceD')
    feat(body, P, 'Pad', 'Brace', s, 'BraceH')
    s = SK(body, P, 'BraceWindowSketch', 'XY_Plane')
    for x0 in ('BraceEndT', 'BraceL - BraceEndT - BraceWinL'):
        s.rect(x0, f'{x0} + BraceWinL', 'BraceScrewY - BraceWinW / 2', 'BraceScrewY + BraceWinW / 2')
    feat(body, P, 'Pocket', 'BraceWindows', s, 'BraceH', Reversed=True)
    # slot bumps on the end faces, up the back uprights' inner slots (the brace goes in as the frame is
    # built): they locate it
    R, H, a = bump_section(P, P['BraceClear'])
    sy, L = P['BraceScrewY'], P['BraceL']
    for i, (x, sg) in enumerate(((0.0, -1), (L, 1)), start=1):
        s = SK(body, P, f'BraceBump{i}Sketch', 'XY_Plane')
        cx, phi = x + sg * (H - R), math.degrees(math.asin(a / R))
        th = 0 if sg > 0 else 180
        A = s.arc((cx, sy), R, th - phi, th + phi)
        e0, e1 = (x, sy - a), (x, sy + a)
        Ln = s.line(e1, e0) if sg > 0 else s.line(e0, e1)
        s.co(Ln, 2, A, 1); s.co(Ln, 1, A, 2)
        s.px(A, 3, repr(cx)); s.py(A, 3, repr(sy)); s.dim('Radius', A, expr=repr(R))
        s.px(Ln, 1, repr(x)); s.px(Ln, 2, repr(x))
        feat(body, P, 'Pad', f'BraceBump{i}', s, 'BraceH')
    # the end screws come from outside the uprights into inserts pressed into the end walls from the windows
    # (the screw pulls them against the wall)
    for i, (x, d) in enumerate((('BraceEndT', '-'), ('BraceL - BraceEndT', '+')), start=1):
        s = SK(body, P, f'BraceInsert{i}Sketch', 'YZ_Plane', x)
        teardrop(s, 'BraceScrewY', 'BraceScrewZ', 'InsertD', '+v')
        cut_through(body, P, f'BraceInsert{i}', s, '2 * InsertDepth')
        s = SK(body, P, f'BraceHole{i}Sketch', 'YZ_Plane', x)
        teardrop(s, 'BraceScrewY', 'BraceScrewZ', 'ScrewD', '+v')
        cut_through(body, P, f'BraceHole{i}', s, '2 * (BraceEndT + BraceClear + SlotBumpH + 1)')
    # ridge with a slot for the bottom of the I/O bracket: a wall behind it, and a wall in front of it that
    # runs out past the brace front over a 45 deg underside (local: y = case X - XBackIn, z = case Y - BraceY0)
    yb0 = 'IoBackX - BraceSlotClear - BraceRidgeBackT - XBackIn'
    yb1 = 'IoBackX - BraceSlotClear - XBackIn'
    yf0 = 'IoFrontX + BraceSlotClear - XBackIn'
    yf1 = 'BraceRidgeFrontX - XBackIn'
    top, c = 'IoBotY + BraceSlotUp - BraceY0', 'BraceSlotLead'
    s = SK(body, P, 'BraceRidgeSketch', 'YZ_Plane', 'BraceRidgeZ0 - ZRightIn - ExtW - BraceClear')
    s.polygon([(yb0, 'BraceH'), (yb1, 'BraceH'), (yb1, f'{top} - {c}'), (f'{yb1} - {c}', top), (yb0, top)])
    s.polygon([(yf0, 'BraceH'), ('BraceD', f'BraceH - ({yf1} - BraceD)'), (yf1, 'BraceH'), (yf1, top),
               (f'{yf0} + {c}', top), (yf0, f'{top} - {c}')])
    feat(body, P, 'Pad', 'BraceRidge', s, 'BracketZ1 + 1 - BraceRidgeZ0')
    # fillet at the root of the back wall (the bracket levers on it): a cove that faces up as it prints
    yv, zv = P.py(yb0), P.py('BraceH')
    fillet(body, P, 'BraceRidgeFillet', 'BraceRidgeFillet', lambda e: e.BoundBox.YLength < 1e-6 and
           e.BoundBox.ZLength < 1e-6 and abs(e.BoundBox.YMin - yv) < 1e-6 and abs(e.BoundBox.ZMin - zv) < 1e-6, count=1)
    chamfer(body, P, 'BedChamfer', 'BedChamfer', at_z(0))
    return body


# ------------------------------------------------------------------ panels (Part solids in the board frame)
AX = {'X': 0, 'Y': 1, 'Z': 2}


class Panel:
    """A plate on one frame face. axis: its normal; inner: the inner face coordinate (the frame face);
    inward: +1/-1, the direction into the case; u, v: the board coordinates of the other two axes (in X,
    Y, Z order). Features are cut from or fused to self.shape; self.fixings collects the screws."""
    def __init__(self, P, name, axis, inner, inward, urange, vrange, splits=(), pointy_u=True):
        self.P, self.name, self.ax, self.s = P, name, AX[axis], inward
        self.pointy_u = pointy_u  # pattern hexagons point along u (else along v)
        self.keep = []  # pattern keepouts: functions (u, v) -> distance outside the feature
        self.bed = []  # openings in the outer (bed) face that get a bed chamfer: (u, v) -> distance to the outline
        self.T = P['PanelT']
        self.o = inner - inward * self.T
        self.ua, self.va = [i for i in range(3) if i != self.ax]
        self.u0, self.u1 = urange
        self.v0, self.v1 = vrange
        self.splits = list(splits)
        self.n_in = self.vec({self.ax: inward})
        self.n_out = self.vec({self.ax: -inward})
        self.shape = self.plate()
        self.fixings = []

    def vec(self, d):
        c = [0.0, 0.0, 0.0]
        for k, x in d.items():
            c[k] = x
        return V(*c)

    def pt(self, u, v, d=0.0):
        """Board point at (u, v), d in from the outer face."""
        return self.vec({self.ua: u, self.va: v, self.ax: self.o + self.s * d})

    def plate(self):
        """The frame face (inner face) grown by T all round on the outer face: 45 deg mitres all round, each set
        back MitreGap / 2 square to itself (so the inner face is that much times sqrt 2 inside the frame face)."""
        T = self.T
        k = self.P['MitreGap'] / 2 * math.sqrt(2)
        rect = lambda d, m: Part.makePolygon([self.pt(self.u0 - m, self.v0 - m, d), self.pt(self.u1 + m, self.v0 - m, d),
                                              self.pt(self.u1 + m, self.v1 + m, d), self.pt(self.u0 - m, self.v1 + m, d),
                                              self.pt(self.u0 - m, self.v0 - m, d)])
        sh = Part.makeLoft([rect(0, T - k), rect(T, -k)], True, True)
        sh = sh if sh.Volume > 0 else sh.reversed()
        # bed chamfer on the outer face's edges: no knife edge on the bed (elephant's foot)
        es = [e for e in sh.Edges if all(abs(vx.Point[self.ax] - self.o) < 1e-6 for vx in e.Vertexes)]
        return sh.makeChamfer(self.P['BedChamfer'], es)

    def hole(self, u, v, d, depth=None, at=None):
        """Cylinder along the panel normal: through the panel, or depth long from d = at."""
        if depth is None:
            depth, at = self.T + self.P['SlotBumpH'] + 2, -1.0  # through any slot bump too
        return Part.makeCylinder(d / 2, depth, self.pt(u, v, at), self.n_in)

    def csink(self, u, v, hole, d, angle):
        k = (d / 2 - hole / 2 + self.P['CsinkRun']) / math.tan(math.radians(angle / 2))
        return Part.makeCone(d / 2, hole / 2 - self.P['CsinkRun'], k, self.pt(u, v, 0), self.n_in)

    def prism(self, pts, d0=-1.0, d1=None):
        """Cutter from a (u, v) outline, from d0 to d1 in from the outer face (default: through)."""
        d1 = self.T + 1 if d1 is None else d1
        w = Part.makePolygon([self.pt(u, v, d0) for u, v in pts] + [self.pt(*pts[0], d0)])
        return Part.Face(w).extrude(self.n_in * (d1 - d0))

    def box(self, u0, u1, v0, v1, d0, d1):
        return self.prism([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], d0, d1)

    def cut(self, *tools):
        self.shape = self.shape.cut(list(tools) if len(tools) > 1 else tools[0])

    def add(self, *solids):
        self.shape = self.shape.fuse(list(solids)).removeSplitter()

    def screw(self, kind, u, v, rail, csink=True):
        """Panel screw (or foot screw) into a T-nut in the rail slot under (u, v); rail: the rail's axis."""
        self.cut(self.hole(u, v, self.P['ClearD']))
        if csink:
            self.cut(self.csink(u, v, self.P['ClearD'], self.P['CsinkD'], self.P['CsinkA']))
        self.keep_circle(u, v, (self.P['CsinkD'] if csink else self.P['FootD']) / 2)
        self.fix(kind, u, v, rail=rail)

    def bed_circle(self, cu, cv, r):
        self.bed.append(lambda u, v: abs(math.hypot(u - cu, v - cv) - r))

    def bed_poly(self, pts):
        self.bed.append(lambda u, v: min(seg_dist((u, v), a, b) for a, b in zip(pts, pts[1:] + pts[:1])))

    def bed_chamfer(self):
        """BedChamfer round the registered openings, on the outer (bed) face."""
        es = []
        for e in self.shape.Edges:
            if not all(abs(vx.Point[self.ax] - self.o) < 1e-6 for vx in e.Vertexes):
                continue
            m = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
            if any(f(m[self.ua], m[self.va]) < 1e-3 for f in self.bed):
                es.append(e)
        if es:
            self.shape = self.shape.makeChamfer(self.P['BedChamfer'], es)
        print(f'  {self.name}: bed chamfer on {len(es)} opening edges, valid={self.shape.isValid()}')

    def keep_circle(self, cu, cv, r):
        self.keep.append(lambda u, v: math.hypot(u - cu, v - cv) - r)

    def keep_poly(self, pts):
        def d(u, v):
            inside = False
            for (a, b), (c, e) in zip(pts, pts[1:] + pts[:1]):
                if (b > v) != (e > v) and u < a + (v - b) * (c - a) / (e - b):
                    inside = not inside
            return 0.0 if inside else min(seg_dist((u, v), a, b) for a, b in zip(pts, pts[1:] + pts[:1]))
        self.keep.append(d)

    def pattern(self):
        """Hex V-groove lattice on the outer face, centred on it, masked by the keepouts and the edges."""
        P = self.P
        p = P['HexP']
        t = p / 2 / math.cos(math.radians(30))
        clear = P['PatternClear'] + P['GrooveW'] / 2
        m = clear + 1 - self.T  # from the frame face edges: 1 + clear in from the outer face edges
        uc, vc = (self.u0 + self.u1) / 2, (self.v0 + self.v1) / 2

        def ok(u, v):
            return (self.u0 + m <= u <= self.u1 - m and self.v0 + m <= v <= self.v1 - m
                    and all(k(u, v) >= clear for k in self.keep))
        ha, hb = ((self.u1 - self.u0) / 2 + self.T, (self.v1 - self.v0) / 2 + self.T)
        if not self.pointy_u:
            ha, hb = hb, ha
        uv = (lambda a, b: (uc + a, vc + b)) if self.pointy_u else (lambda a, b: (uc + b, vc + a))
        segs = {}
        for j in range(-math.ceil(ha / (1.5 * t)) - 1, math.ceil(ha / (1.5 * t)) + 2):
            for k in range(-math.ceil(hb / p) - 1, math.ceil(hb / p) + 2):
                a, b = 1.5 * t * j, (j % 2) * p / 2 + k * p
                hx = [(a + t, b), (a + t / 2, b + p / 2), (a - t / 2, b + p / 2), (a - t, b), (a - t / 2, b - p / 2), (a + t / 2, b - p / 2)]
                hx = [uv(*q) for q in hx]
                for q, r in zip(hx, hx[1:] + hx[:1]):
                    segs[tuple(sorted((tuple(round(x, 4) for x in q), tuple(round(x, 4) for x in r))))] = (q, r)
        gs = []
        for (ua, va), (ub, vb) in segs.values():
            L = math.hypot(ub - ua, vb - va)
            for t0, t1 in mask(lambda f: ok(ua + (ub - ua) * f, va + (vb - va) * f), L):
                if (t1 - t0) * L >= min(P['PatternMinRun'], 0.99 * L):
                    gs.append(vgroove(P, self.pt(ua + (ub - ua) * t0, va + (vb - va) * t0),
                                         self.pt(ua + (ub - ua) * t1, va + (vb - va) * t1), self.n_out, False, False))
        print(f'  {self.name}: hex pattern {len(gs)} grooves')
        if gs:  # one cutter (cutting with the loose solids goes wrong)
            cutter = gs[0].fuse(gs[1:]).removeSplitter() if len(gs) > 1 else gs[0]
            if not cutter.isValid():
                cutter.fix(1e-7, 1e-7, 1e-7)
            assert cutter.isValid(), f'{self.name}: pattern cutter is not a valid solid'
            before = self.shape.Volume
            self.shape = self.shape.cut(cutter)
            want = sum(c.common(self.plate()).Volume for c in cutter.Solids)
            print(f'  {self.name}: pattern removed {before - self.shape.Volume:.0f} of about {want:.0f} mm3 '
                  f'valid={self.shape.isValid()} solids={len(self.shape.Solids)}')

    def fix(self, kind, u, v, **kw):
        p = self.pt(u, v, 0)
        self.fixings.append(dict(kind=kind, panel=self.name, p=[p.x, p.y, p.z], n=list(self.n_out), **kw))


def vgroove(P, pa, pb, n, cut_a, cut_b):
    """45 deg V-groove (GrooveW wide, GrooveD deep) along pa -> pb, in a surface with outward normal n; cut_a,
    cut_b: run on past that end at full depth (out through an edge); otherwise the end wall is 45 deg too."""
    d = pb - pa
    d.normalize()
    lv = d.cross(n)
    hw, depth, over = P['GrooveW'] / 2, P['GrooveD'], 1.0

    def end(p, sg, cut):  # bottom point, top corners (+lv, -lv)
        t = p + d * (sg * (P['GrooveW'] + 1 if cut else depth + over))
        b = (t if cut else p) - n * depth
        return b, t + lv * (hw + over) + n * over, t - lv * (hw + over) + n * over
    b0, p0, m0 = end(pa, -1, cut_a)
    b1, p1, m1 = end(pb, 1, cut_b)
    poly = lambda *q: Part.Face(Part.makePolygon(list(q) + [q[0]]))
    solid = Part.Solid(Part.Shell([poly(p0, p1, m1, m0), poly(b0, b1, p1, p0), poly(b0, m0, m1, b1),
                                   poly(b0, p0, m0), poly(b1, m1, p1)]))
    if solid.Volume < 0:
        solid.reverse()
    return solid


def mask(ok, length, step=0.5):
    """Parameter spans [t0, t1] of a segment where ok(t) holds, ends refined by bisection."""
    n = max(2, math.ceil(length / step))
    ts = [k / n for k in range(n + 1)]
    vals = [ok(t) for t in ts]

    def edge(t_in, t_out):
        for _ in range(10):
            m = (t_in + t_out) / 2
            t_in, t_out = (m, t_out) if ok(m) else (t_in, m)
        return t_in
    spans, start = [], None
    for k, v in enumerate(vals):
        if v and start is None:
            start = 0.0 if k == 0 else edge(ts[k], ts[k - 1])
        if not v and start is not None:
            spans.append((start, edge(ts[k - 1], ts[k])))
            start = None
    if start is not None:
        spans.append((start, 1.0))
    return spans


def octagon_pts(u0, u1, v0, v1, c):
    return [(u0 + c, v0), (u1 - c, v0), (u1, v0 + c), (u1, v1 - c), (u1 - c, v1), (u0 + c, v1), (u0, v1 - c), (u0, v0 + c)]


def hex_field(P, cu, cv, inside):
    """Hex holes (pointy along u) on a grill lattice centred on (cu, cv), kept where inside(u, v, r) says that
    a circle of radius r round the hole at (u, v) is clear. The lattice is symmetrical about the centre."""
    f, p = P['GrillHole'], P['GrillHole'] + P['GrillRib']
    R = f / 2 / math.cos(math.radians(30))
    du = p * math.cos(math.radians(30))
    out = []
    for i in range(-60, 61):
        for j in range(-60, 61):
            u, v = cu + i * du, cv + j * p + (i % 2) * p / 2
            if inside(u, v, R):
                out.append([(u + R * math.cos(math.radians(a)), v + R * math.sin(math.radians(a))) for a in range(0, 360, 60)])
    return out


def outline_dist(shape):
    """(u, v) -> distance outside the outline (negative inside): ('circle', cu, cv, r), or ('rrect', cu, cv, L, W,
    r): L along u, W along v, corner radius r (a pill when r = W / 2)."""
    if shape[0] == 'circle':
        _, cu, cv, r = shape
        return lambda u, v: math.hypot(u - cu, v - cv) - r
    _, cu, cv, L, W, r = shape

    def d(u, v):
        qu, qv = abs(u - cu) - (L / 2 - r), abs(v - cv) - (W / 2 - r)
        return math.hypot(max(qu, 0), max(qv, 0)) + min(max(qu, qv), 0) - r
    return d


def add_grill(pn, shape):
    """Hex holes through the panel, inside the outline shape, and none nearer than GrillRib to a keepout (a
    screw countersink): a screw in the grill stands in a small solid island."""
    P = pn.P
    dist, rib = outline_dist(shape), P['GrillRib']
    keep = list(pn.keep)
    holes = hex_field(P, shape[1], shape[2],
                      lambda u, v, r: dist(u, v) + r <= 0 and all(k(u, v) >= r + rib for k in keep))
    if holes:
        pn.cut(*[pn.prism(h) for h in holes])
    pn.keep.append(dist)
    print(f'  {pn.name}: grill {shape[0]} at ({shape[1]:.1f}, {shape[2]:.1f}): {len(holes)} holes')


def seam_groove(pn, u):
    """45 deg V-groove in the outer face along v at u."""
    w = pn.P['SeamGrooveW']
    v = pn.v0 - pn.T - 1
    tri = Part.Face(Part.makePolygon([pn.pt(u - w / 2 - 0.5, v, -0.5), pn.pt(u + w / 2 + 0.5, v, -0.5),
                                      pn.pt(u, v, w / 2), pn.pt(u - w / 2 - 0.5, v, -0.5)]))
    return tri.extrude(pn.vec({pn.va: pn.v1 - pn.v0 + 2 * pn.T + 2}))


def splice(pn, P, u, v):
    """Short strip behind a split, on the panel's inner face at the middle of the split: an FHCS M3x10 through
    each piece into an insert pressed in from the strip's far face (the screw pulls it against the shoulder).
    The rail screws hold the ends of the split."""
    T, t, w, L, di = P['PanelT'], P['SpliceT'], P['SpliceW'], P['SpliceL'], P['SpliceInsertDepth']
    strip = pn.box(u - w / 2, u + w / 2, v - L / 2, v + L / 2, T, T + t)
    for du in (-P['SpliceScrewOff'], P['SpliceScrewOff']):
        pn.cut(pn.hole(u + du, v, P['ClearD']), pn.csink(u + du, v, P['ClearD'], P['CsinkD'], P['CsinkA']))
        pn.keep_circle(u + du, v, P['CsinkD'] / 2)
        pn.fix('splice', u + du, v, far=T + t)
        strip = strip.cut([pn.hole(u + du, v, P['InsertD'], di + 1, T + t - di),
                           pn.hole(u + du, v, P['ScrewD'], t + 2, T - 1)])
    far, near = pn.o + pn.s * (T + t), pn.o + pn.s * T  # near: against the panel, on the bed when printed
    es = [e for e in strip.Edges if any(all(abs(vx.Point[pn.ax] - f) < 1e-6 for vx in e.Vertexes) for f in (far, near))
          and not isinstance(e.Curve, Part.Circle)]
    return strip.makeChamfer(P['EdgeChamfer'], es)


def teardrop_prism(c, axis, up, d, length):
    """Hole of diameter d along axis, centred on c, pointed toward up (prints without support when up is up)."""
    r = d / 2
    q = r * math.cos(math.radians(45))
    arc = Part.ArcOfCircle(Part.Circle(V(), V(0, 0, 1), r), math.radians(135), math.radians(405)).toShape()
    tip = V(0, r * math.sqrt(2), 0)
    f = Part.Face(Part.Wire([arc, Part.makeLine(V(q, q, 0), tip), Part.makeLine(tip, V(-q, q, 0))]))
    sol = f.extrude(V(0, 0, length))
    sol.translate(V(0, 0, -length / 2))
    xd = up.cross(axis)
    sol = sol.transformGeometry(App.Matrix(xd.x, up.x, axis.x, 0, xd.y, up.y, axis.y, 0, xd.z, up.z, axis.z, 0))
    sol.translate(c)
    return sol


def bump_section(P, gap=0.0):
    """Slot bump section: (R, H, a): arc radius, height above the part's face, and half-width at that face. The
    arc is SlotBumpW wide at the rail face (gap past the part's face) and SlotBumpH past it."""
    w, h = P['SlotBumpW'] / 2, P['SlotBumpH']
    R = (w * w + h * h) / (2 * h)
    H = gap + h
    return R, H, math.sqrt(R * R - (R - H) ** 2)


def slot_bump(P, start, along, length, out, side, gap=0.0, taper=(False, False)):
    """Slot bump on a part's face: from start (on the slot centre line, on the part's face) along the unit vector
    along for length; out: the face normal (into the slot); side: across the slot. gap: the part's face to the
    rail face. taper: (start, end) ends that run out at 45 deg (no flat end face; for an end that prints facing
    down)."""
    R, H, a = bump_section(P, gap)
    pt = lambda u, v: start + side * u + out * v
    f = Part.Face(Part.Wire([Part.Arc(pt(-a, 0), pt(0, H), pt(a, 0)).toShape(), Part.makeLine(pt(a, 0), pt(-a, 0))]))
    sol = f.extrude(along * length)
    for i, on in enumerate(taper):
        if on:
            e = start + along * (length if i else 0)
            d = -along if i else along  # into the bump from that end
            q = lambda t, v: e + d * t + out * v - side * (a + 1)
            tri = Part.Face(Part.makePolygon([q(-1, -1), q(H + 1, H + 1), q(-1, H + 1), q(-1, -1)]))
            sol = sol.cut(tri.extrude(side * (2 * a + 2)))
    return sol


def build_panels(P):
    """All panels, in the board frame. Returns {piece: shape}, {other part: shape}, and the fixings."""
    g = P.__getitem__
    xb, xf, yb, yt, zr, zl = g('XBackIn'), g('XFrontIn'), g('YBotIn'), g('YTopIn'), g('ZRightIn'), g('ZLeftIn')
    c, w = g('SlotC'), g('ExtW')
    mid_y, mid_z = (yb + yt) / 2, (zr + zl) / 2
    extra, grills = {}, {}

    def rail_screws(pn):
        """Screws along the long rails: at both ends of each piece (the frame ends: on the slot centre of the
        upright or cross rail there; at a split: SplitScrewOff from it), and between, at most ScrewMaxGap
        apart. Returns the screw positions per piece."""
        ends = [xb + c] + [x for sp in pn.splits for x in (sp - g('SplitScrewOff'), sp + g('SplitScrewOff'))] + [xf - c]
        pieces = []
        for a, b in zip(ends[::2], ends[1::2]):
            n = math.ceil((b - a) / g('ScrewMaxGap') - 1e-9)
            pieces.append([a + k * (b - a) / n for k in range(n + 1)])
        return pieces

    e = g('SlotBumpEnd')
    side_runs = [('u', yb + c, xb + e, xf - e), ('u', yt - c, xb + e, xf - e),        # long rails
                 ('v', xb + c, yb + w + e, yt - w - e), ('v', xf - c, yb + w + e, yt - w - e)]  # uprights

    def bumps(pn, runs):
        """Slot bumps on the inner face, along each rail slot under it: (along 'u' or 'v', at, from, to)."""
        sols = []
        for along, at, a0, a1 in runs:
            u, v = (pn.ua, pn.va) if along == 'u' else (pn.va, pn.ua)
            start = pn.pt(a0, at, pn.T) if along == 'u' else pn.pt(at, a0, pn.T)
            sols.append(slot_bump(P, start, pn.vec({u: 1}), a1 - a0, pn.n_in, pn.vec({v: 1})))
        pn.add(*sols)

    def splices(pn, v):
        for i, sp in enumerate(pn.splits, start=1):
            name = pn.name.replace('Panel', 'Splice') + ('' if i == 1 else str(i))
            extra[name] = splice(pn, P, sp, v)

    # side grills: rounded rectangles between the long rails, the left two either side of the centre, the right
    # one on it (the grills are cut last, round all the screws)
    side_grill = lambda x: ('rrect', x, mid_y, g('GrillL'), g('GrillW'), g('GrillR'))
    L = Panel(P, 'PanelLeft', 'Z', zl, -1, (xb, xf), (yb, yt), [g('SplitLX')])  # push and pull fans
    bumps(L, side_runs)
    grills['L'] = [side_grill(g('PanelMidX') - g('GrillDX')), side_grill(g('PanelMidX') + g('GrillDX'))]
    for fx in (g('PullFanX'), g('PushFanX')):
        for sx in (1, -1):
            for sy in (1, -1):
                u, v = fx + sx * g('FanHoleSpacing') / 2, g('FanY') + sy * g('FanHoleSpacing') / 2
                L.cut(L.hole(u, v, g('FanScrewD')), L.csink(u, v, g('FanScrewD'), g('CsinkD'), g('CsinkA')))
                L.keep_circle(u, v, g('CsinkD') / 2)
    R = Panel(P, 'PanelRight', 'Z', zr, 1, (xb, xf), (yb, yt), [g('SplitRX'), g('SplitRX2')])  # backplate fan intake
    bumps(R, side_runs)
    grills['R'] = [side_grill(g('PanelMidX'))]  # backplate fan intake
    for pn in (L, R):
        pieces = rail_screws(pn)
        for x in (x for pc in pieces for x in pc):
            for y in (yb + c, yt - c):
                pn.screw('panel', x, y, 'X')
        for x in (xb + c, xf - c):  # up the uprights
            pn.screw('panel', x, mid_y, 'Y')
        splices(pn, mid_y)
        if pn is R:  # feet for lying on the right side: between the first two and the last two screws
            for x in ((pieces[0][0] + pieces[0][1]) / 2, (pieces[-1][-2] + pieces[-1][-1]) / 2):
                for y in (yb + c, yt - c):
                    R.screw('foot_tall', x, y, 'X', csink=False)

    T = Panel(P, 'PanelTop', 'Y', yt, -1, (xb, xf), (zr, zl), [g('SplitTX')])  # vents
    long_runs = [('u', zr + c, xb + e, xf - e), ('u', zl - c, xb + e, xf - e)]
    cross = lambda x: ('v', x, zr + w + e, zl - w - e)
    bumps(T, long_runs + [cross(xb + c), cross(xf - c)])  # both top cross rails
    grills['T'] = [('rrect', g('PanelMidX') + s * g('GrillDX'), g('VentZ'), g('VentL'), g('VentW'), g('GrillR'))
                   for s in (-1, 1)]
    B = Panel(P, 'PanelBottom', 'Y', yb, 1, (xb, xf), (zr, zl), [g('SplitBX')])  # feet for standing
    bumps(B, long_runs + [cross(xf - c)])  # the bottom front cross rail (the back one is the printed brace)
    for pn in (T, B):
        pieces = rail_screws(pn)
        for x in (x for pc in pieces for x in pc):
            for z in (zr + c, zl - c):
                pn.screw('panel', x, z, 'X')
        pn.screw('panel', xf - c, mid_z, 'Z')  # the front cross rail
        if pn is T:
            pn.screw('panel', xb + c, mid_z, 'Z')  # the top back cross rail (the bottom one is a printed brace)
        splices(pn, mid_z)
        if pn is B:
            for x in ((pieces[0][0] + pieces[0][1]) / 2, (pieces[-1][-2] + pieces[-1][-1]) / 2):
                for z in (zr + c, zl - c):
                    B.screw('foot_short', x, z, 'X', csink=False)

    # back: split just above the PSU. The bottom piece carries the PSU's rear screws and stays on; the top piece
    # (the I/O opening) comes off on its own
    K = Panel(P, 'PanelBack', 'X', xb, 1, (yb, yt), (zr, zl), [g('BackSplitY')], pointy_u=False)
    upright_runs = [('u', zr + c, yb + w + e, yt - w - e), ('u', zl - c, yb + w + e, yt - w - e)]
    bumps(K, upright_runs + [('v', yt - c, zr + w + e, zl - w - e)])  # the top back cross rail
    py0, pz0, pz1 = g('PsuY0'), g('PsuZ0'), g('PsuZ0') + g('PsuW')
    grills['K'] = [('circle', py0 + g('PsuFanY'), pz0 + g('PsuFanZ'), g('PsuGrillR'))]  # PSU fan
    for o in (octagon_pts(g('IoY0'), g('IoY1'), g('IoZ0'), g('IoZ1'), g('IoChamfer')),
              octagon_pts(py0 + g('PsuOpenInset'), py0 + g('PsuC14H'), pz0 + g('PsuC14Z') - g('PsuC14W') / 2,
                          pz0 + g('PsuC14Z') + g('PsuC14W') / 2, g('IoChamfer'))):
        K.cut(K.prism(o))
        K.keep_poly(o)
        K.bed_poly(o)
    for y in (g('PsuHoleY1'), g('PsuHoleY2')):
        u, v = py0 + y, pz1 - g('PsuHoleIn')
        K.cut(K.hole(u, v, g('PsuScrewD')), K.csink(u, v, g('PsuScrewD'), g('PsuCsinkD'), g('PsuCsinkA')))
        K.keep_circle(u, v, g('PsuCsinkD') / 2)
        K.fix('psu', u, v)
    for z in (zr + g('CornerNutY'), zl - g('CornerNutY')):  # top piece's top corners: the top back cross rail
        K.screw('panel', yt - c, z, 'Z')
    ks = K.splits[0]
    # in the uprights: the bottom piece one each side, as low as a T-nut goes (its middle is in the long rail's
    # end); the top piece at its bottom corners and in the middle
    for y in (yb + g('CornerNutY'), ks + g('SplitScrewOff'), mid_y):
        for z in (zr + c, zl - c):
            K.screw('panel', y, z, 'Y')

    F = Panel(P, 'PanelFront', 'X', xf, -1, (yb, yt), (zr, zl), pointy_u=False)  # USB hub port slot, power button
    bumps(F, upright_runs + [('v', y, zr + w + e, zl - w - e) for y in (yb + c, yt - c)])  # the front cross rails
    hz0, hz1 = g('HubZ') - g('HubT') / 2 - g('HubClear'), g('HubZ') + g('HubT') / 2 + g('HubClear')
    sy0 = g('HubY0') + g('HubPort1') - g('HubSlotMargin')
    sy1 = g('HubY0') + g('HubPort1') + 3 * g('HubPortPitch') + g('HubSlotMargin')
    F.cut(F.box(sy0, sy1, hz0, hz1, -1, g('PanelT') + 1))
    F.cut(F.hole(g('ButtonY'), g('ButtonZ'), g('ButtonHoleD')))
    F.keep_circle(g('ButtonY'), g('ButtonZ'), g('ButtonBezelD') / 2)
    F.bed_circle(g('ButtonY'), g('ButtonZ'), g('ButtonHoleD') / 2)
    F.bed_poly([(sy0, hz0), (sy1, hz0), (sy1, hz1), (sy0, hz1)])  # the port slot
    F.keep_poly([(sy0, hz0), (sy1, hz0), (sy1, hz1), (sy0, hz1)])
    for pn in (F,):  # corners and middle, in the uprights' slots
        for y in (yb + g('CornerNutY'), mid_y, yt - g('CornerNutY')):
            for z in (zr + c, zl - c):
                pn.screw('panel', y, z, 'Y')
    for y in (yb + c, yt - c):  # the front cross rails
        F.screw('panel', y, mid_z, 'Z')

    for k, pn in (('L', L), ('R', R), ('T', T), ('K', K)):
        for sh in grills[k]:
            add_grill(pn, sh)
    for pn in (L, R, T, B, K, F):
        pn.bed_chamfer()
        if pn is F:  # the hex pattern: the front panel only (the others have the grills)
            pn.pattern()
    # split the long panels: a V-groove over each split, then one piece each side
    panels = {}
    for pn in (L, R, T, B, K):
        for u in pn.splits:
            pn.cut(seam_groove(pn, u))
        cuts = [pn.u0 - pn.T - 1] + pn.splits + [pn.u1 + pn.T + 1]
        names = ('Bottom', 'Top') if pn is K else ('Back', 'Front') if len(pn.splits) == 1 else ('Back', 'Middle', 'Front')
        h = g('SplitGap') / 2
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            a, b = a + (h if i > 0 else 0), b - (h if i < len(pn.splits) else 0)
            keep = pn.box(a, b, pn.v0 - pn.T - 1, pn.v1 + pn.T + 1, -1, 3 * g('PanelT'))
            panels[pn.name + names[i]] = pn.shape.common(keep)
    panels[F.name] = F.shape
    return panels, extra, [f for pn in (L, R, T, B, K, F) for f in pn.fixings]


def build_hub_cradle(P):
    """USB hub cradle, in the board frame: a back wall behind the hub and an inner wall on its +Z side (a
    C-channel, the front right upright's inner face being the other side), with a block behind the upright
    that two FHCS M3x16 screw into T-nuts in its back slot (from counterbores: their countersinks print at 45 deg). A floor under the cable end (with a slot for the
    cable, open to the front) and a cap over the top end hold the hub along Y; the hub slides in between
    them from the front. The back wall's outer corner is chamfered (the push shroud's middle clamp screw
    head is just past it). Prints lying on the back face of its back wall: the floor and the cap are then walls."""
    g = P.__getitem__
    x1 = g('HubBackX')
    x0 = x1 - g('CradleBackT')
    xf = g('HubFaceX')
    xu = g('XFrontIn') - g('ExtW')  # the upright's back face
    xs = xu + g('CradleScrewIn') - 16  # FHCS M3x16 heads: flush here, at the bottom of counterbores from the back face
    hz0, hz1 = g('HubZ') - g('HubT') / 2 - g('HubClear'), g('HubZ') + g('HubT') / 2 + g('HubClear')
    zi = hz1 + g('CradleWallT')
    y0, ye = g('HubY0') - g('HubStopH'), g('HubY0') + g('HubL') + g('HubClear')
    y1 = ye + g('HubTopStop')
    box = lambda xa, xb, ya, yb, za, zb: Part.makeBox(xb - xa, yb - ya, zb - za, V(xa, ya, za))
    sh = box(x0, x1, y0, y1, hz0, zi).fuse([
        box(x1, xf, y0, y1, hz1, zi),                                    # inner wall
        box(x0, xu, y0, y1, g('ZRightIn') + 0.3, hz0),                   # block behind the upright
        box(x1, xf, y0, g('HubY0'), hz0, hz1),                          # floor under the cable end
        box(x1, xf, ye, y1, hz0, hz1),                                   # cap over the top end
        slot_bump(P, V(xu, y0, g('CradleScrewZ')), V(0, 1, 0), y1 - y0, V(1, 0, 0), V(0, 0, 1))]).removeSplitter()  # in the upright's back slot
    # chamfer along the back wall's outer corner
    c = g('CradleChamfer')
    bevel = Part.Face(Part.makePolygon([V(x0 - 1, y0 - 1, zi - c - 1), V(x0 - 1, y0 - 1, zi + 1), V(x0 + c + 1, y0 - 1, zi + 1),
                                        V(x0 - 1, y0 - 1, zi - c - 1)])).extrude(V(0, y1 - y0 + 2, 0))
    # slot in the floor for the cable, open to the front: the hub goes in from the front, the cable down it
    cz = g('HubCableD') / 2 + g('HubCableClear')
    cuts = [bevel, box(g('HubCableX') - g('HubCableClear'), xf + 1, y0 - 1, g('HubY0') + 1, g('HubZ') - cz, g('HubZ') + cz)]
    fixings = []
    for y in (g('CradleY1'), g('CradleY2')):
        z = g('CradleScrewZ')
        k = (g('CradleCboreD') / 2 - g('ClearD') / 2 + g('CsinkRun')) / math.tan(math.radians(g('CsinkA') / 2))
        cuts += [Part.makeCylinder(g('ClearD') / 2, xu - x0 + 4, V(x0 - 1, y, z), V(1, 0, 0)),
                 Part.makeCylinder(g('CradleCboreD') / 2, xs - x0 + 1, V(x0 - 1, y, z), V(1, 0, 0)),
                 Part.makeCone(g('CradleCboreD') / 2, g('ClearD') / 2 - g('CsinkRun'), k, V(xs, y, z), V(1, 0, 0))]
        fixings.append(dict(kind='hub_rail', p=[xs, y, z], n=[-1, 0, 0], rail='Y', nut=[xu + g('SlotLip'), y, z]))
    sh = sh.cut(cuts)
    # bed chamfer, but not where the corner chamfer already meets the bed at 45 deg
    es = [e for e in sh.Edges if all(abs(vx.Point.x - x0) < 1e-6 for vx in e.Vertexes) and not isinstance(e.Curve, Part.Circle)
          and not all(abs(vx.Point.z - (zi - c)) < 1e-6 for vx in e.Vertexes)]
    return sh.makeChamfer(g('BedChamfer'), es), fixings


def build_tab_bar(P):
    """Tab bar, in the board frame: a bar under the I/O bracket tab across the full width between the back
    uprights (so the tab screw doesn't lever a one-sided mount off its rail), with the tab insert pressed in
    from the top. Each end is a block down round its end screw: a BHCS M3x20 from outside the upright into an
    insert pressed in from the block's inner face (the screw pulls it against the block). Prints on its back
    face: the holes along Y and Z are teardrops."""
    g = P.__getitem__
    x0, x1 = g('XBackIn') + g('MountBackGap'), g('ArmX1')
    za, zb = g('ZRightIn') + g('ExtW') + g('BraceClear'), g('ZLeftIn') - g('ExtW') - g('BraceClear')
    ya, yt = g('TabUnderY') - g('ArmH'), g('TabUnderY')
    t = g('BraceEndT')
    box = lambda y0, y1, z0, z1: Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    sx, sy = g('XBackIn') + g('SlotC'), g('TabBarScrewY')
    # slot bumps on the end faces, along the back uprights' inner slots
    bumps = [slot_bump(P, V(sx, g('TabBarEndY0'), z), V(0, 1, 0), yt - g('TabBarEndY0'), V(0, 0, sg), V(1, 0, 0),
                       gap=g('BraceClear')) for z, sg in ((za, -1), (zb, 1))]
    sh = box(ya, yt, za, zb).fuse([box(g('TabBarEndY0'), yt, za, za + t), box(g('TabBarEndY0'), yt, zb - t, zb)]
                                  + bumps).removeSplitter()
    up = V(1, 0, 0)  # print up
    tab = V(g('TabX'), g('TabUnderY'), g('TabZ'))
    cuts = [teardrop_prism(tab, V(0, 1, 0), up, g('InsertD'), 2 * g('InsertDepth')),
            teardrop_prism(tab, V(0, 1, 0), up, g('ScrewD'), 2 * g('ArmH') + 2)]
    for zf, sg in ((za + t, -1), (zb - t, 1)):  # inner faces of the end blocks; the insert goes outward from there
        cuts += [teardrop_prism(V(sx, sy, zf + sg * g('InsertDepth') / 2), V(0, 0, 1), up, g('InsertD'), g('InsertDepth')),
                 teardrop_prism(V(sx, sy, zf + sg * t / 2), V(0, 0, 1), up, g('ScrewD'), t + 2 * (g('BraceClear') + g('SlotBumpH')) + 2)]
    sh = sh.cut(cuts)
    es = [e for e in sh.Edges if all(abs(vx.Point.x - x0) < 1e-6 for vx in e.Vertexes) and not isinstance(e.Curve, Part.Circle)]
    return sh.makeChamfer(g('BedChamfer'), es)


def build_psu_mount(P):
    """PSU front mount, in the board frame: one U-shaped profile, PsuMountT deep, against the PSU's front lip
    (the modular sockets face up, behind it): a plate with two #6-32 flat heads through it into the lip (in
    counterbores, in the middle of its height), and a side each end, across the bottom long rail to the side
    panel, screwed (FHCS M3x16, flush) into a T-nut in the rail. Symmetric about the PSU's centre line. Its front and back faces have
    the same chamfer all round. Prints on its back face (the one against the PSU): the lip screw holes are vertical, the rail
    screw holes teardrops."""
    g = P.__getitem__
    x0 = g('PsuX0') + g('PsuL')  # the lip's front face
    xf = x0 + g('PsuMountT')
    y0, z0 = g('PsuY0'), g('PsuZ0')
    zr, zl, cl = g('ZRightIn') + g('ExtW'), g('ZLeftIn') - g('ExtW'), g('PsuMountClear')
    yt = g('YBotIn') + g('ExtW')  # the bottom long rails' top faces
    wt = yt + g('PsuMountWingT')
    cr, cl0 = z0 + g('PsuColIn'), z0 + g('PsuW') - g('PsuColIn')
    # the profile (Y, Z), extruded along X
    pts = [(y0, zr + cl), (y0, zl - cl), (yt, zl - cl), (yt, g('ZLeftIn') - cl), (wt, g('ZLeftIn') - cl), (wt, cl0),
           (y0 + g('PsuMountH'), cl0), (y0 + g('PsuMountH'), cr), (wt, cr), (wt, g('ZRightIn') + cl),
           (yt, g('ZRightIn') + cl), (yt, zr + cl)]
    sh = Part.Face(Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, *pts[0])])).extrude(V(g('PsuMountT'), 0, 0))
    k = (g('PsuCsinkD') / 2 - g('PsuScrewD') / 2 + g('CsinkRun')) / math.tan(math.radians(g('PsuCsinkA') / 2))
    fixings, cuts = [], []
    for z in (z0 + g('PsuLipZ'), z0 + g('PsuW') - g('PsuLipZ')):
        y = y0 + g('PsuLipY')
        xh = xf - g('PsuMountCbore')  # the screw head
        cuts += [Part.makeCylinder(g('PsuScrewD') / 2, g('PsuMountT') + 2, V(x0 - 1, y, z), V(1, 0, 0)),
                 Part.makeCylinder(g('PsuCsinkD') / 2, g('PsuMountCbore') + 1, V(xh, y, z), V(1, 0, 0)),
                 Part.makeCone(g('PsuCsinkD') / 2, g('PsuScrewD') / 2 - g('CsinkRun'), k, V(xh, y, z), V(-1, 0, 0))]
        fixings.append(dict(kind='psu_front', p=[xh, y, z], n=[1, 0, 0]))
    sh = sh.cut(cuts)
    line = lambda e: not isinstance(e.Curve, Part.Circle)
    at = lambda e, x: all(abs(vx.Point.x - x) < 1e-6 for vx in e.Vertexes)
    m = g('PsuMountChamfer')
    sh = sh.makeChamfer(m, [e for e in sh.Edges if line(e) and at(e, xf)])
    sh = sh.makeChamfer(m, [e for e in sh.Edges if line(e) and at(e, x0)])
    # slot bumps under the sides, in the rails' top slots: they run out at both ends (the bottom one prints
    # facing down), clear of the chamfers
    rails = (g('ZRightIn') + g('SlotC'), g('ZLeftIn') - g('SlotC'))
    sh = sh.fuse([slot_bump(P, V(x0 + m + 0.5, yt, z), V(1, 0, 0), g('PsuMountT') - 2 * m - 1, V(0, -1, 0), V(0, 0, 1),
                            taper=(True, True)) for z in rails]).removeSplitter()
    xr = (x0 + xf) / 2
    cuts = []
    kc = (g('CsinkD') / 2 - g('ClearD') / 2 + g('CsinkRun')) / math.tan(math.radians(g('CsinkA') / 2))
    for z in rails:
        cuts.append(teardrop_prism(V(xr, (yt + wt) / 2, z), V(0, 1, 0), V(1, 0, 0), g('ClearD'), g('PsuMountWingT') + 2 * g('SlotBumpH') + 2))
        cuts.append(Part.makeCone(g('CsinkD') / 2, g('ClearD') / 2 - g('CsinkRun'), kc, V(xr, wt, z), V(0, -1, 0)))
        fixings.append(dict(kind='psu_rail', p=[xr, wt, z], n=[0, 1, 0], rail='X', nut=[xr, yt - g('SlotLip'), z]))
    return sh.cut(cuts), fixings


def build_foot(P, h, recess):
    """Round TPU foot, ground face at z=0: an FHCS M3x16 sits recessed in it and runs through the panel
    into a T-nut in the rail."""
    g = P.__getitem__
    r = g('FootD') / 2
    sh = Part.makeCylinder(r, h)
    sh = sh.makeChamfer(g('FootChamfer'), [e for e in sh.Edges if abs(e.BoundBox.ZMax) < 1e-6])
    sh = sh.makeChamfer(g('EdgeChamfer'), [e for e in sh.Edges if abs(e.BoundBox.ZMin - h) < 1e-6
                                            and isinstance(e.Curve, Part.Circle)])
    k = (g('CsinkD') / 2 - g('ClearD') / 2 + g('CsinkRun')) / math.tan(math.radians(g('CsinkA') / 2))
    return sh.cut([Part.makeCylinder(g('CsinkD') / 2, recess + 1, V(0, 0, -1)),
                   Part.makeCone(g('CsinkD') / 2, g('ClearD') / 2 - g('CsinkRun'), k, V(0, 0, recess)),
                   Part.makeCylinder(g('ClearD') / 2, h + 2, V(0, 0, -1))])


def build_jig(P):
    """Blind-joint drill jig, in print orientation (guide face on the bed): local x along the rail (end stop
    at x < 0), y across it, z down the rail from its face (z = JigGuideT at the rail face). Two guide bores:
    5 mm, 10 mm from the end (blind-joint access holes), and 3.4 mm, BraceScrewUp from the end (the back
    brace screw holes through the back uprights)."""
    g = P.__getitem__
    t, w, c, L = g('JigGuideT'), g('JigWallT'), g('JigClear'), g('JigL')
    half = g('ExtW') / 2 + c
    sh = Part.makeBox(L + w, 2 * (half + w), t + g('JigWallH'), V(-w, -half - w, 0))
    sh = sh.cut(Part.makeBox(L + 1, 2 * half, g('JigWallH') + 1, V(0, -half, t)))  # the rail end goes in here
    # slot bump in the face's slot, run out at the open end so the rail slides in onto it
    key = slot_bump(P, V(0, 0, t), V(1, 0, 0), L, V(0, 0, 1), V(0, 1, 0), taper=(False, True))
    sh = sh.fuse(key).removeSplitter()
    bore = Part.makeCylinder(g('JigHoleD') / 2 + g('JigBoreClear'), t + g('SlotBumpH') + 2, V(g('JigHoleX'), 0, -1))
    bore2 = Part.makeCylinder(g('JigHole2D') / 2 + g('JigBoreClear'), t + g('SlotBumpH') + 2, V(g('JigHole2X'), 0, -1))
    sh = sh.cut([bore, bore2])
    es = [e for e in sh.Edges if abs(e.BoundBox.ZMax) < 1e-6 and not isinstance(e.Curve, Part.Circle)]
    sh = sh.makeChamfer(g('BedChamfer'), es)
    es = [e for e in sh.Edges if abs(e.BoundBox.ZMin - (t + g('JigWallH'))) < 1e-6 and abs(e.BoundBox.ZMax - e.BoundBox.ZMin) < 1e-6]
    return sh.makeChamfer(g('EdgeChamfer'), es)


def build_frame():
    doc = App.newDocument('fish_tank_frame')
    P = Params(doc, FRAME)
    for n, L in (('Rail_X', P['RailLX']), ('Rail_Y', P['RailLY']), ('Rail_Z', P['RailLZ'])):
        rail(doc, n, L)
    # back uprights: a hole through them for the back brace screw (along the rail's local z: the board Z)
    back = rail(doc, 'Rail_Y_Back', P['RailLY'])
    back.Shape = back.Shape.cut([Part.makeCylinder(P['ClearD'] / 2, P['ExtW'] + 2, V(x, 0, -P['ExtW'] / 2 - 1))
                                 for x in (P['BraceScrewUp'], P['RailLY'] - P['BraceScrewUp'])])  # brace, tab bar
    # the extrusions are bought (cut to these lengths, and drilled to these holes): they are locked like the
    # printed parts (stls/locked.json). Change them only if there is no other way; then make relock
    # PARTS=Rail_X,...
    for n in ('Rail_X', 'Rail_Y', 'Rail_Y_Back', 'Rail_Z'):
        print(f'  {n}: {doc.getObject(n).Label}: bought extrusion lock '
              f'ok={check_lock(doc.getObject(n).Shape, os.path.join(OUTDIR, "stls", n))}')
    bhcs_m5(doc, 10)
    tnut_m3(doc)
    build_brace(doc, P)
    panels, extra, fixings = build_panels(P)
    ret, rfix = build_hub_cradle(P)
    pmount, pfix = build_psu_mount(P)
    extra['PsuMount'] = pmount
    extra['HubCradle'] = ret
    extra['TabBar'] = build_tab_bar(P)
    for name, h, rec in (('TpuFootShort', 'FootShortH', 'FootShortRecess'), ('TpuFootTall', 'FootTallH', 'FootTallRecess')):
        extra[name] = build_foot(P, P[h], P[rec])
    extra['DrillJig'] = build_jig(P)
    for name, sh in list(panels.items()) + list(extra.items()):
        doc.addObject('Part::Feature', name).Shape = sh
    fx = doc.addObject('App::FeaturePython', 'Fixings')
    fx.addProperty('App::PropertyString', 'Data', 'Fixings', 'Screw positions for the assembly (JSON, board frame)')
    fx.Data = json.dumps(fixings + rfix + pfix)
    doc.recompute()
    return doc


# print orientation: the face that goes on the bed, as its outward direction in the board frame (the
# braces and the feet are modelled in print orientation)
DOWN = {'PanelLeft': (0, 0, 1), 'PanelRight': (0, 0, -1), 'PanelTop': (0, 1, 0), 'PanelBottom': (0, -1, 0),
        'PanelFront': (1, 0, 0), 'PanelBack': (-1, 0, 0), 'SpliceLeft': (0, 0, 1), 'SpliceRight': (0, 0, -1),
        'SpliceTop': (0, 1, 0), 'SpliceBottom': (0, -1, 0), 'HubCradle': (-1, 0, 0), 'TabBar': (-1, 0, 0),
        'PsuMount': (-1, 0, 0)}
# (the splice strips: the face against the panel goes on the bed, so the insert holes open upward)

# body: (quantity, STL name, accent colour)
PRINT_QTY = {'PanelLeftBack': (1, 'panel_left_back', False), 'PanelLeftFront': (1, 'panel_left_front', False),
             'PanelRightBack': (1, 'panel_right_back', False), 'PanelRightMiddle': (1, 'panel_right_middle', False),
             'PanelRightFront': (1, 'panel_right_front', False),
             'PanelTopBack': (1, 'panel_top_back', False), 'PanelTopFront': (1, 'panel_top_front', False),
             'PanelBottomBack': (1, 'panel_bottom_back', False), 'PanelBottomFront': (1, 'panel_bottom_front', False),
             'PanelFront': (1, 'panel_front', False), 'PanelBackBottom': (1, 'panel_back_bottom', False),
             'PanelBackTop': (1, 'panel_back_top', False),
             # the side splice strips (left, two right) are one part, and so are the top and bottom ones
             'SpliceLeft': (3, 'splice_side', False), 'SpliceTop': (2, 'splice_top_bottom', False),
             'BackBrace': (1, 'back_brace', False), 'HubCradle': (1, 'hub_cradle', False),
             'TabBar': (1, 'tab_bar', False), 'PsuMount': (1, 'psu_mount', False),
             'TpuFootShort': (4, 'tpu_foot_short', False), 'TpuFootTall': (4, 'tpu_foot_tall', False),
             'DrillJig': (1, 'blind_joint_drill_jig', True)}
BED = 250.0

if os.environ.get('GEN_MAIN') == 'frame':
    stldir = os.path.join(OUTDIR, 'stls')
    os.makedirs(stldir, exist_ok=True)
    doc = build_frame()
    os.makedirs(CADDIR, exist_ok=True)
    path = os.path.join(CADDIR, doc.Name + '.FCStd')
    if os.path.exists(path):
        os.remove(path)
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    doc = App.openDocument(path)
    doc.recompute()
    for name, (qty, fname, accent) in PRINT_QTY.items():
        obj = doc.getObject(name)
        check(doc, obj)
        sh = obj.Shape.copy()
        base = next((k for k in DOWN if name in (k, k + 'Back', k + 'Middle', k + 'Front', k + 'Bottom', k + 'Top')), None)
        if base:
            sh = sh.transformGeometry(App.Placement(V(), App.Rotation(V(*DOWN[base]), V(0, 0, -1))).toMatrix())
        b = sh.optimalBoundingBox()
        fits = b.XLength <= BED and b.YLength <= BED
        print(f'  {fname}: bed footprint {b.XLength:.1f} x {b.YLength:.1f} mm ok={fits}')
        export_stl(sh, stl_path(stldir, fname, qty, accent), tight=True)
