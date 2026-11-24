# Generates parametric FreeCAD models for the board module: the BC-250 push-pull fan shrouds, the PCB
# clamps, the backplate fan mount, the fan hub frame, and the TPU fan gaskets and washers.
# Run with: GEN_MAIN=shrouds freecadcmd scripts/gen_shrouds.py   (env OUTDIR = project directory;
# FCStd files go to OUTDIR/cad, printable STLs to OUTDIR/stls with Voron-style names)
import json, math, os, re
import FreeCAD as App, Part, Sketcher

V = App.Vector
OUTDIR = os.environ.get('OUTDIR', '.')
CADDIR = os.path.join(OUTDIR, 'cad')  # every FreeCAD file of the project

# ---------------------------------------------------------------- parameters
# (alias, value-or-formula, comment). Formulas start with '='.
COMMON = [
    ('Height', 49.6, 'Fan face (bed, z=0) to PCB seating plane'),
    ('WallT', 4.0, 'Wall thickness'),
    ('FlangeT', 4.0, 'Fan flange plate thickness'),
    ('PcbW', 122.5, 'BC-250 PCB width (without the power extension), from the STEP'),
    ('HeatsinkHalfW', 60.0, 'Largest distance from PCB centreline to a heatsink side (STEP models: 60.0 / 59.5)'),
    ('HeatsinkClear', 0.5, 'Clearance between heatsink sides and the inside of the side walls'),
    ('HalfW', '=HeatsinkHalfW + HeatsinkClear + WallT', 'Half of outer width across the side walls (Y)'),
    ('FanOpeningD', 115.0, 'Fan air opening diameter'),
    ('FanHoleSpacing', 105.0, '120 mm fan screw pattern'),
    ('FanBossD', 9.5, 'Boss diameter around fan inserts'),
    ('FanBossH', 8.0, 'Fan boss height from fan face'),
    ('InsertD', 4.4, 'Heat-set insert hole dia (Voron M3x5x4: OD5 L4)'),
    ('InsertDepth', 5.5, 'Insert hole depth (insert length 4 + relief)'),
    ('ScrewD', 3.2, 'Screw clearance beyond the insert'),
    ('MaxOverhang', 65.0, 'Max overhang of any scoop/roof underside, deg from vertical'),
    ('ScoopT', 4.0, 'Scoop thickness at its root'),
    ('ScoopTip', 1.0, 'Scoop thickness at its edge: the inside is a larger arc than the outside, so each scoop '
                      'tapers (and its underside ends up shallower than MaxOverhang)'),
    ('PcbT', 1.6, 'BC-250 PCB thickness'),
    ('ClampPreload', 0.2, 'Clamp block top sits this far below PCB top'),
    ('ClampGap', 0.5, 'Clearance between the PCB end and the end clamp block'),
    ('ClampSideGap', 0.05, 'Clearance between each PCB long edge and its side clamp blocks (0.1 mm slack in all)'),
    ('ClampBlock', 9.0, 'Clamp block depth (perpendicular to PCB edge)'),
    ('ClampW', 9.0, 'Clamp block width (along PCB edge)'),
    ('ClampDrop', 11.0, 'Side clamp block: full-width height below its top'),
    ('FenceT', 2.0, 'Fence on the outer edge of each clamp block: the bar end butts against it'),
    ('FenceH', 2.5, 'Fence height above the clamp block (< clamp BarT)'),
    ('CornerChamfer', 1.0, 'Chamfer on the outer vertical corners'),
    ('BedChamfer', 0.5, 'Chamfer on edges touching the print bed (elephant foot)'),
    ('ClampTopZ', '=Height + PcbT - ClampPreload', 'Clamp block top'),
    ('ClampHoleOff', '=PcbW / 2 + ClampSideGap + ClampBlock / 2', 'Side clamp hole |Y|'),
    ('ScoopOuterR', '=(ScoopTopZ - ScoopBaseZ) / sin(MaxOverhang)', 'Entry scoop outer radius (derived)'),
    # zip tie mounts on the outside of both side walls, two per side: a block with a vertical slot (the
    # print direction, so no bridging) the tie runs through; the cable lies along the wall
    ('ZipX1', -25.0, 'Zip tie mount 1 position (X)'),
    ('ZipX2', 25.0, 'Zip tie mount 2 position (X)'),
    ('ZipTopZ', 20.0, 'Zip tie mount top face (Z); keeps the push shroud mounts clear of the case joint ribs'),
    ('ZipH', 8.0, 'Zip tie mount: height of its outer face'),
    ('ZipD', 4.0, 'Zip tie mount: depth out of the wall (45 deg slopes above and below: a trapezium)'),
    ('ZipW', 10.0, 'Zip tie mount: width along the wall'),
    ('ZipDip', 0.5, 'Zip tie mount: depth of the dip in the outer face that the cable rests in'),
    ('ZipDipR', 4.0, 'Zip tie mount: radius of that dip (shallow enough to print: under 45 deg)'),
    ('ZipSlotW', 4.0, 'Zip tie slot width (ties up to about 3.6 mm)'),
    ('ZipSlotT', 2.0, 'Zip tie slot thickness, against the wall'),
]
PUSH = COMMON + [
    ('XEntry', -64.65, 'Heatsink entry side outer face (X)'),
    ('XEnd', 64.65, 'Board end side outer face (X)'),
    ('ScoopBaseZ', 1.5, 'Entry scoop: arc centre height'),
    ('ScoopTopZ', 23.7, 'Entry scoop: tip height (outer surface)'),
    ('RoofInnerR', 16.5, 'End roof: inner (underside) arc radius'),
    ('RoofLandX', 38.65, 'End roof: where the underside, extended, meets the top plane (the roof edge stops '
                         'ScoopTip thick, just short of it)'),
    ('RoofArcZ', '=Height - RoofInnerR * sin(MaxOverhang) - (XEnd - WallT - RoofInnerR * (1 - cos(MaxOverhang)) - RoofLandX) / tan(MaxOverhang)',
     'End roof: arc centre height (derived)'),
    ('RoofLandEnd', '=XEnd - (RoofInnerR + WallT) * (1 - cos(MaxOverhang)) - (Height - RoofArcZ - (RoofInnerR + WallT) * sin(MaxOverhang)) * tan(MaxOverhang)',
     'End roof: where the outer slope meets the top plane (derived)'),
    ('PcbEndX', 45.0, 'X of the PCB end edge'),
    ('EndClampX0', '=PcbEndX + ClampGap', 'End clamp block start'),
    ('ClampX1', -60.0, 'Side clamp position (X); clears the PCB power-connector extension'),
    ('SideNotchX0', -40.0, '+Y wall component notch start'),
    ('SideNotchX1', 38.65, '+Y wall component notch end'),
    ('SideNotchDepth', 4.0, '+Y wall component notch depth'),
    # J4003, a 2x8 pin header on the PCB power extension (measured on the real board), stands under
    # the +Y wall at the end: a pocket clears it
    ('PcbExtW', 21.8, 'PCB power extension: width past the main board edge (+Y side, assembled)'),
    ('PcbExtEdge', '=PcbW / 2 + PcbExtW', 'Y of the PCB power extension outer edge'),
    ('HeaderFromEnd', 5.0, 'J4003: distance from the PCB end'),
    ('HeaderW', 5.0, 'J4003: size along the board (X)'),
    ('HeaderFromEdge', 4.0, 'J4003: distance from the power extension outer edge'),
    ('HeaderL', 20.0, 'J4003: length across the board (Y)'),
    ('HeaderH', 9.0, 'J4003: height above the PCB'),
    ('HeaderClear', 1.0, 'Clearance round J4003'),
    # CPU_FAN1, a 4 pin fan header beside J4003 (measured), sits right against the +Y wall's outer
    # face: a shallow relief in the wall gives its plug room
    ('FanHdrFromEnd', 15.0, 'CPU_FAN1: distance from the PCB end'),
    ('FanHdrW', 5.5, 'CPU_FAN1: size along the board (X)'),
    ('FanPlugH', 16.0, 'CPU_FAN1: height of the plug and its wires to clear, from the PCB'),
    ('FanReliefD', 1.0, 'CPU_FAN1 relief depth into the +Y wall'),
    ('FanReliefClear', 1.5, 'CPU_FAN1 relief: extra length past the header at each end'),
]
PULL = COMMON + [
    ('XEntry', -61.55, 'Heatsink entry side outer face (X)'),
    ('XEnd', 62.05, 'End wall outer face (X)'),
    # the end wall stands in the narrow gap between the I/O connectors and the M.2 SSD
    ('EndWallX', 17.5, 'End wall outer face: distance from the PCB I/O edge'),
    ('EndWallT', 2.0, 'End wall thickness (0.5 mm clear of the USB/DP connector backs and the SSD)'),
    ('SsdH', 9.0, 'M.2 SSD: top height above the PCB (measured)'),
    ('SsdClear', 1.0, 'Clearance between the end-wall scoop and the SSD'),
    ('ScoopBaseZ', 2.1, 'Entry scoop: arc centre height'),
    ('ScoopTopZ', 23.35, 'Entry scoop: tip height (outer surface)'),
    ('HiScoopBaseZ', 17.7, 'End-wall scoop: arc centre / tangent height'),
    ('HiScoopTopZ', '=Height - SsdH - SsdClear', 'End-wall scoop: tip height (outer surface), clear of the SSD'),
    ('HiScoopOuterR', '=(HiScoopTopZ - HiScoopBaseZ) / sin(MaxOverhang)', 'End-wall scoop outer radius (derived)'),
    ('ClampX1', -55.0, 'Side clamp 1 position (X)'),
    ('ClampX2', 50.0, 'Side clamp 2 position (X)'),
    ('Notch1Y0', -44.5, 'End wall notch 1 (Ethernet jack)'), ('Notch1Y1', -27.5, ''), ('Notch1Z', 34.6, ''),
    # TPMS1, a 2x9 fine-pitch header near the I/O edge (measured on the real board), stands under the
    # end wall and into the duct: a pocket clears it
    ('PcbIoX', '=XEnd + EndWallX', 'X of the PCB I/O edge'),
    ('TpmFromIo', 15.0, 'TPMS1: distance from the PCB I/O edge'),
    ('TpmL', 18.0, 'TPMS1: length along the board (X)'),
    ('TpmFromEdge', 4.5, 'TPMS1: distance from the PCB long edge (-Y)'),
    ('TpmW', 4.0, 'TPMS1: width across the board (Y)'),
    ('TpmH', 6.0, 'TPMS1: height above the PCB'),
    ('TpmClear', 1.0, 'Clearance round TPMS1'),
    # surface-mount parts (not in the STEP) on the PCB under the end wall: up to 2 mm high
    ('SmdClear', 2.5, 'End wall relief over the PCB between the side walls: 2 mm parts + clearance'),
]
CLAMP = [
    ('ClampBlock', 9.0, 'Must match shroud ClampBlock'),
    ('ClampGap', 0.5, 'Must match shroud ClampGap (the end clamp; at the side clamps the tongue reaches '
                      'ClampGap - ClampSideGap further over the PCB)'),
    ('ClampReach', 4.0, 'How far the tongue overlaps the PCB edge'),
    ('ClampW', 9.0, 'Bar width (must match shroud ClampW)'),
    ('BarT', 4.0, 'Bar thickness over the clamp block'),
    ('TongueT', 1.5, 'Tongue thickness: must fit between PCB and BC-250 backplate (2 mm gap)'),
    ('GussetC', 1.0, 'Chamfer gusset where the tongue meets the bar'),
    ('FenceGap', 0.2, 'Clearance between bar end and the shroud clamp-block fence'),
    ('BarHoleD', 3.4, 'M3 clearance'),
    ('EdgeChamfer', 0.5, 'Top edge chamfers'),
    ('BedChamfer', 0.5, 'Chamfer on edges touching the print bed (elephant foot)'),
    ('BarL', '=ClampBlock + ClampGap + ClampReach - FenceGap', 'Bar length'),
    ('HoleX', '=ClampReach + ClampGap + ClampBlock / 2', 'Hole position from the tongue tip (clamp block centre)'),
]

TPU = [
    ('FanSize', 120.0, 'Fan frame size'),
    ('GasketSize', 123.0, 'Gasket outer size: wider than the fan for a stronger web, <= shortest flange (pull shroud: 123.1)'),
    ('GasketCornerR', 6.0, 'Gasket corner radius'),
    ('FanOpeningD', 115.0, 'Match shroud FanOpeningD'),
    ('FanHoleSpacing', 105.0, 'Match shroud FanHoleSpacing'),
    ('GasketT', 1.5, 'Gasket thickness (TPU 95A)'),
    ('GasketHoleD', 3.6, 'Screw clearance through gasket'),
    ('WasherOD', 8.0, 'Washer under the M3 button head'),
    ('WasherID', 3.4, ''),
    ('WasherT', 1.5, ''),
    ('BedChamfer', 0.5, 'Chamfer on edges touching the print bed (elephant foot)'),
]
BACKFAN = [
    ('FanSize', 120.0, '120x15 slim fan blowing onto the BC-250 backplate'),
    ('FanOpeningD', 115.0, 'Fan air opening diameter'),
    ('FanHoleSpacing', 105.0, '120 mm fan screw pattern'),
    ('FanBossD', 9.5, 'Boss diameter around fan inserts'),
    ('FanBossH', 7.0, 'Fan boss height from fan face (insert hole + cone + 0.9)'),
    ('InsertD', 4.4, 'Heat-set insert hole dia (Voron M3x5x4: OD5 L4)'),
    ('InsertDepth', 5.5, 'Insert hole depth (insert length 4 + relief)'),
    ('ScrewD', 3.2, 'Screw clearance beyond the insert'),
    ('EdgeChamfer', 0.5, 'Top edge chamfers'),
    ('BedChamfer', 0.5, 'Chamfer on edges touching the print bed (elephant foot)'),
    ('PlateW', 124.0, 'Plate size along the board (X); >= TPU GasketSize'),
    ('PlateT', 4.0, 'Plate thickness'),
    ('FootSpanX', 68.45, 'Foot spacing along the board: pull shroud ClampX1 to push shroud ClampX1 holes, as assembled'),
    ('FootSpanY', 131.6, 'Foot spacing across the board: 2 * shroud ClampHoleOff'),
    ('FootSize', 9.0, 'Foot footprint, matches the clamp bar end (ClampBlock x ClampW)'),
    ('FootH', 5.0, 'Foot height above the plate; sets the fan-to-backplate gap (bosses clear the backplate by 1.5)'),
    ('FootHoleD', 3.4, 'M3 clearance'),
    ('PlateL', '=FootSpanY + FootSize', 'Plate size across the board (Y)'),
    # the PWM fan hub hangs under an extension of the plate toward the I/O end (behind the pull shroud),
    # held by its frame (fan_hub_frame), whose legs screw into inserts set through the extension
    # from the feet side; so the fan hub and its cables go in with the board
    ('HubPlugRoom', 20.0, 'Room for the fan plugs between the fan hub and the slim fan\'s gasket (PlateW wide)'),
    ('HubCX', '=-PlateW / 2 - HubPlugRoom - 42 / 2', 'Fan hub centre (X): its 42 mm width, past the gasket and the plug room'),
    ('HubCY', 0.0, 'Fan hub centre (Y): its long axis is along Y'),
    ('HubLegU', '=102 / 2 - 6 + (6 + 0.3 + 2 + 8 / 2) * cos(45)', 'Fan hub frame legs from the hub centre along it (Y): must match fan_hub_frame FanHubLegU'),
    ('HubLegV', '=42 / 2 - 6 + (6 + 0.3 + 2 + 8 / 2) * cos(45)', '... and across it (X): must match fan_hub_frame FanHubLegV'),
    ('HubLegD', 8.0, 'Must match fan_hub_frame FanHubLegD'), ('HubExtMargin', 3.0, 'Plate extension past the frame legs'),
    # two more feet hold the extension's end: they stand on the clamp bars of pull shroud ClampX2 and
    # share their inserts, as the first four share ClampX1's
    ('Foot2X', '=-FootSpanX / 2 - 105', 'Extension feet (X): pull shroud ClampX2 - ClampX1 = 105 (must match)'),
    ('HubExtX0', '=Foot2X - FootSize / 2 - 1', 'Plate extension end (X): past the extension feet (and the frame legs)'),
    ('HubWindowY', 43.0, 'Window in the extension (half width): the fan hub bears on the plate past it, near its ends'),
    ('HubWindowRim', 10.0, 'Extension rim round the window, at its ends (X)'),
]

# PWM fan hub (102 x 42 x 15, 6 mm corners): power and PWM inputs on its ends, fan ports on both long edges,
# so it is held by its face and corners only. It hangs under an extension of the backplate fan mount, held by
# a printed frame: a plate on its face, a 2 mm wall round its top, and four legs in the corner zones, each
# screwed (FHCS M3x25, flush) into an insert in the mount
FAN_HUB_FRAME = [
    ('FanHubL', 102.0, 'Fan hub length (Y)'), ('FanHubW', 42.0, 'Fan hub width (X)'),
    ('FanHubH', 15.0, 'Fan hub height off the mount plate'), ('FanHubR', 6.0, 'Fan hub corner radius'),
    ('FanHubLipClear', 0.1, 'Frame rim above the fan hub face'),
    ('FanHubPlateT', 4.0, 'Backplate fan mount plate the legs screw into: must match its PlateT'),
    ('FanHubRingT', '=25 - FanHubLipClear - FanHubH - FanHubPlateT', 'Frame plate thickness: an FHCS M3x25 flush in it ends flush with the far side of the mount plate'),
    ('FanHubWindowInset', 6.0, 'Frame window: inset from the fan hub outline'), ('FanHubWindowR', 8.0, 'Frame window corner radius'),
    ('FanHubWallT', 2.0, 'Wall round the fan hub top: thickness'), ('FanHubWallH', 2.0, '... and how far it reaches down the fan hub sides'),
    ('FanHubWallClear', 0.3, 'Wall to fan hub clearance'),
    ('FanHubLegD', 8.0, 'Frame leg diameter'), ('FanHubCornerR', 7.0, 'Frame plate corners, round about the legs (screw to edge)'),
    # legs on each corner's diagonal, against the wall: inside the corner zones, clear of the ports
    ('FanHubLegU', '=FanHubL / 2 - FanHubR + (FanHubR + FanHubWallClear + FanHubWallT + FanHubLegD / 2) * cos(45)',
     'Frame legs from the fan hub centre along it: must match backfan mount HubLegU'),
    ('FanHubLegV', '=FanHubW / 2 - FanHubR + (FanHubR + FanHubWallClear + FanHubWallT + FanHubLegD / 2) * cos(45)',
     '... and across it: must match backfan mount HubLegV'),
    ('ClearD', 3.4, 'M3 clearance'),
    ('CsinkD', 6.9, 'M3 countersink diameter at the surface (ISO 10642 head: 6.72 max)'),
    ('CsinkA', 90.0, 'M3 countersink included angle'),
    ('CsinkRun', 0.1, 'Cone runs this far (radially) into the hole, so it leaves no ledge'),
    ('BedChamfer', 0.5, 'Chamfer on edges touching the print bed (elephant foot)'),
]

PYFN = {'sin': lambda d: math.sin(math.radians(d)), 'cos': lambda d: math.cos(math.radians(d)),
        'tan': lambda d: math.tan(math.radians(d)), 'sqrt': math.sqrt, 'abs': abs}


class Params:
    def __init__(self, doc, table):
        self.names = [n for n, _, _ in table]
        self.vals = {}
        self.sheet = doc.addObject('Spreadsheet::Sheet', 'Params')
        sh = self.sheet
        sh.set('A1', 'Parameter'); sh.set('B1', 'Value'); sh.set('C1', 'Notes')
        for i, (name, val, note) in enumerate(table, start=2):
            sh.set(f'A{i}', name)
            sh.set(f'B{i}', str(val))
            sh.setAlias(f'B{i}', name)
            sh.set(f'C{i}', note)
            if not isinstance(val, str):
                self.vals[name] = float(val)
        pending = [(n, v[1:]) for n, v, _ in table if isinstance(v, str)]
        while pending:
            left = []
            for n, f in pending:
                try:
                    self.vals[n] = self.py(f)
                except NameError:
                    left.append((n, f))
            if len(left) == len(pending):
                raise ValueError(f'unresolvable params: {left}')
            pending = left
        sh.setColumnWidth('A', 140); sh.setColumnWidth('C', 380)

    def add(self, name, val, note=''):
        """Append a parameter worked out by the script (e.g. from a computed layout)."""
        i = len(self.names) + 2
        self.sheet.set(f'A{i}', name); self.sheet.set(f'B{i}', str(val))
        self.sheet.setAlias(f'B{i}', name); self.sheet.set(f'C{i}', note)
        self.names.append(name)
        self.vals[name] = float(val)

    def py(self, expr):
        return float(eval(expr, dict(PYFN), dict(self.vals)))

    def fc(self, expr):
        return re.sub(r'\b(' + '|'.join(sorted(self.names, key=len, reverse=True)) + r')\b', r'Params.\1', expr)

    def __getitem__(self, k):
        return self.vals[k]


class SK:
    """Sketch builder: geometry + constraints, dimensions bound to spreadsheet expressions."""
    def __init__(self, body, P, name, plane, offset=0.0):
        self.P = P
        self.s = body.newObject('Sketcher::SketchObject', name)
        org = {f.Role: f for f in body.Origin.OriginFeatures}
        self.s.AttachmentSupport = [(org[plane], '')]
        self.s.MapMode = 'FlatFace'
        self.offset_expr = None
        if isinstance(offset, str):
            self.offset_expr = offset
            offset = P.py(offset)
        self.s.AttachmentOffset = App.Placement(V(0, 0, offset), App.Rotation())
        if self.offset_expr:
            self.s.setExpression('.AttachmentOffset.Base.z', P.fc(self.offset_expr))

    def line(self, a, b):
        return self.s.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))

    def arc(self, c, r, a0, a1):
        return self.s.addGeometry(Part.ArcOfCircle(Part.Circle(V(c[0], c[1], 0), V(0, 0, 1), r),
                                                   math.radians(a0), math.radians(a1)))

    def circle(self, c, r):
        return self.s.addGeometry(Part.Circle(V(c[0], c[1], 0), V(0, 0, 1), r))

    def c(self, *args):
        return self.s.addConstraint(Sketcher.Constraint(*args))

    def dim(self, kind, *args, expr, name=None, angle=False):
        v = self.P.py(expr)
        i = self.s.addConstraint(Sketcher.Constraint(kind, *args, math.radians(v) if angle else v))
        if name:
            self.s.renameConstraint(i, name)
        try:
            float(expr)
        except ValueError:
            self.s.setExpression(f'Constraints[{i}]', self.P.fc(expr))
        return i

    # helpers
    def px(self, g, pos, expr, name=None): return self.dim('DistanceX', g, pos, expr=expr, name=name)
    def py(self, g, pos, expr, name=None): return self.dim('DistanceY', g, pos, expr=expr, name=name)
    def co(self, g1, p1, g2, p2): return self.c('Coincident', g1, p1, g2, p2)

    def polygon(self, pts):
        """Closed polygon; pts are (xexpr, yexpr) strings. Every vertex fixed by expressions."""
        n = len(pts)
        num = [(self.P.py(x), self.P.py(y)) for x, y in pts]
        L = [self.line(num[i], num[(i + 1) % n]) for i in range(n)]
        for i in range(n):
            self.co(L[i], 2, L[(i + 1) % n], 1)
            self.px(L[i], 1, pts[i][0]); self.py(L[i], 1, pts[i][1])
        return L

    def rounded_rect(self, half, r):
        """Square centred on the origin, side 2 * half, corners rounded to radius r."""
        h, R = self.P.py(half), self.P.py(r)
        L = [self.line((-h + R, -h), (h - R, -h)), self.line((h, -h + R), (h, h - R)),
             self.line((h - R, h), (-h + R, h)), self.line((-h, h - R), (-h, -h + R))]
        A = [self.arc((sx * (h - R), sy * (h - R)), R, a, a + 90)
             for sx, sy, a in [(1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)]]
        for i in range(4):
            self.c('Tangent', L[i], 2, A[i], 1)
            self.c('Tangent', A[i], 2, L[(i + 1) % 4], 1)
        self.c('Horizontal', L[0]); self.c('Horizontal', L[2])
        self.c('Vertical', L[1]); self.c('Vertical', L[3])
        self.py(L[0], 1, f'-{half}'); self.px(L[1], 1, half)
        self.py(L[2], 1, half); self.px(L[3], 1, f'-{half}')
        self.dim('Radius', A[0], expr=r)
        for a in A[1:]:
            self.c('Equal', A[0], a)
        return L, A

    def rect(self, x0, x1, y0, y1):
        return self.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def new_part(name, table):
    doc = App.newDocument(name)
    P = Params(doc, table)
    body = doc.addObject('PartDesign::Body', 'Body')
    body.Label = name
    return doc, P, body


def feat(body, P, kind, name, sketch, length, **kw):
    f = body.newObject(f'PartDesign::{kind}', name)
    f.Profile = sketch.s
    f.Type = 'Length'
    f.Length = P.py(length)
    try:
        float(length)
    except ValueError:
        f.setExpression('Length', P.fc(length))
    for k, v in kw.items():
        setattr(f, k, v)
    return f


def mirror(body, name, originals):
    """Mirror features across the XZ plane (Y -> -Y), kept in the body's feature chain."""
    tip = body.Tip
    m = body.Document.addObject('PartDesign::Mirrored', name)
    body.insertObject(m, tip, True)
    m.Originals = originals
    m.MirrorPlane = ({f.Role: f for f in body.Origin.OriginFeatures}['XZ_Plane'], [''])
    body.Tip = m
    return m


def chamfer(body, P, name, size, pred):
    """PartDesign chamfer on every edge of the current tip that satisfies pred(edge)."""
    body.Document.recompute()
    prev = body.Tip
    names = [f'Edge{i}' for i, e in enumerate(prev.Shape.Edges, start=1) if pred(e)]
    c = body.newObject('PartDesign::Chamfer', name)
    c.Base = (prev, names)
    c.Size = P.py(size)
    c.setExpression('Size', P.fc(size))
    prev.Visibility = False
    return c


def at_z(z):
    return lambda e: abs(e.BoundBox.ZMin - z) < 1e-6 and abs(e.BoundBox.ZMax - z) < 1e-6


def vertical_at(pts, tol=1e-6):
    """Straight edges parallel to Z through any of the (x, y) points."""
    def pred(e):
        b = e.BoundBox
        return (b.XLength < tol and b.YLength < tol and b.ZLength > tol and
                any(abs(b.XMin - x) < tol and abs(b.YMin - y) < tol for x, y in pts))
    return pred


def shroud_chamfers(body, P):
    x0, x1, h = P['XEntry'], P['XEnd'], P['HalfW']
    corner = vertical_at([(x, y) for x in (x0, x1) for y in (h, -h)])

    def ok(e):
        try:
            return body.Tip.Shape.makeChamfer(P['CornerChamfer'], [e]).isValid()
        except Exception:
            return False
    # OCC can't chamfer some corners (push shroud entry side, where the scoop root and both wall ends
    # share one face): cut those with a 45 deg triangular pocket instead, run past the corner
    body.Document.recompute()
    bad = [(b.XMin, b.YMin) for b in (e.BoundBox for e in body.Tip.Shape.Edges if corner(e) and not ok(e))]
    if bad:
        s = SK(body, P, 'CornerCutSketch', 'XY_Plane')
        for x, y in bad:
            X = 'XEntry' if abs(x - x0) < 1e-6 else 'XEnd'
            Y = 'HalfW' if y > 0 else '-HalfW'
            sx, sy = ('+', '-') if X == 'XEntry' else ('-', '+'), ('+', '-') if Y == 'HalfW' else ('-', '+')
            s.polygon([(f'{X} {sx[0]} (CornerChamfer + 0.5)', f'{Y} {sy[0]} 0.5'),
                       (f'{X} {sx[1]} 0.5', f'{Y} {sy[0]} 0.5'),
                       (f'{X} {sx[1]} 0.5', f'{Y} {sy[1]} (CornerChamfer + 0.5)')])
        feat(body, P, 'Pocket', 'CornerCut', s, 'Height + 10', Reversed=True)
    chamfer(body, P, 'CornerChamfer', 'CornerChamfer', lambda e: corner(e) and ok(e))
    chamfer(body, P, 'BedChamfer', 'BedChamfer', at_z(0))


def flange_and_fan_bosses(body, P, outline=('XEntry', 'XEnd', '-HalfW', 'HalfW'), thick='FlangeT'):
    sk = SK(body, P, 'FlangeSketch', 'XY_Plane')
    sk.rect(*outline)
    ci = sk.circle((0, 0), P['FanOpeningD'] / 2)
    sk.co(ci, 3, -1, 1)
    sk.dim('Diameter', ci, expr='FanOpeningD', name='FanOpening')
    feat(body, P, 'Pad', 'Flange', sk, thick)

    def four(name, dia_expr, offset=0.0):
        s = SK(body, P, name, 'XY_Plane', offset)
        h = P['FanHoleSpacing'] / 2
        cs = [s.circle((sx * h, sy * h), P.py(dia_expr) / 2) for sx in (1, -1) for sy in (1, -1)]
        for g, (sx, sy) in zip(cs, [(1, 1), (1, -1), (-1, 1), (-1, -1)]):
            s.px(g, 3, ('' if sx > 0 else '-') + 'FanHoleSpacing / 2')
            s.py(g, 3, ('' if sy > 0 else '-') + 'FanHoleSpacing / 2')
        s.dim('Diameter', cs[0], expr=dia_expr)
        for g in cs[1:]:
            s.c('Equal', cs[0], g)
        return s
    feat(body, P, 'Pad', 'FanBosses', four('FanBossSketch', 'FanBossD'), 'FanBossH')
    feat(body, P, 'Pocket', 'FanInsertHoles', four('FanInsertSketch', 'InsertD'), 'InsertDepth', Reversed=True)
    feat(body, P, 'Pocket', 'FanScrewHoles', four('FanScrewSketch', 'ScrewD'), 'FanBossH', Reversed=True)
    # 45 deg cone from insert bore down to screw hole, so the bore ceiling needs no bridging
    feat(body, P, 'Pocket', 'FanInsertCone', four('FanInsertConeSketch', 'InsertD', 'InsertDepth'),
                '(InsertD - ScrewD) / 2', Reversed=True, TaperAngle=-45)


def taper_arc(C, Ro, tip_deg, x_root, z_root, tip_t):
    """Inside arc of a tapered scoop: tangent to the vertical x = x_root at height z_root (the root,
    ScoopT inside the outside arc) and through the point tip_t inside the outer arc's tip, measured
    toward its centre C. Returns (centre, radius, tip point, tip angle about the centre)."""
    a = math.radians(tip_deg)
    q = (C[0] + (Ro - tip_t) * math.cos(a), C[1] + (Ro - tip_t) * math.sin(a))
    dx, dz = q[0] - x_root, q[1] - z_root
    r = (dx * dx + dz * dz) / (2 * abs(dx))
    c = (x_root + math.copysign(r, dx), z_root)
    return c, r, q, math.degrees(math.atan2(q[1] - c[1], q[0] - c[0]))


def entry_scoop(body, P):
    """Low scoop on the heatsink-entry side: rises from the flange edge, curves inward, stops where
    its outside reaches MaxOverhang; the inside is a larger arc, tapering it to ScoopTip."""
    s = SK(body, P, 'EntryScoopSketch', 'XZ_Plane')
    A = P['MaxOverhang']; Ro = P['ScoopOuterR']
    xe, zb = P['XEntry'], P['ScoopBaseZ']
    C = (xe + Ro, zb)
    tip = lambda r: (C[0] + r * math.cos(math.radians(180 - A)), zb + r * math.sin(math.radians(180 - A)))
    # the inside stays vertical up to the flange top before curving, so the flange (which stops at the
    # scoop's inside face) leaves no step on either face
    zf = P['FlangeT']
    Ci, Ri, q, aq = taper_arc(C, Ro, 180 - A, xe + P['ScoopT'], zf, P['ScoopTip'])
    Lv0 = s.line((xe, 0), (xe, zb))
    Ao = s.arc(C, Ro, 180 - A, 180)
    Le = s.line(tip(Ro), q)
    Ai = s.arc(Ci, Ri, aq, 180)
    Lv1 = s.line((xe + P['ScoopT'], zf), (xe + P['ScoopT'], 0))
    Lb = s.line((xe + P['ScoopT'], 0), (xe, 0))
    s.c('Horizontal', Lb); s.c('PointOnObject', Lb, 2, -1); s.px(Lb, 2, 'XEntry')
    s.px(Lb, 1, 'XEntry + ScoopT')
    s.co(Lb, 2, Lv0, 1); s.c('Vertical', Lv0)
    s.c('Tangent', Lv0, 2, Ao, 2)
    s.dim('Radius', Ao, expr='ScoopOuterR', name='ScoopOuterR')
    s.dim('Angle', Ao, expr='MaxOverhang', angle=True)
    s.py(Ao, 3, 'ScoopBaseZ')
    s.co(Ao, 1, Le, 1); s.co(Le, 2, Ai, 1)
    s.c('PointOnObject', Ao, 3, Le)  # the edge face points at the outside arc's centre
    s.dim('Distance', Le, expr='ScoopTip', name='ScoopTip')
    s.py(Ai, 3, 'FlangeT')
    s.c('Tangent', Ai, 2, Lv1, 1); s.c('Vertical', Lv1)
    s.co(Lv1, 2, Lb, 1)
    feat(body, P, 'Pad', 'EntryScoop', s, '2 * HalfW', SideType='Symmetric')


def roof_outer(s, P, x_entry_close):
    """Outer silhouette of the push shroud's end roof. Returns (geo ids). If x_entry_close, closes the
    profile back along the top to XEntry (side-wall silhouette)."""
    A = P['MaxOverhang']; Ri = P['RoofInnerR']; Ro = Ri + P['WallT']
    xe, zc, H = P['XEnd'], P['RoofArcZ'], P['Height']
    C = (xe - Ro, zc)
    a = math.radians(A)
    P3 = (C[0] + Ro * math.cos(a), zc + Ro * math.sin(a))
    L1 = s.line((xe, 0), (xe, zc))
    Ao = s.arc(C, Ro, 0, A)
    L2 = s.line(P3, (P['RoofLandEnd'], H))  # the outer slope runs straight onto the top plane
    xt = P['XEntry'] if x_entry_close else P['RoofLandX'] + P['ScoopTip'] * math.tan(a)
    L4 = s.line((P['RoofLandEnd'], H), (xt, H))
    s.c('Vertical', L1); s.px(L1, 1, 'XEnd')
    s.c('Tangent', L1, 2, Ao, 1)
    s.dim('Radius', Ao, expr='RoofInnerR + WallT')
    s.dim('Angle', Ao, expr='MaxOverhang', angle=True)
    s.py(Ao, 3, 'RoofArcZ')
    s.c('Tangent', Ao, 2, L2, 1)
    s.co(L2, 2, L4, 1); s.c('Horizontal', L4); s.py(L4, 1, 'Height')
    return L1, Ao, L2, L4


def push_end_roof(body, P):
    s = SK(body, P, 'EndRoofSketch', 'XZ_Plane')
    L1, Ao, L2, L4 = roof_outer(s, P, False)
    A = math.radians(P['MaxOverhang']); Ri = P['RoofInnerR']
    xi = P['XEnd'] - P['WallT']; zc = P['RoofArcZ']
    C = (xi - Ri, zc)
    P7 = (C[0] + Ri * math.cos(A), zc + Ri * math.sin(A))
    # the roof edge: a ScoopTip-high face instead of the knife edge where the underside meets the top
    xk, zk = P['RoofLandX'] + P['ScoopTip'] * math.tan(A), P['Height'] - P['ScoopTip']
    Lk = s.line((xk, P['Height']), (xk, zk))
    L5 = s.line((xk, zk), P7)
    Ai = s.arc(C, Ri, 0, P['MaxOverhang'])
    L6 = s.line((xi, zc), (xi, 0))
    L0 = s.line((xi, 0), (P['XEnd'], 0))
    s.co(L4, 2, Lk, 1); s.c('Vertical', Lk); s.dim('Distance', Lk, expr='ScoopTip', name='RoofTip')
    s.co(Lk, 2, L5, 1)
    s.c('Tangent', L5, 2, Ai, 2)
    s.co(Ao, 3, Ai, 3)
    s.dim('Radius', Ai, expr='RoofInnerR', name='RoofInnerR')
    s.dim('Angle', Ai, expr='MaxOverhang', angle=True, name='RoofOverhang')
    s.c('Tangent', Ai, 1, L6, 1); s.c('Vertical', L6)
    s.co(L6, 2, L0, 1); s.c('Horizontal', L0); s.c('PointOnObject', L0, 1, -1); s.co(L0, 2, L1, 1)
    feat(body, P, 'Pad', 'EndRoof', s, '2 * HalfW', SideType='Symmetric')


def side_walls(body, P, roof):
    # XZ sketch normal is -Y; plane at Y = -(HalfW - WallT), pad WallT toward -Y, then mirror.
    s = SK(body, P, 'SideWallSketch', 'XZ_Plane', offset='HalfW - WallT')
    H = P['Height']
    if roof:
        L1, Ao, L2, L4 = roof_outer(s, P, True)
        L5 = s.line((P['XEntry'], H), (P['XEntry'], 0))
        L0 = s.line((P['XEntry'], 0), (P['XEnd'], 0))
        s.co(L4, 2, L5, 1); s.c('Vertical', L5); s.px(L5, 1, 'XEntry')
        s.co(L5, 2, L0, 1); s.c('Horizontal', L0); s.c('PointOnObject', L0, 1, -1)
        s.co(L0, 2, L1, 1)
    else:
        s.rect('XEntry', 'XEnd', '0', 'Height')
    pad = feat(body, P, 'Pad', 'SideWall', s, 'WallT')
    return pad, mirror(body, 'SideWallMirror', [pad])


def side_clamps(body, P, xs, start=None):
    """Clamp blocks outside the side walls with 45 deg undersides; bar + M3 screw into an insert.
    With start, the first block runs from x = start (flush with the shroud end) instead of being centred."""
    pads = []
    for i, x in enumerate(xs, start=1):
        far = f'{x} + ClampW / 2'
        s = SK(body, P, f'SideClamp{i}Sketch', 'YZ_Plane', offset=far if start and i == 1 else x)
        # yi is inside the wall, past a corner chamfer, so a block refills the chamfer above its underside;
        # the block's inner face locates on the PCB edge (PcbW / 2 + ClampSideGap)
        # the fence (yo..yf) stands FenceH above the block so the bar can't swing round its screw
        yi, yl, yo = 'HalfW - CornerChamfer - 0.5', 'PcbW / 2 + ClampSideGap', 'PcbW / 2 + ClampSideGap + ClampBlock'
        yf = f'{yo} + FenceT'
        zf = 'ClampTopZ - ClampDrop'
        s.polygon([(yi, f'{zf} - ({yf} - ({yi}))'), (yf, zf), (yf, 'ClampTopZ + FenceH'),
                   (yo, 'ClampTopZ + FenceH'), (yo, 'ClampTopZ'),
                   (yl, 'ClampTopZ'), (yl, 'Height'), (yi, 'Height')])
        if start and i == 1:
            pads.append(feat(body, P, 'Pad', f'SideClamp{i}', s, f'{far} - ({start})', Reversed=True))
        else:
            pads.append(feat(body, P, 'Pad', f'SideClamp{i}', s, 'ClampW', SideType='Symmetric'))
    mirror(body, 'SideClampMirror', pads)


def zip_tie_mounts(body, P):
    """Two zip tie mounts on the outside of each side wall (+Y, then mirrored)."""
    pads = []
    for i, x in enumerate(('ZipX1', 'ZipX2'), start=1):
        s = SK(body, P, f'ZipMount{i}Sketch', 'YZ_Plane', offset=x)
        s.polygon([('HalfW - 0.5', 'ZipTopZ - ZipH - ZipD - 0.5'), ('HalfW + ZipD', 'ZipTopZ - ZipH'),
                   ('HalfW + ZipD', 'ZipTopZ'), ('HalfW - 0.5', 'ZipTopZ + ZipD + 0.5')])
        pads.append(feat(body, P, 'Pad', f'ZipMount{i}', s, 'ZipW', SideType='Symmetric'))
    mirror(body, 'ZipMountMirror', pads)
    # the dip the cable rests in, along the wall
    for i, x in enumerate(('ZipX1', 'ZipX2'), start=1):
        s = SK(body, P, f'ZipDip{i}Sketch', 'YZ_Plane', offset=x)
        for sy in ('', '-'):
            g = s.circle((P.py(f'{sy}(HalfW + ZipD + ZipDipR - ZipDip)'), P.py('ZipTopZ - ZipH / 2')), P['ZipDipR'])
            s.px(g, 3, f'{sy}(HalfW + ZipD + ZipDipR - ZipDip)'); s.py(g, 3, 'ZipTopZ - ZipH / 2')
            s.dim('Radius', g, expr='ZipDipR')
        feat(body, P, 'Pocket', f'ZipDip{i}', s, 'ZipW + 2', SideType='Symmetric')
    # slots, down from above the mounts to just above the flange, beside the wall
    s = SK(body, P, 'ZipSlotSketch', 'XY_Plane', offset='ZipTopZ + ZipD + 1')
    for x in ('ZipX1', 'ZipX2'):
        for y0, y1 in (('HalfW', 'HalfW + ZipSlotT'), ('-HalfW - ZipSlotT', '-HalfW')):
            s.rect(f'{x} - ZipSlotW / 2', f'{x} + ZipSlotW / 2', y0, y1)
    feat(body, P, 'Pocket', 'ZipSlots', s, 'ZipTopZ + ZipD + 1 - FlangeT - 0.5')


def holes(body, P, name, z, pts, dia, depth):
    """Equal holes pocketed down from height z; pts: list of (xexpr, yexpr) centres."""
    s = SK(body, P, name + 'Sketch', 'XY_Plane', offset=z)
    cs = []
    for x, y in pts:
        g = s.circle((P.py(x), P.py(y)), P.py(dia) / 2)
        s.px(g, 3, x); s.py(g, 3, y); cs.append(g)
    s.dim('Diameter', cs[0], expr=dia)
    for g in cs[1:]:
        s.c('Equal', cs[0], g)
    feat(body, P, 'Pocket', name + 'Holes', s, depth)


def clamp_holes(body, P, pts):
    """pts: list of (xexpr, yexpr) hole centres; insert from the top of the clamp blocks."""
    holes(body, P, 'ClampInsert', 'ClampTopZ', pts, 'InsertD', 'InsertDepth')
    holes(body, P, 'ClampScrew', 'ClampTopZ', pts, 'ScrewD', 'InsertDepth + 4')


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


def cut_through(body, P, name, s, thickness):
    """Pocket symmetric about the sketch plane (sketch placed mid-wall)."""
    return feat(body, P, 'Pocket', name, s, thickness, SideType='Symmetric')


def countersinks(body, P, name, plane, face, pts, hole, d='CsinkD', angle='CsinkA'):
    """Countersinks round the holes (diameter hole) at pts, from the outer face (sketch offset face)
    down into the hole, so the screw heads sit flush."""
    s = SK(body, P, name + 'Sketch', plane, face)
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


def teardrop(s, cu, cv, d, tip, psi='45'):
    """Hole of diameter d with a point toward tip ('+u', '-u', '+v' or '-v') whose sides touch the circle psi deg
    either side of it: prints without support when u is the print's up direction (steepest overhang
    90 - psi; 45 is the usual teardrop)."""
    P = s.P
    cx, cy, r, ps = P.py(cu), P.py(cv), P.py(d) / 2, P.py(psi)
    th = {'+u': 0, '+v': 90, '-u': 180, '-v': 270}[tip]
    pt = lambda a, rr=r: (cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a)))
    A = s.arc((cx, cy), r, th + ps, th + 360 - ps)
    T = pt(th, r / math.cos(math.radians(ps)))
    L1 = s.line(pt(th + 360 - ps), T)
    L2 = s.line(T, pt(th + ps))
    s.c('Tangent', L1, 1, A, 2); s.c('Tangent', L2, 2, A, 1); s.co(L1, 2, L2, 1)
    s.px(A, 3, cu); s.py(A, 3, cv)
    s.dim('Radius', A, expr=f'({d}) / 2')
    if tip[1] == 'u':
        s.px(L1, 2, f'({cu}) {tip[0]} ({d}) / 2 / cos({psi})'); s.py(L1, 2, cv)
    else:
        s.px(L1, 2, cu); s.py(L1, 2, f'({cv}) {tip[0]} ({d}) / 2 / cos({psi})')


def rounded_rect(s, P, cx, cy, hl, hw, r):
    """Rounded rectangle centred on (cx, cy): half length hl (u), half width hw (v), corner radius r."""
    X, Y, L, W, R = (P.py(e) for e in (cx, cy, hl, hw, r))
    L1 = s.line((X - L + R, Y - W), (X + L - R, Y - W)); L2 = s.line((X + L, Y - W + R), (X + L, Y + W - R))
    L3 = s.line((X + L - R, Y + W), (X - L + R, Y + W)); L4 = s.line((X - L, Y + W - R), (X - L, Y - W + R))
    A = [s.arc((X + sx * (L - R), Y + sy * (W - R)), R, a, a + 90)
         for sx, sy, a in [(1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)]]
    for i, Ln in enumerate((L1, L2, L3, L4)):
        s.c('Tangent', Ln, 2, A[i], 1); s.c('Tangent', A[i], 2, (L2, L3, L4, L1)[i], 1)
    s.c('Horizontal', L1); s.c('Horizontal', L3); s.c('Vertical', L2); s.c('Vertical', L4)
    s.py(L1, 1, f'({cy}) - ({hw})'); s.px(L2, 1, f'({cx}) + ({hl})'); s.py(L3, 1, f'({cy}) + ({hw})')
    s.px(L4, 1, f'({cx}) - ({hl})'); s.dim('Radius', A[0], expr=r)
    for a in A[1:]:
        s.c('Equal', A[0], a)


def seg_dist(p, a, b):
    """Distance from point p to the segment a-b (2D)."""
    ax, ay = b[0] - a[0], b[1] - a[1]
    if ax == ay == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def build_push():
    doc, P, body = new_part('fan_shroud_push', PUSH)
    flange_and_fan_bosses(body, P, ('XEntry + ScoopT', 'XEnd', '-HalfW', 'HalfW'))  # the scoop root is the edge
    side_walls(body, P, roof=True)
    entry_scoop(body, P)
    push_end_roof(body, P)
    # PCB end clamp block sitting on the roof land
    s = SK(body, P, 'EndClampSketch', 'XZ_Plane')
    x0, x1, x2 = 'EndClampX0', 'EndClampX0 + ClampBlock', 'EndClampX0 + ClampBlock + FenceT'
    zb = lambda x: f'Height - ({x} - RoofLandX) / tan(MaxOverhang) + 1'
    s.polygon([(x0, zb(x0)), (x2, zb(x2)), (x2, 'ClampTopZ + FenceH'), (x1, 'ClampTopZ + FenceH'),
               (x1, 'ClampTopZ'), (x0, 'ClampTopZ')])
    feat(body, P, 'Pad', 'EndClamp', s, 'ClampW', SideType='Symmetric')
    # component clearance notch in +Y wall (XZ normal is -Y; plane at Y=HalfW+1, cut toward -Y)
    s = SK(body, P, 'SideNotchSketch', 'XZ_Plane', offset='-(HalfW + 1)')
    s.rect('SideNotchX0', 'SideNotchX1', 'Height - SideNotchDepth', 'Height + 5')
    feat(body, P, 'Pocket', 'SideNotch', s, 'WallT + 2', Reversed=True)
    # J4003 pin header pocket: down from the PCB plane, through the +Y wall into the duct
    s = SK(body, P, 'HeaderPocketSketch', 'XZ_Plane', offset='-(HalfW + 1)')
    # (its far side lines up with the roof edge, so the two make one face instead of a 0.2 mm jog;
    # that still clears the header by 0.79 mm)
    s.rect('PcbEndX - HeaderFromEnd - HeaderW - HeaderClear', 'RoofLandX + ScoopTip * tan(MaxOverhang)',
           'Height - HeaderH - HeaderClear', 'Height + 5')
    feat(body, P, 'Pocket', 'HeaderPocket', s,
         'HalfW + 1 - (PcbExtEdge - HeaderFromEdge - HeaderL - HeaderClear)', Reversed=True)
    # CPU_FAN1 plug relief: FanReliefD into the +Y wall's outer face, down from the PCB plane
    s = SK(body, P, 'FanReliefSketch', 'XZ_Plane', offset='-(HalfW + 1)')
    s.rect('PcbEndX - FanHdrFromEnd - FanHdrW - FanReliefClear', 'PcbEndX - FanHdrFromEnd + FanReliefClear',
           'Height - FanPlugH', 'Height + 5')
    feat(body, P, 'Pocket', 'FanRelief', s, 'FanReliefD + 1', Reversed=True)
    zip_tie_mounts(body, P)
    # chamfer the entry corners before the side clamps go on: the clamps (flush with the entry end)
    # fill the chamfer back in above their 45 deg undersides
    shroud_chamfers(body, P)
    side_clamps(body, P, ['ClampX1'], start='XEntry')
    clamp_holes(body, P, [('ClampX1', 'ClampHoleOff'), ('ClampX1', '-ClampHoleOff'),
                          ('EndClampX0 + ClampBlock / 2', '0')])
    return doc, body


def build_pull():
    doc, P, body = new_part('fan_shroud_pull', PULL)
    flange_and_fan_bosses(body, P, ('XEntry + ScoopT', 'XEnd', '-HalfW', 'HalfW'))  # the scoop root is the edge
    side_walls(body, P, roof=False)
    entry_scoop(body, P)
    # end wall + scoop that branches off it
    s = SK(body, P, 'EndWallSketch', 'XZ_Plane')
    # (outside arc as before: concentric with a ScoopT-thinner arc tangent to the wall; the inside
    # is a larger arc tangent to the wall at the same height, tapering the scoop to ScoopTip)
    A = P['MaxOverhang']; Ro = P['HiScoopOuterR']; R0 = Ro - P['ScoopT']
    xe, xi, H, zc = P['XEnd'], P['XEnd'] - P['EndWallT'], P['Height'], P['HiScoopBaseZ']
    C = (xi - R0, zc)
    zw = zc + math.sqrt(Ro ** 2 - R0 ** 2)
    aw = math.degrees(math.acos(R0 / Ro))
    tip = lambda r: (C[0] + r * math.cos(math.radians(A)), zc + r * math.sin(math.radians(A)))
    Ci, Ri, q, aq = taper_arc(C, Ro, A, xi, zc, P['ScoopTip'])
    Lb = s.line((xi, 0), (xe, 0))
    Lr = s.line((xe, 0), (xe, H))
    Lt = s.line((xe, H), (xi, H))
    Lw1 = s.line((xi, H), (xi, zw))
    Ao = s.arc(C, Ro, aw, A)
    Le = s.line(tip(Ro), q)
    Ai = s.arc(Ci, Ri, 0, aq)
    Lw2 = s.line((xi, zc), (xi, 0))
    s.c('Horizontal', Lb); s.c('PointOnObject', Lb, 1, -1); s.px(Lb, 1, 'XEnd - EndWallT')
    s.co(Lb, 2, Lr, 1); s.c('Vertical', Lr); s.px(Lr, 1, 'XEnd')
    s.co(Lr, 2, Lt, 1); s.c('Horizontal', Lt); s.py(Lt, 1, 'Height')
    s.co(Lt, 2, Lw1, 1); s.c('Vertical', Lw1); s.px(Lw1, 1, 'XEnd - EndWallT')
    s.co(Lw1, 2, Ao, 1)
    s.dim('Radius', Ao, expr='HiScoopOuterR', name='HiScoopOuterR')
    s.px(Ao, 3, 'XEnd - EndWallT - (HiScoopOuterR - ScoopT)'); s.py(Ao, 3, 'HiScoopBaseZ')
    s.py(Ao, 2, 'HiScoopBaseZ + HiScoopOuterR * sin(MaxOverhang)', name='HiScoopOverhang')
    s.py(Ai, 3, 'HiScoopBaseZ')
    s.co(Ao, 2, Le, 1); s.co(Le, 2, Ai, 2); s.c('PointOnObject', Ao, 3, Le)
    s.dim('Distance', Le, expr='ScoopTip')
    s.c('Tangent', Ai, 1, Lw2, 1); s.c('Vertical', Lw2)
    s.co(Lw2, 2, Lb, 1)
    feat(body, P, 'Pad', 'EndWall', s, '2 * HalfW', SideType='Symmetric')
    side_clamps(body, P, ['ClampX1', 'ClampX2'])
    # component notches in end wall (YZ normal +X; plane at X=XEnd+1, pocket toward -X)
    s = SK(body, P, 'EndNotchSketch', 'YZ_Plane', offset='XEnd + 1')
    s.rect('Notch1Y0', 'Notch1Y1', 'Notch1Z', 'Height + 5')
    feat(body, P, 'Pocket', 'EndNotches', s, 'EndWallT + 2')
    # surface-mount relief: the end wall's PCB edge stands SmdClear off the board between the side walls
    s = SK(body, P, 'SmdReliefSketch', 'YZ_Plane', offset='XEnd + 1')
    s.rect('-(HalfW - WallT)', 'HalfW - WallT', 'Height - SmdClear', 'Height + 5')
    feat(body, P, 'Pocket', 'SmdRelief', s, 'EndWallT + 2')
    # TPMS1 pocket: down from the PCB plane, through the end wall and into the duct
    s = SK(body, P, 'TpmPocketSketch', 'XY_Plane', offset='Height + 5')
    s.rect('PcbIoX - TpmFromIo - TpmL - TpmClear', 'PcbIoX - TpmFromIo + TpmClear',
           '-PcbW / 2 + TpmFromEdge - TpmClear', '-PcbW / 2 + TpmFromEdge + TpmW + TpmClear')
    feat(body, P, 'Pocket', 'TpmPocket', s, 'TpmH + TpmClear + 5')
    clamp_holes(body, P, [(x, y) for x in ('ClampX1', 'ClampX2') for y in ('ClampHoleOff', '-ClampHoleOff')])
    zip_tie_mounts(body, P)
    shroud_chamfers(body, P)
    return doc, body


def build_tpu():
    """TPU fan isolation: gasket between fan and shroud flange, washers under the screw heads,
    so the fan is sandwiched in TPU and only the screw shank passes (with clearance) through it."""
    doc, P, body = new_part('fan_isolation_tpu', TPU)
    body.Label = 'Gasket'
    s = SK(body, P, 'GasketSketch', 'XY_Plane')
    s.rounded_rect('GasketSize / 2', 'GasketCornerR')
    ci = s.circle((0, 0), P['FanOpeningD'] / 2)
    s.co(ci, 3, -1, 1)
    s.dim('Diameter', ci, expr='FanOpeningD')
    h = P['FanHoleSpacing'] / 2
    cs = []
    for sx, sy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        g = s.circle((sx * h, sy * h), P['GasketHoleD'] / 2)
        s.px(g, 3, ('' if sx > 0 else '-') + 'FanHoleSpacing / 2')
        s.py(g, 3, ('' if sy > 0 else '-') + 'FanHoleSpacing / 2')
        cs.append(g)
    s.dim('Diameter', cs[0], expr='GasketHoleD')
    for g in cs[1:]:
        s.c('Equal', cs[0], g)
    feat(body, P, 'Pad', 'GasketPad', s, 'GasketT')
    r_hole = P['GasketHoleD'] / 2 + 1e-3
    chamfer(body, P, 'BedChamfer', 'BedChamfer',
            lambda e: at_z(0)(e) and e.BoundBox.XLength > 2 * r_hole)  # not the small screw holes
    washer = doc.addObject('PartDesign::Body', 'Washer')
    s = SK(washer, P, 'WasherSketch', 'XY_Plane')
    for name in ('WasherOD', 'WasherID'):
        g = s.circle((0, 0), P[name] / 2)
        s.co(g, 3, -1, 1)
        s.dim('Diameter', g, expr=name)
    feat(washer, P, 'Pad', 'WasherPad', s, 'WasherT')
    chamfer(washer, P, 'BedChamfer', 'BedChamfer',
            lambda e: at_z(0)(e) and e.BoundBox.XLength > P['WasherID'] + 1e-3)
    return doc, body, washer


def build_backfan_mount():
    """Plate holding a 120x15 slim fan over the BC-250 backplate. Prints plate-down; the fan
    mounts to the bed face with inserts like the shrouds, and four feet stand on the clamp bars
    of pull shroud ClampX1 and push shroud ClampX1, sharing their inserts via longer screws."""
    doc, P, body = new_part('backfan_mount', BACKFAN)
    flange_and_fan_bosses(body, P, ('-PlateW / 2', 'PlateW / 2', '-PlateL / 2', 'PlateL / 2'), 'PlateT')
    s = SK(body, P, 'FeetSketch', 'XY_Plane')
    feet = [(sx + 'FootSpanX / 2', sy + 'FootSpanY / 2') for sx in ('', '-') for sy in ('', '-')]
    for x, y in feet:
        s.rect(f'{x} - FootSize / 2', f'{x} + FootSize / 2', f'{y} - FootSize / 2', f'{y} + FootSize / 2')
    feat(body, P, 'Pad', 'Feet', s, 'PlateT + FootH')
    holes(body, P, 'FootScrew', 'PlateT + FootH', feet, 'FootHoleD', 'PlateT + FootH')
    # fan hub plate extension, overlapping the plate by 1 mm, with the frame leg inserts through it
    s = SK(body, P, 'HubPlateSketch', 'XY_Plane')
    s.rect('HubExtX0', '-PlateW / 2 + 1', '-PlateL / 2', 'PlateL / 2')
    feat(body, P, 'Pad', 'HubPlate', s, 'PlateT')
    s = SK(body, P, 'Feet2Sketch', 'XY_Plane')
    feet2 = [('Foot2X', sy + 'FootSpanY / 2') for sy in ('', '-')]
    for x, y in feet2:
        s.rect(f'{x} - FootSize / 2', f'{x} + FootSize / 2', f'{y} - FootSize / 2', f'{y} + FootSize / 2')
    feat(body, P, 'Pad', 'Feet2', s, 'PlateT + FootH')
    holes(body, P, 'Foot2Screw', 'PlateT + FootH', feet2, 'FootHoleD', 'PlateT + FootH')
    legs = [(f'HubCX {sx} HubLegV', f'HubCY {sy} HubLegU') for sx in ('+', '-') for sy in ('+', '-')]
    holes(body, P, 'HubInsert', 'PlateT', legs, 'InsertD', 'PlateT')
    s = SK(body, P, 'HubWindowSketch', 'XY_Plane', 'PlateT')
    s.rect('HubExtX0 + HubWindowRim', '-PlateW / 2 - HubWindowRim', 'HubCY - HubWindowY', 'HubCY + HubWindowY')
    feat(body, P, 'Pocket', 'HubWindow', s, 'PlateT')
    w, l, x0 = P['PlateW'] / 2, P['PlateL'] / 2, P['HubExtX0']
    corners = [(x, y) for x in (w, x0) for y in (l, -l)]
    on_rim = lambda b: (any(abs(b.XMin - x) < 1e-6 and b.XLength < 1e-6 for x in (w, x0))
                        or any(abs(b.YMin - y) < 1e-6 and b.YLength < 1e-6 for y in (l, -l)))
    chamfer(body, P, 'EdgeChamfer', 'EdgeChamfer',
            lambda e: vertical_at(corners)(e) and e.BoundBox.ZMax <= P['PlateT'] + 1e-6
            or (at_z(P['PlateT'])(e) and on_rim(e.BoundBox)))
    chamfer(body, P, 'BedChamfer', 'BedChamfer', at_z(0))
    return doc, body


def build_fan_hub_frame():
    """Frame holding the fan hub against the backplate fan mount's plate extension. Modelled in print
    orientation, outer face on the bed: local x along the fan hub, y across it, z from the frame's outer
    face toward the plate. Only the plate (on the face) and a 2 mm wall round the top touch the fan hub,
    so its ports and inputs stay free; the legs stand in the corner zones."""
    doc, P, body = new_part('fan_hub_frame', FAN_HUB_FRAME)
    hl, hw, r = 'FanHubL / 2', 'FanHubW / 2', 'FanHubR'
    # one plate: a rounded rectangle whose corners round about the legs, with a window over the middle
    s = SK(body, P, 'FanHubPlateSketch', 'XY_Plane')
    rounded_rect(s, P, '0', '0', 'FanHubLegU + FanHubCornerR', 'FanHubLegV + FanHubCornerR', 'FanHubCornerR')
    rounded_rect(s, P, '0', '0', f'{hl} - FanHubWindowInset', f'{hw} - FanHubWindowInset', 'FanHubWindowR')
    feat(body, P, 'Pad', 'FanHubPlate', s, 'FanHubRingT')
    # wall round the fan hub's top: stops it moving, reaching FanHubWallH down its sides
    c, t = 'FanHubWallClear', 'FanHubWallClear + FanHubWallT'
    s = SK(body, P, 'FanHubWallSketch', 'XY_Plane')
    rounded_rect(s, P, '0', '0', f'{hl} + {t}', f'{hw} + {t}', f'{r} + {t}')
    rounded_rect(s, P, '0', '0', f'{hl} + {c}', f'{hw} + {c}', f'{r} + {c}')
    feat(body, P, 'Pad', 'FanHubWall', s, 'FanHubRingT + FanHubLipClear + FanHubWallH')
    # legs on the corner diagonals, against the wall, out to the mount plate
    legs = [(sx * P['FanHubLegU'], sy * P['FanHubLegV']) for sx in (1, -1) for sy in (1, -1)]
    pts = [(f"{'' if x > 0 else '-'}FanHubLegU", f"{'' if y > 0 else '-'}FanHubLegV") for x, y in legs]
    s = SK(body, P, 'FanHubLegSketch', 'XY_Plane')
    cs = []
    for (x, y), (ex, ey) in zip(legs, pts):
        g = s.circle((x, y), P['FanHubLegD'] / 2); cs.append(g)
        s.px(g, 3, ex); s.py(g, 3, ey)
    s.dim('Diameter', cs[0], expr='FanHubLegD')
    for g in cs[1:]:
        s.c('Equal', cs[0], g)
    feat(body, P, 'Pad', 'FanHubLegs', s, 'FanHubRingT + FanHubLipClear + FanHubH')
    # screw holes, countersunk flush in the frame face (the bed face: the 90 deg cone prints as is)
    s = SK(body, P, 'FanHubHoleSketch', 'XY_Plane')
    cs = []
    for (x, y), (ex, ey) in zip(legs, pts):
        g = s.circle((x, y), P['ClearD'] / 2); cs.append(g)
        s.px(g, 3, ex); s.py(g, 3, ey)
    s.dim('Diameter', cs[0], expr='ClearD')
    for g in cs[1:]:
        s.c('Equal', cs[0], g)
    cut_through(body, P, 'FanHubHole', s, '2 * (FanHubRingT + FanHubLipClear + FanHubH) + 2')
    countersinks(body, P, 'FanHubCsink', 'XY_Plane', '0', pts, 'ClearD')

    # bed chamfer on the bed edges that take it together (greedy, in case OCC can't do some of them)
    body.Document.recompute()
    tip, keep = body.Tip.Shape, []
    csink = lambda e: hasattr(e.Curve, 'Radius') and abs(e.Curve.Radius - P['CsinkD'] / 2) < 0.2  # its cone is the chamfer
    for e in sorted((e for e in body.Tip.Shape.Edges if at_z(0)(e) and e.Length >= 1.0 and not csink(e)),
                    key=lambda e: -e.Length):
        try:
            if tip.makeChamfer(P['BedChamfer'], keep + [e]).isValid():
                keep.append(e)
        except Exception:
            pass
    chamfer(body, P, 'BedChamfer', 'BedChamfer', lambda e: any(e.isSame(k) for k in keep))
    return doc, body


def build_clamp():
    doc, P, body = new_part('pcb_clamp', CLAMP)
    # Side profile (XZ). x=0 is the tongue tip (over the PCB), x=BarL the outer end that butts
    # against the shroud's fence; z=0 is the face that presses on the PCB (printed on the bed).
    # (flat tongue pad first so the body keeps an identity placement for the chamfer dress-up)
    s = SK(body, P, 'TongueSketch', 'XY_Plane')
    s.rect('0', 'BarL', '-ClampW / 2', 'ClampW / 2')
    feat(body, P, 'Pad', 'Tongue', s, 'TongueT - EdgeChamfer')
    s = SK(body, P, 'ProfileSketch', 'XZ_Plane')
    xb = 'ClampReach + ClampGap'
    s.polygon([('0', '0'), ('BarL', '0'), ('BarL', 'BarT - EdgeChamfer'), ('BarL - EdgeChamfer', 'BarT'),
               (f'{xb} + EdgeChamfer', 'BarT'), (xb, 'BarT - EdgeChamfer'), (xb, 'TongueT + GussetC'),
               (f'{xb} - GussetC', 'TongueT'), ('EdgeChamfer', 'TongueT'), ('0', 'TongueT - EdgeChamfer')])
    feat(body, P, 'Pad', 'Bar', s, 'ClampW', SideType='Symmetric')
    s = SK(body, P, 'BarHoleSketch', 'XY_Plane', offset='BarT')
    g = s.circle((P['HoleX'], 0), P['BarHoleD'] / 2)
    s.px(g, 3, 'HoleX'); s.py(g, 3, '0')
    s.dim('Diameter', g, expr='BarHoleD')
    feat(body, P, 'Pocket', 'BarHole', s, 'BarT')
    w = P['ClampW'] / 2
    chamfer(body, P, 'BedChamfer', 'BedChamfer',
            lambda e: at_z(0)(e) or (e.BoundBox.ZMin > 1e-6 and e.BoundBox.XLength > 1e-6 and e.BoundBox.ZLength < 1e-6
                                     and abs(abs(e.BoundBox.YMin) - w) < 1e-6 and e.BoundBox.YLength < 1e-6))
    return doc, body


def check(doc, body):
    doc.recompute()
    ok = True
    for o in doc.Objects:
        if o.TypeId == 'Sketcher::SketchObject':
            bad = (o.ConflictingConstraints, o.RedundantConstraints, o.MalformedConstraints, o.PartiallyRedundantConstraints)
            if not o.FullyConstrained or any(bad):
                ok = False
                print(f'  SKETCH {o.Name}: full={o.FullyConstrained} conflict/redundant/malformed/partial={bad}')
        if 'Invalid' in o.State or 'Error' in o.State:
            ok = False
            print(f'  {o.Name} state={o.State}')
    sh = body.Shape
    print(f'  {doc.Name}: valid={sh.isValid()} solids={len(sh.Solids)} vol={sh.Volume:.0f}mm3 '
          f'bbox={sh.BoundBox} ok={ok}')
    return ok


def export_stl(shape, path, max_overhang=65.5, tight=False):
    """Write shape, already in print orientation, as an STL ready to slice: lowest face on z=0, centred
    on x/y=0. Checks that it has faces on the bed and nothing else facing down steeper than
    max_overhang from vertical (the 65 deg design limit plus meshing slack). tight: place it by the
    exact bounding box (the default, quick one can be loose on shapes with many faces; the locked
    parts keep the default, so their fingerprints don't move)."""
    import MeshPart
    sh = shape.copy()
    b = sh.optimalBoundingBox() if tight else sh.BoundBox
    sh.translate(V(-b.Center.x, -b.Center.y, -b.ZMin))
    mesh = MeshPart.meshFromShape(Shape=sh, LinearDeflection=0.02, AngularDeflection=0.1)
    bed = over = 0.0
    limit = math.sin(math.radians(max_overhang))
    for f in mesh.Facets:
        if max(p[2] for p in f.Points) < 1e-3:
            bed += f.Area
        elif -f.Normal.z > limit:
            over += f.Area
    mesh.write(path)
    ok = bed > 1.0 and over < 0.5
    print(f'  {os.path.basename(path)}: print check: on bed {bed:.0f} mm2, overhang > {max_overhang:g} deg '
          f'{over:.1f} mm2 ok={ok}')
    return check_lock(sh, path) and ok


# Parts that are printed and in use are locked: stls/locked.json holds a fingerprint of each one's
# exact (B-rep) shape, and a build that changes a locked part fails. Accept a change with
# `make relock` (LOCK_UPDATE=all) or lock more parts with `make relock PARTS=a.stl,b.stl`.
LOCK_TOL = {'volume': 1e-6, 'area': 1e-6, 'moments': 1e-6}  # relative; lengths are within 0.001 mm


def fingerprint(sh):
    """Size and shape of a part in print orientation: catches a resized or moved feature, but not a
    different triangulation of the same shape."""
    vol = sum(s.Volume for s in sh.Solids)
    com = sum((s.CenterOfMass * s.Volume for s in sh.Solids), V(0, 0, 0)) * (1 / vol)
    moments = sorted(m for s in sh.Solids for m in s.PrincipalProperties['Moments'])
    b = sh.BoundBox
    return {'volume': round(vol, 4), 'area': round(sh.Area, 4), 'size': [round(v, 4) for v in (b.XLength, b.YLength, b.ZLength)],
            'center_of_mass': [round(v, 4) for v in (com.x, com.y, com.z)], 'moments': [round(m, 2) for m in moments]}


def check_lock(sh, path):
    name = os.path.basename(path)
    lock_path = os.path.join(os.path.dirname(path), 'locked.json')
    locked = json.load(open(lock_path)) if os.path.exists(lock_path) else {}
    fp = fingerprint(sh)
    update = os.environ.get('LOCK_UPDATE', '')
    if update == 'all' and name in locked or name in update.split(','):
        locked[name] = fp
        with open(lock_path, 'w') as f:
            json.dump(dict(sorted(locked.items())), f, indent=2)
            f.write('\n')
        print(f'  {name}: locked')
        return True
    if name not in locked:
        return True
    ref, bad = locked[name], []
    for k, v in fp.items():
        if k in ('size', 'center_of_mass'):
            if any(abs(a - b) > 1e-3 for a, b in zip(v, ref[k])):
                bad.append(f'{k} {ref[k]} -> {v}')
        elif any(abs(a - b) > LOCK_TOL[k] * max(abs(b), 1.0) for a, b in zip(v if isinstance(v, list) else [v],
                                                                         ref[k] if isinstance(ref[k], list) else [ref[k]])):
            bad.append(f'{k} {ref[k]} -> {v}')
    if bad:
        print(f'  {name}: LOCKED (printed) part changed: {"; ".join(bad)}. To accept it, run '
              f'make relock PARTS={name} ok=False')
    return not bad


def stl_path(stldir, name, qty, accent=False):
    """Voron-style STL name: '[a]_' prefix for accent-colour parts, '_xN' suffix when more than one is
    needed. Earlier exports of the same part (any quantity, accent flag or the old 'Nx_' prefix) go first."""
    old = re.compile(r'^(\[a\]_)?(\d+x_)?' + re.escape(name) + r'(_x\d+)?\.stl$')
    for f in os.listdir(stldir):
        if old.match(f):
            os.remove(os.path.join(stldir, f))
    return os.path.join(stldir, ('[a]_' if accent else '') + name + (f'_x{qty}' if qty > 1 else '') + '.stl')


# How many of each printed part one build needs (the STL name's _xN suffix).
PRINT_QTY = {
    'fan_shroud_push': 1,
    'fan_shroud_pull': 1,
    'pcb_clamp': 7,         # one per clamp block: 3 on push shroud, 4 on pull shroud
    'backfan_mount': 1,
    'fan_hub_frame': 1,
    'tpu_fan_gasket': 5,    # main fans: one each side (shroud and case wall); backplate fan: one
    'tpu_fan_washer': 4,    # under the backplate fan's screw heads (the case screws are countersunk)
}

if os.environ.get('GEN_MAIN') == 'shrouds':  # (gen_frame.py imports this module)
    stldir = os.path.join(OUTDIR, 'stls')
    os.makedirs(stldir, exist_ok=True)
    os.makedirs(CADDIR, exist_ok=True)
    for build in (build_push, build_pull, build_clamp, build_backfan_mount, build_fan_hub_frame, build_tpu):
        doc, *bodies = build()
        path = os.path.join(CADDIR, doc.Name + '.FCStd')
        if os.path.exists(path):
            os.remove(path)  # regenerated from scratch: no FreeCAD .FCBak backup of the old one
        doc.saveAs(path)
        # check what the saved file produces when it is opened and recomputed from scratch
        App.closeDocument(doc.Name)
        doc = App.openDocument(path)
        doc.recompute()
        bodies = [doc.getObject(b) for b in ('Body', 'Washer') if doc.getObject(b)]
        for body in bodies:
            check(doc, body)
        for body in bodies:
            name = doc.Name if len(bodies) == 1 else f'tpu_fan_{body.Label.lower()}'
            export_stl(body.Shape, stl_path(stldir, name, PRINT_QTY[name]))
