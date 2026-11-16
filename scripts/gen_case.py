# Generates The Fish Tank, the parametric BC-250 case: two halves split between the push and pull fans, glue-in
# hex-pattern grills (round for the fans) and the USB hub retainer. Outside screw heads sit flush in countersinks.
# Run with: GEN_MAIN=case OUTDIR=<project dir> freecadcmd scripts/gen_case.py
# (FCStd goes to OUTDIR/cad, printable STLs to OUTDIR/stls, laid out in print orientation.)
#
# The case is modelled in the assembly's board frame: X along the board from the I/O edge (back of
# the case) to the front, Y up (the I/O bracket's tab at the top), Z toward the push-pull fans (left
# side seen from the front). Each half prints standing on its outer end face, so every opening in the
# side, top and bottom walls points toward the split (hexagons, teardrops) and needs no supports.
# The long faces and the front carry a hex deboss pattern; the halves meet along its grooves (case_pattern.py).
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App, Part
from gen_shrouds import CADDIR, Params, SK, feat, chamfer, check, export_stl, stl_path, at_z
import case_pattern as CP

V = App.Vector
OUTDIR = os.environ.get('OUTDIR', '.')

CASE = [
    # --- board-frame positions taken from the assembly
    ('TabTipX', -18.2, 'I/O bracket tab: rear tip (X)'),
    ('TabX', -12.35, 'I/O bracket tab: screw hole centre X'),
    ('TabZ', 6.7, 'I/O bracket tab: screw hole centre Z'),
    ('TabUnderY', 115.9, 'I/O bracket tab: underside (Y)'),
    ('ShroudTopY', 133.5, 'Highest point of the board assembly (clamp-block fences)'),
    ('ShroudBotY', -11.5, 'Lowest point of the board assembly over the PSU (clamp-block fences)'),
    ('FanFaceZ', 78.7, 'Outer face of the push/pull fans (Z)'),
    ('RearFanFaceZ', -29.5, 'Outer (intake) face of the backplate fan (Z)'),
    ('PushFanX', 263.0, 'Push fan centre (X)'),
    ('PullFanX', 79.55, 'Pull fan centre (X)'),
    ('RearFanX', 168.775, 'Backplate fan centre (X)'),
    ('FanY', 60.75, 'Fan centres (Y): the PCB centre, between its main edges at Y = -0.5 and 122'),
    ('FanHoleSpacing', 105.0, '120 mm fan screw pattern'),
    ('FanOpeningD', 115.0, 'Fan air opening'),
    # --- shell
    ('CaseT', 4.0, 'Wall thickness (room for flush countersunk screw heads)'),
    ('CaseChamfer', 4.0, 'Outer edge chamfer'),
    ('BedChamfer', 0.5, 'Chamfer on openings in the faces printed on the bed'),
    ('TabClear', 0.3, 'Back wall inner face to the bracket tab tip'),
    ('TopClear', 3.0, 'Top wall inner face above the board assembly (> TongueClear + TongueT: the front half\'s '
                      'top tongue passes over the push shroud\'s clamp fences as it slides on)'),
    ('WallGasketT', 1.5, 'TPU gasket between the push/pull fans and the left wall'),
    ('FanStackClear', 0.5, 'Sliding clearance at the fan + gasket stacks (taken up by the TPU when the fan screws tighten)'),
    ('RearFanClear', 6.5, 'Backplate fan intake face to the right wall'),
    ('PsuH', 40.5, 'Flex ATX PSU height (lying flat)'),
    ('PsuClear', 1.5, 'PSU top to the lowest point of the board assembly'),
    ('SplitX', '=RearFanX', 'Split plane between the halves (through the backplate fan centre)'),
    ('XBack', '=TabTipX - TabClear - CaseT', 'Back outer face'),
    ('XFront', '=2 * PushFanX - SplitX', 'Front outer face: push fan centred on the front half'),
    ('YTop', '=ShroudTopY + TopClear + CaseT', 'Top outer face'),
    ('YBot', '=ShroudBotY - PsuClear - PsuH - CaseT', 'Bottom outer face (PSU sits on the floor)'),
    ('ZLeft', '=FanFaceZ + WallGasketT + FanStackClear + CaseT', 'Left (fan side) outer face'),
    ('ZRight', '=RearFanFaceZ - RearFanClear - CaseT', 'Right outer face'),
    ('InnerChamfer', '=CaseChamfer - CaseT * (2 - sqrt(2))', 'Inside corner chamfer (even wall thickness)'),
    # --- hex deboss pattern round the long faces (case_pattern.py); the seam follows its grooves
    ('HexCells', 18, 'Pattern cells round the case (the lattice closes on itself)'),
    ('HexP', '=(2 * (YTop - YBot) + 2 * (ZLeft - ZRight) - 8 * CaseChamfer + 4 * sqrt(2) * CaseChamfer) / HexCells',
     'Pattern cell size across flats: the long faces\' perimeter / HexCells'),
    ('HexTip', '=HexP / 2 / cos(30)', 'Cell centre to point (the points run along the case)'),
    ('GrooveW', 1.6, 'Pattern V-groove width'),
    ('GrooveD', '=GrooveW / 2', 'Pattern V-groove depth (45 deg walls)'),
    ('PatternClear', 2.0, 'Grooves stop short of openings, countersinks and the end chamfers by this'),
    ('PatternMinRun', 5.0, 'Groove pieces left shorter than this by the masking are dropped (no dashes)'),
    ('SeamA', '=HexTip / 4', 'The seam zigzags SplitX +- SeamA along the grooves between two cell columns'),
    ('SeamX0', '=SplitX - SeamA', ''), ('SeamX1', '=SplitX + SeamA', ''),
    ('SeamGap', 0.2, 'Gap between the halves at the seam (hidden in the groove)'),
    # --- grills
    ('GrillLip', 3.0, 'Width of the ledge the glue-in grills sit on'),
    ('RebateD', '=CaseT / 2', 'Grill rebate depth (= grill thickness): half the wall'),
    ('GrillClear', 0.3, 'Grill clearance in its rebate, each side (print tolerance + glue)'),
    ('GrillT', '=RebateD', 'Grill thickness'),
    ('GrillHole', 6.0, 'Grill hex hole size (across flats)'),
    ('GrillRib', 1.2, 'Grill rib width between hex holes'),
    ('GrillPitch', '=GrillHole + GrillRib', ''),
    ('GrillPeak', 26.0, 'Fan openings: point toward the split, sides tangent 26 deg from the tip (64 deg overhang)'),
    ('FanScrewD', 3.6, 'Fan screw clearance through the wall'),
    # --- countersinks: every screw head on the outside sits flush
    ('CsinkD', 6.9, 'M3 countersink diameter at the surface (ISO 10642 head: 6.72 max)'),
    ('CsinkA', 90.0, 'M3 countersink included angle'),
    ('PsuCsinkD', 6.9, '#6-32 flat head countersink diameter (head: 6.65 max)'),
    ('PsuCsinkA', 82.0, '#6-32 flat head included angle'),
    ('CsinkRun', 0.1, 'Cone runs this far (radially) into the hole, so it leaves no ledge'),
    ('EdgeChamfer', 0.5, 'Small-part top edge chamfer'),
    ('VentW', 24.0, 'Top vent width (Z)'),
    ('VentL', 110.0, 'Top vent length end to end (X); the point toward the split adds a little'),
    ('VentZ', -18.0, 'Top vent centre (Z): over the backplate fan channel'),
    ('VentBackX', 75.0, 'Back half top vent centre (X)'),
    ('VentFrontX', 262.0, 'Front half top vent centre (X)'),
    # --- joint between the halves: tongues on the front half slide inside the back half
    ('TongueBeyond', 6.0, 'Tongue runs this far past the joint screws'),
    ('TongueT', 2.5, 'Tongue thickness'),
    ('TongueClear', 0.2, 'Tongue to back half wall clearance'),
    ('BandL', 10.0, 'Front half wall thickening that carries the tongue'),
    ('RibH', 5.0, 'Insert rib height on the tongue (insert from its inner face, 2 mm shoulder under the tongue face)'),
    ('RibW', 10.0, 'Insert rib width'),
    ('JointX', '=SplitX - 3 * SeamA', 'Joint screws (X): centres of the pattern cells next to the seam'),
    ('MountTopZ', -4.0, 'Backplate fan mount: its highest Z under the top tongue (the top joint ribs stay clear)'),
    ('InsertD', 4.4, 'Heat-set insert hole (Voron M3x5x4)'),
    ('InsertDepth', 5.5, ''),
    ('ScrewD', 3.2, 'Screw hole beyond an insert'),
    ('ClearD', 3.4, 'M3 clearance'),
    # --- screw-on TPU hex feet, one pattern cell each, keyed into its grooves: short ones on the bottom
    # (standing), tall ones on the right side (lying with the push-pull fans up, the backplate fan
    # intake under the case). Positions come from the pattern (layout()).
    ('FootSize', '=HexP + GrooveW + 0.4', 'Foot across flats: covers its cell and the grooves round it'),
    ('FootShortH', 9.0, 'Standing foot height'), ('FootShortRecess', 1.0, 'Screw head below the foot face (FHCS M3x12)'),
    ('FootTallH', 15.0, 'Lying foot height: clearance for the backplate fan intake'),
    ('FootTallRecess', 7.0, 'Screw head below the foot face (FHCS M3x12, the same screw as the short feet and the joints)'),
    ('FootKeyW', 0.6, 'Key ribs on the foot that sit in the cell grooves'), ('FootKeyH', 0.4, ''),
    ('FootChamfer', 1.0, 'Foot ground edge chamfer'),
    # --- back panel
    ('IoY0', 4.0, 'I/O opening (bracket plate is 4.5..117 x -1.3..26.5)'), ('IoY1', 107.0, ''),
    ('IoZ0', -2.0, ''), ('IoZ1', 27.5, ''), ('IoChamfer', 2.0, ''),
    ('LedgeH', 8.0, 'Bracket tab ledge height under the tab'),
    ('LedgeZ0', 1.5, 'Ledge Z range (tab is 1.5..25.2)'), ('LedgeZ1', 12.0, ''),
    ('LedgeX1', -5.0, 'Ledge front end (bracket plate at -3.3)'),
    ('AccessD', 7.0, 'Screwdriver access hole above the tab screw'),
    # --- Flex ATX PSU (Enhance ENP-8345L-OVT, 165 x 81.5 x 40.5, modular): AC end against the back
    # wall, lying on the floor. It draws air from inside the case and blows it out through the AC end,
    # so the back wall gets a big opening. (Mounting holes / C14 as the Flex ATX FSP drawing.)
    ('PsuL', 165.0, 'PSU length (modular: 15 mm longer than a FlexGURU)'), ('PsuW', 81.5, 'PSU width'),
    ('PsuSideClear', 0.3, ''),
    ('PsuX0', '=XBack + CaseT', 'PSU AC face'),
    ('PsuY0', '=YBot + CaseT', 'PSU bottom'),
    ('PsuZ0', '=ZRight + CaseT + InnerChamfer + PsuSideClear', 'PSU right side (seen from the front)'),
    ('PsuZ1', '=PsuZ0 + PsuW', ''),
    ('PsuHoleZ', '=PsuZ1 - 5.6', '#6-32 holes on the AC face: 5.6 from the edge'),
    ('PsuHoleY1', 4.1, '... at 4.1 and 36.1 above the PSU bottom'), ('PsuHoleY2', 36.1, ''),
    ('PsuScrewD', 3.8, '#6-32 clearance'),
    ('PsuOpenInset', 1.0, 'Exhaust opening inset from the PSU outline'),
    ('PsuOpenTop', 7.5, 'Opening top edge below the PSU top'),
    ('PsuOpenSide', 10.0, 'Opening edge in from the screw side'),
    ('PsuRibH', 6.0, 'Floor guide rib along the PSU (back wall to DC end)'), ('PsuRibT', 3.0, ''),
    ('PsuRibGusset', 3.0, '45 deg gusset between the rib and the floor, outer side only'),
    # --- Anker 4-port USB hub (A7516 / A8309: 108 x 31 x 10), standing vertically behind the front
    # wall on the right, ports facing out, cable leaving the bottom end
    # --- power button: mosfet.party 16 mm backlit momentary (M16 thread, 18 mm head, 19 mm nut),
    # in the middle of the bottom-centre hex of the front pattern (ButtonY/Z from layout())
    ('ButtonHoleD', 16.2, 'Power button panel hole (16 mm cutout)'),
    ('HubL', 108.0, 'Hub length'), ('HubW', 31.0, 'Hub depth (port face to back)'), ('HubT', 10.0, 'Hub thickness'),
    ('HubClear', 0.3, ''),
    ('HubZ', -22.0, 'Hub centre (Z)'),
    ('HubY0', -26.5, 'Hub cable end (Y): port opening centred on the front face'),
    ('HubPort1', 37.6, 'First port centre from the cable end'), ('HubPortPitch', 19.95, ''),
    ('HubSlotMargin', 9.0, 'Port opening past the outer port centres (plug overmolds); lips beyond it'),
    ('HubLipT', 2.0, 'Front wall lips in front of the hub ends: the hub sits in a pocket this far behind the face '
                     '(the front hex pattern runs over the lips: GrooveD deep, leaving 1.2)'),
    ('HubFaceX', '=XFront - HubLipT', 'Hub port face'),
    ('HubRibT', 8.0, 'Rib beside the hub (carries a retainer insert)'),
    ('HubBackX', '=HubFaceX - HubW - HubClear', 'Back face of the hub (retainer sits here)'),
    ('HubStopH', 2.0, 'Stop under the hub bottom end, clear of the cable'), ('HubStopL', 12.0, ''),
    ('RetT', 4.0, 'Hub retainer thickness (it backs the whole hub length)'),
    ('RetScrewInset', 8.0, 'Retainer screws from the hub ends'),
    ('RetY1', '=HubY0 + RetScrewInset', 'Retainer screws, bottom pair (Y)'),
    ('RetY2', '=HubY0 + HubL - RetScrewInset', 'Retainer screws, top pair (Y)'),
    ('HubRibZA', '=HubZ + HubT / 2 + HubClear + HubRibT / 2', 'Inner rib centre'),
    ('HubRibZB', '=(ZRight + CaseT + HubZ - HubT / 2 - HubClear) / 2', 'Outer rib (on the wall) centre'),
]


# ------------------------------------------------------------------ helpers
def poly(s, pts):
    return s.polygon([(str(u), str(v)) for u, v in pts])


def octagon(s, u0, u1, v0, v1, c):
    """Rectangle with 45 deg chamfered corners (all args are expressions)."""
    a = lambda x, d: f'({x}) + ({d})'
    m = lambda x, d: f'({x}) - ({d})'
    return poly(s, [(a(u0, c), v0), (m(u1, c), v0), (u1, a(v0, c)), (u1, m(v1, c)),
                    (m(u1, c), v1), (a(u0, c), v1), (u0, m(v1, c)), (u0, a(v0, c))])


def hexagon(s, cu, cv, a, tip=None):
    """Hexagon pointy along u, across-flats 2a; tip = centre-to-point (default: regular)."""
    t = f'({tip or f"({a}) / cos(30)"})'
    f = f'({t} - ({a}) * tan(30))'
    return poly(s, [(f'({cu}) + {t}', cv), (f'({cu}) + {f}', f'({cv}) + ({a})'),
                    (f'({cu}) - {f}', f'({cv}) + ({a})'), (f'({cu}) - {t}', cv),
                    (f'({cu}) - {f}', f'({cv}) - ({a})'), (f'({cu}) + {f}', f'({cv}) - ({a})')])


def teardrop(s, cu, cv, d, tip, psi='45'):
    """Hole of diameter d with a point toward tip ('+u' or '-u') whose sides touch the circle psi deg
    either side of it: prints without support when u is the print's up direction (steepest overhang
    90 - psi; 45 is the usual teardrop)."""
    P = s.P
    cx, cy, r, ps = P.py(cu), P.py(cv), P.py(d) / 2, P.py(psi)
    th = 0 if tip == '+u' else 180
    pt = lambda a, rr=r: (cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a)))
    A = s.arc((cx, cy), r, th + ps, th + 360 - ps)
    T = pt(th, r / math.cos(math.radians(ps)))
    L1 = s.line(pt(th + 360 - ps), T)
    L2 = s.line(T, pt(th + ps))
    s.c('Tangent', L1, 1, A, 2); s.c('Tangent', L2, 2, A, 1); s.co(L1, 2, L2, 1)
    s.px(A, 3, cu); s.py(A, 3, cv)
    s.dim('Radius', A, expr=f'({d}) / 2')
    s.px(L1, 2, f'({cu}) {tip[0]} ({d}) / 2 / cos({psi})'); s.py(L1, 2, cv)


def disc(s, cu, cv, d, tip=None):
    """Fan-size opening of diameter d: a circle, or pointed toward tip at the overhang limit."""
    if tip:
        return teardrop(s, cu, cv, d, tip, 'GrillPeak')
    g = s.circle((s.P.py(cu), s.P.py(cv)), s.P.py(d) / 2)
    s.px(g, 3, cu); s.py(g, 3, cv)
    s.dim('Diameter', g, expr=d)


def pill(s, cu, cv, length, width, tip, psi='GrillPeak'):
    """Slot along u, length x width with round ends, centred on (cu, cv); the end toward tip
    ('+u' / '-u') gets a point like teardrop's so the slot prints when tip is up."""
    P = s.P
    cx, cy, L, r, ps = P.py(cu), P.py(cv), P.py(length), P.py(width) / 2, P.py(psi)
    sg, th = (1, 0) if tip == '+u' else (-1, 180)
    ct, cb = (cx + sg * (L / 2 - r), cy), (cx - sg * (L / 2 - r), cy)
    pt = lambda c, a, rr=r: (c[0] + rr * math.cos(math.radians(a)), c[1] + rr * math.sin(math.radians(a)))
    A1 = s.arc(ct, r, th + ps, th + 90)
    A2 = s.arc(ct, r, th + 270, th + 360 - ps)
    B = s.arc(cb, r, th + 90, th + 270)
    S1 = s.line(pt(ct, th + 90), pt(cb, th + 90))
    S2 = s.line(pt(cb, th + 270), pt(ct, th + 270))
    T = pt(ct, th, r / math.cos(math.radians(ps)))
    L1 = s.line(pt(ct, th + 360 - ps), T)
    L2 = s.line(T, pt(ct, th + ps))
    s.c('Tangent', A1, 2, S1, 1); s.c('Tangent', S1, 2, B, 1); s.c('Tangent', B, 2, S2, 1)
    s.c('Tangent', S2, 2, A2, 1); s.c('Tangent', A2, 2, L1, 1); s.co(L1, 2, L2, 1); s.c('Tangent', L2, 2, A1, 1)
    s.co(A1, 3, A2, 3); s.c('Equal', A1, A2); s.c('Equal', A1, B)
    s.dim('Radius', A1, expr=f'({width}) / 2')
    off = f'(({length}) / 2 - ({width}) / 2)'
    s.px(A1, 3, f'({cu}) {tip[0]} {off}'); s.py(A1, 3, cv)
    s.px(B, 3, f'({cu}) {"-" if sg > 0 else "+"} {off}'); s.py(B, 3, cv)
    s.px(L1, 2, f'({cu}) {tip[0]} ({off} + ({width}) / 2 / cos({psi}))'); s.py(L1, 2, cv)


def countersinks(body, P, name, plane, face, pts, hole, d='CsinkD', angle='CsinkA'):
    """Countersinks round the holes (diameter hole) at pts, from the outer face (sketch offset face)
    down into the hole, so the screw heads sit flush."""
    s = sketch(body, P, name + 'Sketch', plane, face)
    cs = []
    for u, v in pts:
        g = s.circle((P.py(u), P.py(v)), P.py(d) / 2)
        s.px(g, 3, u); s.py(g, 3, v); cs.append(g)
    s.dim('Diameter', cs[0], expr=d)
    for g in cs[1:]:
        s.c('Equal', cs[0], g)
    f = feat(body, P, 'Pocket', name, s, f'(({d}) / 2 - ({hole}) / 2 + CsinkRun) / tan(({angle}) / 2)')
    f.TaperAngle = -P.py(angle) / 2
    f.setExpression('TaperAngle', P.fc(f'-({angle}) / 2'))
    fix_direction(body, f, False)
    return f


def fix_direction(body, f, grow):
    """Flip f.Reversed if the feature went the wrong way (grow: pad should add volume, pocket remove)."""
    doc = body.Document
    doc.recompute()
    base = f.BaseFeature.Shape.Volume if f.BaseFeature else 0.0
    good = lambda: (f.Shape.Volume - base > 1e-3) if grow else (base - f.Shape.Volume > 1e-3)
    if not good():
        f.Reversed = not f.Reversed
        doc.recompute()
    assert good(), f'{f.Name}: no effect either way'


def sketch(body, P, name, plane, offset=0.0):
    return SK(body, P, name, plane, offset)


def cut_through(body, P, name, s, thickness):
    """Pocket symmetric about the sketch plane (sketch placed mid-wall)."""
    return feat(body, P, 'Pocket', name, s, thickness, SideType='Symmetric')


# ------------------------------------------------------------------ shell
def shell(body, P, front):
    """Half-shell from the seam zone to the outer end: a box with its long edges chamfered, a tapered
    end cap (the chamfer round the end face), hollowed out. The seam zigzag is trimmed later (finish)."""
    far = 'XFront' if front else 'XBack'
    sg = '-' if front else '+'
    near = 'SeamX0' if front else 'SeamX1'
    cap0 = f'{far} {sg} CaseChamfer'
    # first feature from an XY sketch: keeps the body's placement identity (needed by the chamfers)
    s = sketch(body, P, 'OuterSketch', 'XY_Plane', '(ZRight + ZLeft) / 2')
    poly(s, [(near, 'YBot'), (cap0, 'YBot'), (cap0, 'YTop'), (near, 'YTop')])
    feat(body, P, 'Pad', 'Shell', s, 'ZLeft - ZRight', SideType='Symmetric')
    ys, zs = (P['YBot'], P['YTop']), (P['ZRight'], P['ZLeft'])
    chamfer(body, P, 'LongChamfer', 'CaseChamfer',
            lambda e: e.BoundBox.YLength < 1e-6 and e.BoundBox.ZLength < 1e-6 and
            any(abs(e.BoundBox.YMin - y) < 1e-6 for y in ys) and any(abs(e.BoundBox.ZMin - z) < 1e-6 for z in zs))
    # outer end: tapered pad gives the chamfer all round the end face
    s = sketch(body, P, 'EndCapSketch', 'YZ_Plane', cap0)
    octagon(s, 'YBot', 'YTop', 'ZRight', 'ZLeft', 'CaseChamfer')
    cap = feat(body, P, 'Pad', 'EndCap', s, 'CaseChamfer', TaperAngle=-45)
    fix_direction(body, cap, True)
    # hollow: from 1 mm past the seam zone to the inside of the end wall
    inner_end = f'{far} {sg} CaseT'
    over = f'{near} {"-" if front else "+"} 1'
    s = sketch(body, P, 'InnerSketch', 'YZ_Plane', f'({over} + {inner_end}) / 2')
    octagon(s, 'YBot + CaseT', 'YTop - CaseT', 'ZRight + CaseT', 'ZLeft - CaseT', 'InnerChamfer')
    cut_through(body, P, 'Hollow', s, f'abs({inner_end} - ({over}))')


WALLS = {'L': ('XY_Plane', 'ZLeft', 'ZLeft - CaseT / 2'),  # sketch plane, outer face, mid-wall
         'R': ('XY_Plane', 'ZRight', 'ZRight + CaseT / 2'),
         'T': ('XZ_Plane', '-YTop', '-(YTop - CaseT / 2)')}


def wall_round(body, P, name, cu, cv, r, side, tip=None):
    """Glue-in fan grill opening in a side wall: rebate r + GrillLip deep RebateD, opening r through.
    tip: the print-up direction, for an opening that doesn't reach the split (see disc)."""
    plane, outer, mid = WALLS[side]
    s = sketch(body, P, name + 'RebateSketch', plane, outer)
    disc(s, cu, cv, f'2 * ({r} + GrillLip)', tip)
    cut_through(body, P, name + 'Rebate', s, '2 * RebateD')
    s = sketch(body, P, name + 'Sketch', plane, mid)
    disc(s, cu, cv, f'2 * ({r})', tip)
    cut_through(body, P, name, s, 'CaseT + 2')


def wall_pill(body, P, name, cu, cv, length, width, side, tip):
    """Glue-in vent grill opening: pill length x width along u (point toward tip, see pill) with a
    rebate GrillLip wider all round, RebateD deep."""
    plane, outer, mid = WALLS[side]
    s = sketch(body, P, name + 'RebateSketch', plane, outer)
    pill(s, cu, cv, f'{length} + 2 * GrillLip', f'{width} + 2 * GrillLip', tip)
    cut_through(body, P, name + 'Rebate', s, '2 * RebateD')
    s = sketch(body, P, name + 'Sketch', plane, mid)
    pill(s, cu, cv, length, width, tip)
    cut_through(body, P, name, s, 'CaseT + 2')


def fan_screw_holes(body, P, name, fan_x, up):
    s = sketch(body, P, name + 'Sketch', 'XY_Plane', 'ZLeft - CaseT / 2')
    pts = [(f'{fan_x} {sx} FanHoleSpacing / 2', f'FanY {sy} FanHoleSpacing / 2') for sx in '+-' for sy in '+-']
    for u, v in pts:
        teardrop(s, u, v, 'FanScrewD', up)
    cut_through(body, P, name, s, 'CaseT + 2')
    countersinks(body, P, name + 'Csink', 'XY_Plane', 'ZLeft', pts, 'FanScrewD')


def foot_inserts(body, P, x, tip):
    """Through-wall insert holes (the insert is as long as the wall) for the screw-on feet on two
    pattern cells of the bottom and two of the right side; the unused pair just shows brass."""
    s = sketch(body, P, 'FootInsertBotSketch', 'XZ_Plane', '-(YBot + CaseT / 2)')
    for i in (1, 2):
        teardrop(s, x, f'FootBotZ{i}', 'InsertD', tip)
    cut_through(body, P, 'FootInsertBot', s, 'CaseT + 2')
    s = sketch(body, P, 'FootInsertSideSketch', 'XY_Plane', 'ZRight + CaseT / 2')
    for i in (1, 2):
        teardrop(s, x, f'FootSideY{i}', 'InsertD', tip)
    cut_through(body, P, 'FootInsertSide', s, 'CaseT + 2')


def top_vent(body, P, name, cx, tip):
    wall_pill(body, P, name, cx, 'VentZ', 'VentL', 'VentW', 'T', tip)


# ------------------------------------------------------------------ halves
def tongues(body, P):
    """Front half: tongues on the top and bottom walls that reach under the back half's wall past the
    joint screws, carried by a thickened band (45 deg lead-in, so it prints) that starts beyond the
    seam zigzag, plus insert ribs under the joint screws."""
    yt, yb = 'YTop - CaseT', 'YBot + CaseT'
    c, t = 'TongueClear', 'TongueT'
    x1, x0 = 'SeamX1 + SeamGap', 'JointX - TongueBeyond'

    def profile(s, y, sg, extra='0'):
        o = lambda d: f'{y} {"-" if sg > 0 else "+"} ({d})'
        poly(s, [(f'{x1} + BandL + {t} + {c} + {extra}', y), (x1, y), (x1, o(c)), (x0, o(c)),
                 (x0, o(f'{c} + {t} + {extra}')), (f'{x1} + BandL', o(f'{c} + {t} + {extra}'))])
    s = sketch(body, P, 'TongueSketch', 'XY_Plane', '(ZRight + ZLeft) / 2')
    profile(s, yt, 1); profile(s, yb, -1)
    feat(body, P, 'Pad', 'Tongues', s, 'ZLeft - ZRight - 2 * CaseT - 2 * InnerChamfer - 1', SideType='Symmetric')
    for side, y, sg in (('Top', yt, 1), ('Bot', yb, -1)):
        for i in (1, 2):
            s = sketch(body, P, f'Rib{side}{i}Sketch', 'XY_Plane', f'RibZ{side}{i}')
            profile(s, y, sg, 'RibH')
            feat(body, P, 'Pad', f'Rib{side}{i}', s, 'RibW', SideType='Symmetric')
    # joint inserts go in from the rib's inner face, so the joint screw (from outside the back half)
    # pulls them against the shoulder under the tongue face instead of out of their holes
    for y, side, sg in ((yt, 'Top', '-'), (yb, 'Bot', '+')):
        face, inner = f'{y} {sg} {c}', f'{y} {sg} ({c} + {t} + RibH)'
        for kind, d, at, depth in (('Insert', 'InsertD', inner, '2 * InsertDepth'),
                                   ('Screw', 'ClearD', face, f'2 * ({t} + RibH + 1)')):
            s = sketch(body, P, f'Joint{kind}{side}Sketch', 'XZ_Plane', f'-({at})')
            for i in (1, 2):
                teardrop(s, 'JointX', f'RibZ{side}{i}', d, '-u')
            cut_through(body, P, f'Joint{kind}{side}', s, depth)


def build_front(doc, P):
    body = doc.addObject('PartDesign::Body', 'CaseFrontBody')
    shell(body, P, True)
    tongues(body, P)
    wall_round(body, P, 'PushGrill', 'PushFanX', 'FanY', 'FanOpeningD / 2', 'L', '-u')
    fan_screw_holes(body, P, 'PushFanScrews', 'PushFanX', '-u')
    wall_round(body, P, 'RearOpening', 'RearFanX', 'FanY', 'FanOpeningD / 2', 'R')  # spans the seam: round
    top_vent(body, P, 'TopVent', 'VentFrontX', '-u')
    foot_inserts(body, P, 'FootX2', '-u')
    hub_features(body, P)
    s = sketch(body, P, 'ButtonSketch', 'YZ_Plane', 'XFront - CaseT / 2')  # power button
    g = s.circle((P['ButtonY'], P['ButtonZ']), P['ButtonHoleD'] / 2)
    s.px(g, 3, 'ButtonY'); s.py(g, 3, 'ButtonZ'); s.dim('Diameter', g, expr='ButtonHoleD')
    cut_through(body, P, 'ButtonHole', s, 'CaseT + 2')
    return body


def build_back(doc, P):
    body = doc.addObject('PartDesign::Body', 'CaseBackBody')
    shell(body, P, False)
    wall_round(body, P, 'PullGrill', 'PullFanX', 'FanY', 'FanOpeningD / 2', 'L', '+u')
    fan_screw_holes(body, P, 'PullFanScrews', 'PullFanX', '+u')
    wall_round(body, P, 'RearOpening', 'RearFanX', 'FanY', 'FanOpeningD / 2', 'R')
    top_vent(body, P, 'TopVent', 'VentBackX', '+u')
    foot_inserts(body, P, 'FootX1', '+u')
    # joint screws into the front half's tongues
    for y, face, name in (('YTop - CaseT / 2', 'YTop', 'Top'), ('YBot + CaseT / 2', 'YBot', 'Bot')):
        s = sketch(body, P, f'Joint{name}Sketch', 'XZ_Plane', f'-({y})')
        for i in (1, 2):
            teardrop(s, 'JointX', f'RibZ{name}{i}', 'ClearD', '+u')
        cut_through(body, P, f'Joint{name}', s, 'CaseT + 2')
        countersinks(body, P, f'Joint{name}Csink', 'XZ_Plane', f'-{face}',
                     [('JointX', f'RibZ{name}{i}') for i in (1, 2)], 'ClearD')
    # I/O opening behind the BC-250's bracket
    s = sketch(body, P, 'IoSketch', 'YZ_Plane', 'XBack + CaseT / 2')
    octagon(s, 'IoY0', 'IoY1', 'IoZ0', 'IoZ1', 'IoChamfer')
    cut_through(body, P, 'IoOpening', s, 'CaseT + 2')
    # ledge the bracket tab screws down onto, with a screwdriver hole in the top above it
    x0 = 'XBack + CaseT - 0.5'
    s = sketch(body, P, 'TabLedgeSketch', 'YZ_Plane', f'({x0} + LedgeX1) / 2')
    poly(s, [('TabUnderY - LedgeH', 'LedgeZ0'), ('TabUnderY', 'LedgeZ0'), ('TabUnderY', 'LedgeZ1'),
             ('TabUnderY - LedgeH', 'LedgeZ1')])
    feat(body, P, 'Pad', 'TabLedge', s, f'LedgeX1 - ({x0})', SideType='Symmetric')
    for kind, d, depth in (('Insert', 'InsertD', '2 * InsertDepth'), ('Screw', 'ScrewD', '2 * LedgeH')):
        s = sketch(body, P, f'Tab{kind}Sketch', 'XZ_Plane', '-TabUnderY')
        teardrop(s, 'TabX', 'TabZ', d, '+u')
        cut_through(body, P, f'Tab{kind}', s, depth)
    s = sketch(body, P, 'TabAccessSketch', 'XZ_Plane', '-(YTop - CaseT / 2)')
    teardrop(s, 'TabX', 'TabZ', 'AccessD', '+u')
    cut_through(body, P, 'TabAccess', s, 'CaseT + 2')
    psu_features(body, P)
    return body


def psu_features(body, P):
    # exhaust opening round the C14 (the FlexGURU AC face is honeycomb vent), clear of the screws
    s = sketch(body, P, 'PsuOpeningSketch', 'YZ_Plane', 'XBack + CaseT / 2')
    octagon(s, 'PsuY0 + PsuOpenInset', 'PsuY0 + PsuH - PsuOpenTop', 'PsuZ0 + PsuOpenInset',
            'PsuZ1 - PsuOpenSide', 'IoChamfer')
    cut_through(body, P, 'PsuOpening', s, 'CaseT + 2')
    s = sketch(body, P, 'PsuScrewSketch', 'YZ_Plane', 'XBack + CaseT / 2')
    cs = []
    for y in ('PsuHoleY1', 'PsuHoleY2'):
        g = s.circle((P.py(f'PsuY0 + {y}'), P['PsuHoleZ']), P['PsuScrewD'] / 2)
        s.px(g, 3, f'PsuY0 + {y}'); s.py(g, 3, 'PsuHoleZ'); cs.append(g)
    s.dim('Diameter', cs[0], expr='PsuScrewD'); s.c('Equal', cs[0], cs[1])
    cut_through(body, P, 'PsuScrews', s, 'CaseT + 2')
    countersinks(body, P, 'PsuScrewCsink', 'YZ_Plane', 'XBack',
                 [(f'PsuY0 + {y}', 'PsuHoleZ') for y in ('PsuHoleY1', 'PsuHoleY2')], 'PsuScrewD',
                 'PsuCsinkD', 'PsuCsinkA')
    # guide rib on the floor along the PSU's left side (the right wall guides the other side), from
    # the back wall to the DC end, with a 45 deg gusset to the floor on its outer side
    x0, x1 = 'XBack + CaseT - 0.5', 'PsuX0 + PsuL'
    z0 = 'PsuZ1 + PsuSideClear'
    z1, zg = f'{z0} + PsuRibT', f'{z0} + PsuRibT + PsuRibGusset'
    s = sketch(body, P, 'PsuRibSketch', 'YZ_Plane', f'({x0} + {x1}) / 2')
    poly(s, [('PsuY0 - 0.5', z0), ('PsuY0 + PsuRibH', z0), ('PsuY0 + PsuRibH', z1), ('PsuY0 + PsuRibGusset', z1),
             ('PsuY0', zg), ('PsuY0 - 0.5', zg)])
    feat(body, P, 'Pad', 'PsuRib', s, f'{x1} - ({x0})', SideType='Symmetric')


def hub_features(body, P):
    """Vertical channel behind the front wall for the USB hub: ribs either side (the outer one on the
    right wall), a stop under its bottom end, a pocket + port opening in the front wall, inserts for
    the retainer at both ends."""
    xin = 'XFront - CaseT'
    xm = f'(HubBackX + {xin} + 0.5) / 2'
    s = sketch(body, P, 'HubRibSketch', 'YZ_Plane', xm)
    za0, za1 = 'HubZ + HubT / 2 + HubClear', 'HubZ + HubT / 2 + HubClear + HubRibT'
    zb0, zb1 = 'ZRight + CaseT - 0.5', 'HubZ - HubT / 2 - HubClear'
    yb0, yb1 = 'HubY0 - HubStopH', 'HubY0 + HubL'
    poly(s, [(yb0, za0), (yb1, za0), (yb1, za1), (yb0, za1)])
    poly(s, [(yb0, zb0), (yb1, zb0), (yb1, zb1), (yb0, zb1)])
    feat(body, P, 'Pad', 'HubRibs', s, f'{xin} + 0.5 - HubBackX', SideType='Symmetric')
    s = sketch(body, P, 'HubStopSketch', 'YZ_Plane', f'({xin} + 0.5 + {xin} - HubStopL) / 2')
    poly(s, [(yb0, zb1), ('HubY0', zb1), ('HubY0', za0), (yb0, za0)])
    feat(body, P, 'Pad', 'HubStop', s, 'HubStopL + 0.5', SideType='Symmetric')
    # pocket in the front wall: the hub's port face sits HubLipT behind the outside, held by lips
    # over its two ends; between them the opening is the full hub thickness
    s = sketch(body, P, 'HubPocketSketch', 'YZ_Plane', f'(HubFaceX + {xin} - 1) / 2')
    poly(s, [('HubY0', za0), ('HubY0 + HubL + HubClear', za0), ('HubY0 + HubL + HubClear', zb1), ('HubY0', zb1)])
    cut_through(body, P, 'HubPocket', s, f'HubFaceX - ({xin} - 1)')
    s = sketch(body, P, 'HubSlotSketch', 'YZ_Plane', 'XFront - CaseT / 2')
    y0 = 'HubY0 + HubPort1 - HubSlotMargin'
    y1 = 'HubY0 + HubPort1 + 3 * HubPortPitch + HubSlotMargin'
    poly(s, [(y0, za0), (y1, za0), (y1, zb1), (y0, zb1)])
    cut_through(body, P, 'HubSlot', s, 'CaseT + 2')
    for kind, d, depth in (('Insert', 'InsertD', '2 * InsertDepth'), ('Screw', 'ScrewD', '2 * (InsertDepth + 4)')):
        s = sketch(body, P, f'Hub{kind}Sketch', 'YZ_Plane', 'HubBackX')
        cs = []
        for z in ('HubRibZA', 'HubRibZB'):
            for y in ('RetY1', 'RetY2'):
                g = s.circle((P[y], P[z]), P.py(d) / 2)
                s.px(g, 3, y); s.py(g, 3, z); cs.append(g)
        s.dim('Diameter', cs[0], expr=d)
        for g in cs[1:]:
            s.c('Equal', cs[0], g)
        cut_through(body, P, f'Hub{kind}', s, depth)


def end_face_chamfer(body, P, x):
    """0.5 mm chamfer round the openings in the face that sits on the bed (not the outer rim)."""
    y0, y1, z0, z1 = (P[k] for k in ('YBot', 'YTop', 'ZRight', 'ZLeft'))
    m = P['CaseChamfer'] + 0.1
    csink = lambda e: isinstance(e.Curve, Part.Circle) and abs(e.Curve.Radius - P['PsuCsinkD'] / 2) < 1e-3

    def inner_loop(e):
        b = e.BoundBox
        return (abs(b.XMin - x) < 1e-6 and abs(b.XMax - x) < 1e-6 and b.YMin > y0 + m and b.YMax < y1 - m
                and b.ZMin > z0 + m and b.ZMax < z1 - m and not csink(e))
    chamfer(body, P, 'BedChamfer', 'BedChamfer', inner_loop)


# ------------------------------------------------------------------ grills + hub retainer
def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    if ax == ay == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def bed_edges_on(dist):
    """Edge predicate: bed edge lying on an outline; dist(p) = distance from (u, v) to the outline."""
    def pred(e):
        b = e.BoundBox
        if abs(b.ZMin) > 1e-6 or abs(b.ZMax) > 1e-6:
            return False
        m = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
        return dist((m.x, m.y)) < 1e-4
    return pred


def pill_dist(length, r, psi):
    """Outline of pill(..., '+u', psi) (teardrop when length = 2r) centred on the origin."""
    c, sn, ct = math.cos(math.radians(psi)), math.sin(math.radians(psi)), length / 2 - r
    t, a, b = (ct + r / c, 0), (ct + r * c, r * sn), (ct + r * c, -r * sn)

    def d(p):
        in_point = p[0] > ct and math.degrees(math.atan2(abs(p[1]), p[0] - ct)) < psi - 1e-6
        rim = math.inf if in_point else abs(seg_dist(p, (-ct, 0), (ct, 0)) - r)
        return min(rim, seg_dist(p, a, t), seg_dist(p, b, t))
    return d


def grill(doc, P, name, outer, inner, outer_dist, half_w, half_h):
    """Glue-in grill, printed visible face down: plate (outer outline), a field of hex holes patterned
    over it, then the rim (outer minus inner outline) padded back over the hole field.
    outer/inner: functions drawing the outlines into a sketch; outer_dist: numeric distance to the
    outer outline (picks the bed chamfer edges); half_w/half_h: expressions for the field extent."""
    body = doc.addObject('PartDesign::Body', name)
    s = sketch(body, P, name + 'Sketch', 'XY_Plane')
    outer(s)
    feat(body, P, 'Pad', name + 'Plate', s, 'GrillT')
    # two holes half a cell apart, patterned along Y (pitch) and along X (2 * pitch * cos 30)
    s = sketch(body, P, name + 'HoleSketch', 'XY_Plane')
    x0, y0 = f'-({half_w}) - GrillPitch', f'-({half_h}) - GrillPitch'
    hexagon(s, x0, y0, 'GrillHole / 2')
    hexagon(s, f'{x0} + GrillPitch * cos(30)', f'{y0} + GrillPitch / 2', 'GrillHole / 2')
    hole = cut_through(body, P, name + 'Hole', s, '2 * GrillT + 2')
    ny = math.ceil((2 * P.py(half_h) + 2 * P['GrillPitch']) / P['GrillPitch']) + 1
    nx = math.ceil((2 * P.py(half_w) + 2 * P['GrillPitch']) / (2 * P['GrillPitch'] * math.cos(math.radians(30)))) + 1
    org = {f.Role: f for f in body.Origin.OriginFeatures}
    mt = body.newObject('PartDesign::MultiTransform', name + 'Holes')
    subs = []
    for axis, n, step in (('Y_Axis', ny, 'Params.GrillPitch'), ('X_Axis', nx, '2 * Params.GrillPitch * cos(30)')):
        lp = doc.addObject('PartDesign::LinearPattern', name + 'Holes' + axis[0])
        lp.Direction = (org[axis], [''])
        lp.Occurrences = n
        lp.setExpression('Length', f'{n - 1} * {step}')
        lp.Visibility = False
        subs.append(lp)
    mt.Transformations = subs
    mt.Originals = [hole]
    body.Tip = mt
    hole.Visibility = False
    s = sketch(body, P, name + 'RimSketch', 'XY_Plane')
    outer(s); inner(s)
    feat(body, P, 'Pad', name + 'Rim', s, 'GrillT')
    chamfer(body, P, 'BedChamfer', 'BedChamfer', bed_edges_on(outer_dist))
    return body


def build_grills(doc, P):
    """Round fan grills and pill-shaped vent grills; pointed ends face the seam (their +x)."""
    r_out = 'FanOpeningD / 2 + GrillLip - GrillClear'
    fan = grill(doc, P, 'FanGrill', lambda s: disc(s, '0', '0', f'2 * ({r_out})', '+u'),
                lambda s: disc(s, '0', '0', 'FanOpeningD', '+u'),
                pill_dist(2 * P.py(r_out), P.py(r_out), P['GrillPeak']), f'({r_out}) / cos(GrillPeak)', r_out)
    # the backplate fan's opening spans the seam: one round grill, glued into the back half only so
    # the front half still slides off
    rear = grill(doc, P, 'RearGrill', lambda s: disc(s, '0', '0', f'2 * ({r_out})'),
                 lambda s: disc(s, '0', '0', 'FanOpeningD'), pill_dist(2 * P.py(r_out), P.py(r_out), 0), r_out, r_out)
    grow = '2 * (GrillLip - GrillClear)'
    l_out, w_out = f'VentL + {grow}', f'VentW + {grow}'
    vent = grill(doc, P, 'TopVentGrill', lambda s: pill(s, '0', '0', l_out, w_out, '+u'),
                 lambda s: pill(s, '0', '0', 'VentL', 'VentW', '+u'),
                 pill_dist(P.py(l_out), P.py(w_out) / 2, P['GrillPeak']),
                 f'({l_out}) / 2 - ({w_out}) / 2 + ({w_out}) / 2 / cos(GrillPeak)', f'({w_out}) / 2')
    return fan, rear, vent


def build_retainer(doc, P):
    """Plate across the hub ribs backing the hub over its whole length, screwed into inserts near both
    ends, so pushing a plug into an end port can't pivot the hub. Local x = -Z (board), y = Y, z: 0 on
    the screw-head side, RetT against the hub."""
    body = doc.addObject('PartDesign::Body', 'HubRetainer')
    s = sketch(body, P, 'RetainerSketch', 'XY_Plane')
    x0, x1 = '-(HubRibZA + HubRibT / 2)', '-(ZRight + CaseT + 0.3)'
    y0, y1 = 'HubY0', 'HubY0 + HubL'
    poly(s, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    feat(body, P, 'Pad', 'Retainer', s, 'RetT')
    s = sketch(body, P, 'RetainerHoleSketch', 'XY_Plane', 'RetT / 2')
    cs = []
    for z in ('HubRibZA', 'HubRibZB'):
        for y in ('RetY1', 'RetY2'):
            g = s.circle((-P[z], P[y]), P['ClearD'] / 2)
            s.px(g, 3, f'-{z}'); s.py(g, 3, y); cs.append(g)
    s.dim('Diameter', cs[0], expr='ClearD')
    for g in cs[1:]:
        s.c('Equal', cs[0], g)
    cut_through(body, P, 'RetainerHoles', s, 'RetT + 2')
    xs = (P.py(x0), P.py(x1)); ys = (P.py(y0), P.py(y1)); t = P['RetT']

    def edges(e):
        b = e.BoundBox
        flat = b.ZLength < 1e-6 and (abs(b.ZMin) < 1e-6 or abs(b.ZMin - t) < 1e-6)
        rim = any(abs(b.XMin - x) < 1e-6 and b.XLength < 1e-6 for x in xs) or \
            any(abs(b.YMin - y) < 1e-6 and b.YLength < 1e-6 for y in ys)
        vertical = b.XLength < 1e-6 and b.YLength < 1e-6
        return (flat and rim) or (vertical and b.XMin in xs and b.YMin in ys)
    chamfer(body, P, 'EdgeChamfer', 'EdgeChamfer', edges)
    return body


def build_foot(doc, P, name, h, recess):
    """Screw-on TPU foot (grip, damping), the size of one pattern cell, printed ground face down: key ribs on top drop
    into the cell's grooves (locate it, stop it turning), a countersunk M3 sits recessed in the ground
    face and runs into the insert in the case wall."""
    body = doc.addObject('PartDesign::Body', name)
    s = sketch(body, P, name + 'Sketch', 'XY_Plane')
    hexagon(s, '0', '0', 'FootSize / 2')
    feat(body, P, 'Pad', name + 'Body', s, h)
    chamfer(body, P, 'GroundChamfer', 'FootChamfer', at_z(0))
    chamfer(body, P, 'TopChamfer', 'EdgeChamfer', at_z(P[h]))
    s = sketch(body, P, name + 'KeySketch', 'XY_Plane', h)
    hexagon(s, '0', '0', 'HexP / 2 + FootKeyW / 2'); hexagon(s, '0', '0', 'HexP / 2 - FootKeyW / 2')
    fix_direction(body, feat(body, P, 'Pad', name + 'Keys', s, 'FootKeyH'), True)
    s = sketch(body, P, name + 'RecessSketch', 'XY_Plane')
    g = s.circle((0, 0), P['CsinkD'] / 2); s.co(g, 3, -1, 1); s.dim('Diameter', g, expr='CsinkD')
    fix_direction(body, feat(body, P, 'Pocket', name + 'Recess', s, recess), False)
    countersinks(body, P, name + 'Csink', 'XY_Plane', recess, [('0', '0')], 'ClearD')
    s = sketch(body, P, name + 'HoleSketch', 'XY_Plane', f'{h} / 2')
    g = s.circle((0, 0), P['ClearD'] / 2); s.co(g, 3, -1, 1); s.dim('Diameter', g, expr='ClearD')
    cut_through(body, P, name + 'Hole', s, f'{h} + 2')
    return body


# ------------------------------------------------------------------ pattern + seam
def layout(P):
    """Joint screws and feet sit on pattern cell centres: work them out and add them to Params."""
    assert P['TopClear'] >= P['TongueClear'] + P['TongueT'] + 0.2, 'top tongue would scrape the shroud clamp fences'
    lat = CP.Lattice(P)
    cells = lambda face, j, margin: [lat.face_coord(face, w) for _, w in lat.cells_on_face(face, j, margin)]
    lo = P['ZRight'] + P['CaseT'] + P['InnerChamfer'] + P['RibW'] / 2 + 1.5  # tongue ribs fit
    hi = P['ZLeft'] - P['CaseT'] - P['InnerChamfer'] - P['RibW'] / 2 - 1.5
    for face, side, lo_side in ((CP.TOP, 'Top', max(lo, P['MountTopZ'] + P['RibW'] / 2 + 1.5)), (CP.BOTTOM, 'Bot', lo)):
        z = sorted(v for v in cells(face, 0, 0) if lo_side <= v <= hi)
        P.add(f'RibZ{side}1', round(z[0], 4), f'Joint screws, {side.lower()} (Z): pattern cell centres (layout)')
        P.add(f'RibZ{side}2', round(z[-1], 4), '')
    # feet: the outermost even columns (column 0's cells: three across the bottom) clear of the ends
    x_lo = P['XBack'] + P['CaseChamfer'] + P['PatternClear'] + P['GrooveW'] / 2
    x_hi = P['XFront'] - P['CaseChamfer'] - P['PatternClear'] - P['GrooveW'] / 2
    js = [j for j in range(-40, 41, 2) if lat.column_x(j) - lat.tip >= x_lo and lat.column_x(j) + lat.tip <= x_hi]
    feet = []
    for i, j in ((1, js[0]), (2, js[-1])):
        P.add(f'FootX{i}', round(lat.column_x(j), 4), f'Feet, {"back" if i == 1 else "front"} pair (X): pattern cell centres (layout)')
    m = P['GrooveW'] / 2 + 0.2
    for face, name in ((CP.BOTTOM, 'FootBotZ'), (CP.RIGHT, 'FootSideY')):
        found = lat.cells_on_face(face, 0, m)
        found = sorted(found, key=lambda sw: lat.face_coord(face, sw[1]))
        for i, (sv, w) in ((1, found[0]), (2, found[-1])):
            P.add(f'{name}{i}', round(lat.face_coord(face, w), 4), '')
            feet += [(js[0], sv), (js[-1], sv)]
    # power button: centre of the lowest whole cell in the middle column of the front pattern
    # (case_pattern.front_grooves centres its lattice on the face)
    yc, zc = (P['YTop'] + P['YBot']) / 2, (P['ZLeft'] + P['ZRight']) / 2
    lowest = P['YBot'] + P['CaseChamfer'] + P['PatternClear'] + P['GrooveW'] / 2 + P['HexP'] / 2
    P.add('ButtonY', round(yc + math.ceil((lowest - yc) / P['HexP']) * P['HexP'], 4), 'Power button centre (layout)')
    P.add('ButtonZ', round(zc, 4), '')
    return lat, feet


def keepouts(P):
    """Outlines on the long faces the pattern grooves stay clear of."""
    r, h, pk = P['FanOpeningD'] / 2 + P['GrillLip'], P['FanHoleSpacing'] / 2, P['GrillPeak']
    out = []
    for x, tip in ((P['PullFanX'], 1), (P['PushFanX'], -1)):
        out.append(CP.outline_face(CP.pill_pts(x, P['FanY'], 2 * r, 2 * r, tip, pk), 'XY', P['ZLeft']))
        out += [CP.outline_face(CP.circle_pts(x + sx * h, P['FanY'] + sy * h, P['CsinkD'] / 2), 'XY', P['ZLeft'])
                for sx in (1, -1) for sy in (1, -1)]
    out.append(CP.outline_face(CP.circle_pts(P['RearFanX'], P['FanY'], r), 'XY', P['ZRight']))
    for x, tip in ((P['VentBackX'], 1), (P['VentFrontX'], -1)):
        out.append(CP.outline_face(CP.pill_pts(x, P['VentZ'], P['VentL'] + 2 * P['GrillLip'],
                                               P['VentW'] + 2 * P['GrillLip'], tip, pk), 'XZ', P['YTop']))
    out.append(CP.outline_face(CP.circle_pts(P['TabX'], P['TabZ'], P['AccessD'] / 2 * math.sqrt(2)), 'XZ', P['YTop']))
    for side, y in (('Top', P['YTop']), ('Bot', P['YBot'])):
        out += [CP.outline_face(CP.circle_pts(P['JointX'], P[f'RibZ{side}{i}'], P['CsinkD'] / 2), 'XZ', y) for i in (1, 2)]
    return out


def finish(doc, P, lat, feet, front, back):
    """Cut the seam zigzag and the hex pattern (long faces and the front) into the halves: Part::Cuts over the parametric bodies,
    with the pattern and seam as fixed shapes (rebuilt each time this script runs)."""
    foot_cells = {(j, round(sv % lat.perimeter, 3)) for j, sv in feet}

    def protect(cells):  # always groove the seam (it hides the joint) and the foot cells (keys)
        cols = {j for j, _ in cells}
        return {0, 1} <= cols or any((j, round(lat.cell_s(j, m) % lat.perimeter, 3)) in foot_cells for j, m in cells)
    pattern = doc.addObject('Part::Feature', 'HexPattern')
    # front: clear of the hub's port opening (the pattern runs over the lips round it)
    assert P['HubLipT'] - P['GrooveD'] >= 1.2 - 1e-9, 'hub lips too thin under the pattern grooves'
    y0 = P['HubY0'] + P['HubPort1'] - P['HubSlotMargin']
    y1 = P['HubY0'] + P['HubPort1'] + 3 * P['HubPortPitch'] + P['HubSlotMargin']
    z0, z1 = P['HubZ'] - P['HubT'] / 2 - P['HubClear'], P['HubZ'] + P['HubT'] / 2 + P['HubClear']
    face = CP.front_grooves(P, [CP.outline_face([(y0, z0), (y1, z0), (y1, z1), (y0, z1)], 'YZ', P['XFront'])])
    pattern.Shape = Part.makeCompound(CP.grooves(lat, keepouts(P), protect).Solids + face)
    pattern.Visibility = False
    for body, is_front in ((front, True), (back, False)):
        name = 'CaseFront' if is_front else 'CaseBack'
        seam = doc.addObject('Part::Feature', name + 'Seam')
        seam.Shape = CP.teeth(lat, is_front)
        trimmed = doc.addObject('Part::Cut', name + 'Trimmed')
        trimmed.Base, trimmed.Tool = body, seam
        final = doc.addObject('Part::Cut', name)
        final.Base, final.Tool = trimmed, pattern
        for o in (body, seam, trimmed):
            o.Visibility = False
    doc.recompute()
    # OCC can fail a cut quietly (the result is just the base): check each removed what it should
    for name in ('CaseFront', 'CaseBack'):
        for cut in (doc.getObject(name + 'Trimmed'), doc.getObject(name)):
            base, tool = cut.Base.Shape, cut.Tool.Shape
            want = sum(base.common(t).Volume for t in tool.Solids)  # tool: one solid per face
            got = base.Volume - cut.Shape.Volume
            ok = abs(want - got) < 0.01 * want + 1
            print(f'  {cut.Name}: cut removed {got:.0f} of {want:.0f} mm3 ok={ok}')


# ------------------------------------------------------------------ main
def build_case():
    doc = App.newDocument('fish_tank_case')
    P = Params(doc, CASE)
    lat, feet = layout(P)
    front = build_front(doc, P)
    end_face_chamfer(front, P, P['XFront'])
    back = build_back(doc, P)
    end_face_chamfer(back, P, P['XBack'])
    build_grills(doc, P)
    build_retainer(doc, P)
    build_foot(doc, P, 'TpuFootShort', 'FootShortH', 'FootShortRecess')
    build_foot(doc, P, 'TpuFootTall', 'FootTallH', 'FootTallRecess')
    finish(doc, P, lat, feet, front, back)
    return doc


# print orientation for each body: matrix applied to the board-frame shape before export
def print_matrix(name, P):
    if name == 'CaseFront':  # front face down
        return App.Matrix(0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, P['XFront'])
    if name == 'CaseBack':  # back face down
        return App.Matrix(0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, -P['XBack'])
    return App.Matrix()  # flat parts are modelled print-side down


# body: (quantity, STL name, accent colour)
PRINT_QTY = {'CaseFront': (1, 'case_front', False), 'CaseBack': (1, 'case_back', False),
             'FanGrill': (2, 'fan_grill', True), 'RearGrill': (1, 'rear_grill', True),
             'TopVentGrill': (2, 'top_vent_grill', True), 'HubRetainer': (1, 'hub_retainer', False),
             'TpuFootShort': (4, 'tpu_foot_short', False), 'TpuFootTall': (4, 'tpu_foot_tall', False)}

if os.environ.get('GEN_MAIN') == 'case':
    stldir = os.path.join(OUTDIR, 'stls')
    os.makedirs(stldir, exist_ok=True)
    doc = build_case()
    os.makedirs(CADDIR, exist_ok=True)
    path = os.path.join(CADDIR, doc.Name + '.FCStd')
    if os.path.exists(path):
        os.remove(path)  # regenerated from scratch: no FreeCAD .FCBak backup of the old one
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    doc = App.openDocument(path)
    doc.recompute()
    P = type('P', (), {'__getitem__': lambda self, k: float(doc.getObject('Params').get(k))})()
    for name, (qty, fname, accent) in PRINT_QTY.items():
        obj = doc.getObject(name)
        check(doc, obj)
        sh = obj.Shape.copy()
        sh.transformShape(print_matrix(name, P))
        export_stl(sh, stl_path(stldir, fname, qty, accent))
