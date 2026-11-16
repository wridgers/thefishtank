# Generates parametric FreeCAD models for the BC-250 push-pull fan shrouds.
# Run with: GEN_MAIN=shrouds freecadcmd scripts/gen_shrouds.py   (env OUTDIR = project directory;
# FCStd files go to OUTDIR/cad, printable STLs to OUTDIR/stls with Voron-style names)
import math, os, re
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
    ('XEnd', 61.55, 'End wall outer face (X)'),
    ('ScoopBaseZ', 2.1, 'Entry scoop: arc centre height'),
    ('ScoopTopZ', 23.35, 'Entry scoop: tip height (outer surface)'),
    ('HiScoopBaseZ', 17.7, 'End-wall scoop: arc centre / tangent height'),
    ('HiScoopTopZ', 40.6, 'End-wall scoop: tip height (outer surface)'),
    ('HiScoopOuterR', '=(HiScoopTopZ - HiScoopBaseZ) / sin(MaxOverhang)', 'End-wall scoop outer radius (derived)'),
    ('ClampX1', -55.0, 'Side clamp 1 position (X)'),
    ('ClampX2', 50.0, 'Side clamp 2 position (X)'),
    ('Notch1Y0', -44.5, 'End wall notch 1 (Ethernet jack)'), ('Notch1Y1', -27.5, ''), ('Notch1Z', 34.6, ''),
    # TPMS1, a 2x9 fine-pitch header near the I/O edge (measured on the real board), stands under the
    # end wall and into the duct: a pocket clears it
    ('PcbIoX', '=XEnd + 18', 'X of the PCB I/O edge (assembled: the end wall outer face is 18 mm from it)'),
    ('TpmFromIo', 15.0, 'TPMS1: distance from the PCB I/O edge'),
    ('TpmL', 18.0, 'TPMS1: length along the board (X)'),
    ('TpmFromEdge', 4.5, 'TPMS1: distance from the PCB long edge (-Y)'),
    ('TpmW', 4.0, 'TPMS1: width across the board (Y)'),
    ('TpmH', 6.0, 'TPMS1: height above the PCB'),
    ('TpmClear', 1.0, 'Clearance round TPMS1'),
    # surface-mount parts (not in the STEP) on the PCB under the end wall: up to 2 mm high
    ('SmdClear', 2.5, 'End wall relief over the PCB between the side walls: 2 mm parts + clearance'),
    ('M2ReliefY0', 48.0, 'Inside relief in end wall for the M.2 connector'), ('M2ReliefY1', 56.0, ''),
    ('M2ReliefZ', 40.1, ''), ('M2ReliefDepth', 2.5, 'Leaves WallT - M2ReliefDepth of wall'),
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
    s.rect('PcbEndX - HeaderFromEnd - HeaderW - HeaderClear', 'PcbEndX - HeaderFromEnd + HeaderClear',
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
    xe, xi, H, zc = P['XEnd'], P['XEnd'] - P['WallT'], P['Height'], P['HiScoopBaseZ']
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
    s.c('Horizontal', Lb); s.c('PointOnObject', Lb, 1, -1); s.px(Lb, 1, 'XEnd - WallT')
    s.co(Lb, 2, Lr, 1); s.c('Vertical', Lr); s.px(Lr, 1, 'XEnd')
    s.co(Lr, 2, Lt, 1); s.c('Horizontal', Lt); s.py(Lt, 1, 'Height')
    s.co(Lt, 2, Lw1, 1); s.c('Vertical', Lw1); s.px(Lw1, 1, 'XEnd - WallT')
    s.co(Lw1, 2, Ao, 1)
    s.dim('Radius', Ao, expr='HiScoopOuterR', name='HiScoopOuterR')
    s.px(Ao, 3, 'XEnd - WallT - (HiScoopOuterR - ScoopT)'); s.py(Ao, 3, 'HiScoopBaseZ')
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
    feat(body, P, 'Pocket', 'EndNotches', s, 'WallT + 2')
    # surface-mount relief: the end wall's PCB edge stands SmdClear off the board between the side walls
    s = SK(body, P, 'SmdReliefSketch', 'YZ_Plane', offset='XEnd + 1')
    s.rect('-(HalfW - WallT)', 'HalfW - WallT', 'Height - SmdClear', 'Height + 5')
    feat(body, P, 'Pocket', 'SmdRelief', s, 'WallT + 2')
    # TPMS1 pocket: down from the PCB plane, through the end wall and into the duct
    s = SK(body, P, 'TpmPocketSketch', 'XY_Plane', offset='Height + 5')
    s.rect('PcbIoX - TpmFromIo - TpmL - TpmClear', 'PcbIoX - TpmFromIo + TpmClear',
           '-PcbW / 2 + TpmFromEdge - TpmClear', '-PcbW / 2 + TpmFromEdge + TpmW + TpmClear')
    feat(body, P, 'Pocket', 'TpmPocket', s, 'TpmH + TpmClear + 5')
    s = SK(body, P, 'M2ReliefSketch', 'YZ_Plane', offset='XEnd - WallT')
    s.rect('M2ReliefY0', 'M2ReliefY1', 'M2ReliefZ', 'Height + 5')
    feat(body, P, 'Pocket', 'M2Relief', s, 'M2ReliefDepth', Reversed=True)
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
    w, l = P['PlateW'] / 2, P['PlateL'] / 2
    chamfer(body, P, 'EdgeChamfer', 'EdgeChamfer',
            lambda e: vertical_at([(x, y) for x in (w, -w) for y in (l, -l)])(e) or (
                at_z(P['PlateT'])(e) and (abs(abs(e.BoundBox.XMin) - w) < 1e-6 and e.BoundBox.XLength < 1e-6
                                          or abs(abs(e.BoundBox.YMin) - l) < 1e-6 and e.BoundBox.YLength < 1e-6)))
    chamfer(body, P, 'BedChamfer', 'BedChamfer', at_z(0))
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


def export_stl(shape, path, max_overhang=65.5):
    """Write shape, already in print orientation, as an STL ready to slice: lowest face on z=0, centred
    on x/y=0. Checks that it has faces on the bed and nothing else facing down steeper than
    max_overhang from vertical (the 65 deg design limit plus meshing slack)."""
    import MeshPart
    sh = shape.copy()
    b = sh.BoundBox
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
    return ok


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
    'tpu_fan_gasket': 5,    # main fans: one each side (shroud and case wall); backplate fan: one
    'tpu_fan_washer': 4,    # under the backplate fan's screw heads (the case screws are countersunk)
}

if os.environ.get('GEN_MAIN') == 'shrouds':  # (gen_case.py imports this module)
    stldir = os.path.join(OUTDIR, 'stls')
    os.makedirs(stldir, exist_ok=True)
    os.makedirs(CADDIR, exist_ok=True)
    for build in (build_push, build_pull, build_clamp, build_backfan_mount, build_tpu):
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
