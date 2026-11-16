# Builds the assembly of The Fish Tank (the BC-250 push-pull case). Must run inside the FreeCAD GUI (colours, Assembly joints).
# env: OUTDIR (project folder; the printed-part FCStd files are in its cad/), BC_STEP, FAN_STEP, LOG, SHOTS,
# optional SLIM_FAN_STEP (a STEP of the 120x15 slim fan; otherwise a model built from its dimensions)
import math, os, re, traceback
import FreeCAD as App, FreeCADGui as Gui, Part
from PySide import QtCore, QtGui

V, Rot = App.Vector, App.Rotation
OUT = os.environ['OUTDIR']  # project folder: BOM.md here, every FreeCAD file in cad/
CAD = os.path.join(OUT, 'cad')
LOG = open(os.environ['LOG'], 'w')


def log(*a):
    LOG.write(' '.join(str(x) for x in a) + '\n'); LOG.flush()


def color(obj, rgb, transparency=0):
    obj.ViewObject.ShapeColor = rgb
    obj.ViewObject.Transparency = transparency


def feature(doc, parent, name, shape, rgb, transparency=0):
    o = doc.addObject('Part::Feature', name)
    o.Shape = shape
    parent.addObject(o)
    color(o, rgb, transparency)
    return o


# ------------------------------------------------------------------ BC-250 board
def build_board():
    doc = App.newDocument('bc250_board')
    part = doc.addObject('App::Part', 'BC250')
    solids = Part.read(os.environ['BC_STEP']).Solids
    bb = lambda s: s.BoundBox
    pcb = [s for s in solids if bb(s).XMin > -0.1 and bb(s).XMax < 1.7][0]
    heatsink = max(solids, key=lambda s: s.Volume)
    backplate = [s for s in solids if bb(s).XMax < -1.5 and s.Volume > 50000][0]
    bracket = [s for s in solids if bb(s).YMin < -160][0]
    rear_tab = [s for s in solids if bb(s).YMax > 170][0]
    power = [s for s in solids if s not in (pcb, heatsink, backplate, bracket, rear_tab)][0]
    # STEP frame: x = board normal (heatsink +x), y = length (I/O end at -y), z = width.
    # Board frame: X along length from the I/O edge, Y across (PCB main area 0..122, power
    # extension at Y<0), Z normal with the heatsink on +Z, PCB = Z 0..1.6.
    m = App.Matrix(0, 1, 0, -pcb.BoundBox.YMin,
                   0, 0, 1, -(pcb.BoundBox.ZMax - 122.0),
                   1, 0, 0, 0)

    def tf(s):
        c = s.copy(); c.transformShape(m); return c
    feature(doc, part, 'PCB', tf(pcb), (0.08, 0.40, 0.18))
    feature(doc, part, 'Heatsink', tf(heatsink), (0.78, 0.79, 0.82))
    feature(doc, part, 'Backplate', tf(backplate), (0.55, 0.56, 0.58))
    feature(doc, part, 'IO_Bracket', tf(bracket), (0.70, 0.70, 0.72))
    feature(doc, part, 'PowerConnector', tf(power), (0.12, 0.12, 0.12))
    # Rear mounting tab overhangs the PCB end where the push shroud's roof sits; it has to come off.
    tab = doc.addObject('Part::Feature', 'RearTab_remove')
    tab.Shape = tf(rear_tab); tab.Visibility = False
    color(tab, (0.7, 0.2, 0.2))
    # Components missing from the STEP, from Fahad_Alduraibi's BC250.scad (CC BY-SA) dimensions.
    boxes = [('Ethernet', (-1, 17, 2), (22, 16, 14), (0.85, 0.85, 0.82)),
             ('USB_1', (-1, 40, 1.6), (18, 12, 16), (0.20, 0.30, 0.75)),
             ('DisplayPort', (-1, 57, 1.6), (14, 16, 7), (0.15, 0.15, 0.15)),
             ('USB_2', (-1, 78, 1.6), (18, 12, 16), (0.20, 0.30, 0.75)),
             ('Buttons', (7, 96, 1.6), (9, 9, 23), (0.90, 0.90, 0.90)),
             ('M2_Connector', (20.5, 110, 1.6), (22, 6, 8.5), (0.15, 0.15, 0.15)),
             # 2x8 pin header J4003 on the power extension, measured on the real board: 5 mm from the
             # PCB end, 4 mm from the extension's outer edge (y = -22.3), 9 mm high
             ('J4003_Header', (308 - 5 - 5, -22.3 + 4, 1.6), (5, 20, 9), (0.15, 0.15, 0.15)),
             # 4 pin fan header CPU_FAN1 beside it, measured: corner 15 mm from the PCB end and 9 mm
             # from the extension edge, pins 10 mm high
             ('CPU_FAN1_Header', (308 - 15 - 5.5, -22.3 + 9, 1.6), (5.5, 10, 10), (0.15, 0.15, 0.15)),
             # 2x9 fine-pitch header TPMS1 near the I/O edge, measured: 15 mm from the I/O edge, 4.5 mm
             # from the main edge (y = -0.5), 6 mm high
             ('TPMS1_Header', (15, -0.5 + 4.5, 1.6), (18, 4, 6), (0.15, 0.15, 0.15)),
             # M.2 2280 NVMe SSD, measured: 20 mm from the I/O edge, 6 mm from the y = 122 edge, top 9 mm
             # above the PCB; modelled from its standoff to its connector, on the standoff (7 mm)
             ('M2_SSD', (20, 34, 8.6), (22, 76, 2.0), (0.12, 0.12, 0.13))]
    for name, p, s, rgb in boxes:
        feature(doc, part, name, Part.makeBox(s[0], s[1], s[2], V(*p)), rgb)
    feature(doc, part, 'M2_Standoff', Part.makeCylinder(2.5, 7, V(31, 34.5, 1.6)), (0.8, 0.7, 0.3))
    # surface-mount parts behind the I/O connectors (not in the STEP), up to 2 mm high: a slab from the
    # connectors to the heatsink, 1.5 mm in from the PCB edges, round the parts already modelled
    smd = Part.makeBox(34, 119.5, 2, V(14, 1.0, 1.6))
    for o in part.Group:
        smd = smd.cut(o.Shape)
    feature(doc, part, 'SMD_Parts', smd.removeSplitter(), (0.10, 0.35, 0.20))
    doc.Comment = ('BC-250 board. PCB/heatsink/backplate/bracket from "Accurate 3D model of the AMD BC-250 board" '
                   'by torassk (Printables 1341336); I/O and M.2 boxes from Fahad_Alduraibi (Printables 1651082).')
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'bc250_board.FCStd'))
    return doc


# ------------------------------------------------------------------ 120 mm fan
def build_fan():
    # ARCTIC P12 Pro (120x120x25, 105 mm holes), shown by a Noctua NF-A12x25 STEP, which has the same frame
    # size and hole pattern.
    doc = App.newDocument('fan_120x25')
    part = doc.addObject('App::Part', 'Fan')
    solids = sorted(Part.read(os.environ['FAN_STEP']).Solids, key=lambda s: -s.Volume)
    feature(doc, part, 'Frame', solids[0], (0.12, 0.12, 0.13))
    feature(doc, part, 'Impeller', solids[1], (0.08, 0.08, 0.09))
    feature(doc, part, 'Hub', solids[2], (0.08, 0.08, 0.09))
    pads = feature(doc, part, 'Pads', Part.makeCompound(solids[3:]), (0.20, 0.20, 0.21))
    doc.Comment = ('Stand-in for the ARCTIC P12 Pro: the Noctua NF-A12x25 model, public domain, by djos_1475 '
                   '(Printables 273355). Fan axis Z, motor struts (outlet) on the -Z face, pad faces at Z=-1.5 '
                   'and Z=24.5, holes on a 105 mm square.')
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'fan_120x25.FCStd'))
    return doc


def build_slim_fan():
    # Thermalright TL-C12015B (120x120x15 slim, 105 mm holes), simplified; set SLIM_FAN_STEP to a STEP
    # of it to use that instead. Outlet face with motor struts at z=0, body to z=15.
    doc = App.newDocument('fan_120x15')
    part = doc.addObject('App::Part', 'Fan')
    if os.environ.get('SLIM_FAN_STEP'):
        solids = sorted(Part.read(os.environ['SLIM_FAN_STEP']).Solids, key=lambda s: -s.Volume)
        feature(doc, part, 'Frame', solids[0], (0.12, 0.12, 0.13))
        feature(doc, part, 'Impeller', Part.makeCompound(solids[1:]), (0.08, 0.08, 0.09))
        doc.Comment = 'Thermalright TL-C12015B from ' + os.path.basename(os.environ['SLIM_FAN_STEP'])
    else:
        frame = Part.makeBox(120, 120, 15, V(-60, -60, 0))
        for sx in (1, -1):
            for sy in (1, -1):
                corner = Part.makeBox(5, 5, 15, V(sx * 57.5 - 2.5, sy * 57.5 - 2.5, 0)).cut(
                    Part.makeCylinder(5, 15, V(sx * 55, sy * 55, 0)))
                frame = frame.cut(corner).cut(Part.makeCylinder(2.25, 15, V(sx * 52.5, sy * 52.5, 0)))
        frame = frame.cut(Part.makeCylinder(57.5, 15))
        for a in (45, 135, 225, 315):
            strut = Part.makeBox(42, 3, 2.5, V(18, -1.5, 0))
            strut.rotate(V(0, 0, 0), V(0, 0, 1), a)
            frame = frame.fuse(strut)
        frame = frame.fuse(Part.makeCylinder(21, 2.5)).removeSplitter()
        feature(doc, part, 'Frame', frame, (0.12, 0.12, 0.13))
        hub = Part.makeCylinder(20, 11.5, V(0, 0, 3))
        blades = []
        for i in range(9):
            b = Part.makeBox(37, 1.2, 10, V(19, -0.6, 3.5))
            b.rotate(V(38, 0, 8.5), V(1, 0, 0), 35)
            b.rotate(V(0, 0, 0), V(0, 0, 1), i * 40)
            blades.append(b)
        imp = hub.fuse(blades).common(Part.makeCylinder(56.5, 11.5, V(0, 0, 3)))
        feature(doc, part, 'Impeller', imp, (0.08, 0.08, 0.09))
        doc.Comment = ('Thermalright TL-C12015B, simplified: 120x120x15, 105 mm hole '
                       'pattern through the full frame, outlet (struts) on the z=0 face.')
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'fan_120x15.FCStd'))
    return doc


def build_psu():
    # Enhance ENP-8345L-OVT modular Flex ATX PSU, 165 x 81.5 x 40.5 (no drawing published: AC-face
    # layout as the Flex ATX FSP drawing). Local frame: x from the AC face (0) to the DC face (165),
    # y up from the bottom, z across (0..81.5, z=0 is the C14 side). C14 inlet 15 from that side and
    # 17.5 up; #6-32 holes on the AC face 5.6 from the z=81.5 side; the DC face takes air in (40 mm fan)
    # and carries the modular sockets, whose plugs are modelled as one block.
    doc = App.newDocument('psu_flex_atx')
    part = doc.addObject('App::Part', 'PSU')
    L, H, W = 165.0, 40.5, 81.5
    body = Part.makeBox(L, H, W)
    for y in (4.1, 36.1):
        body = body.cut(Part.makeCylinder(1.75, 6, V(0, y, W - 5.6), V(1, 0, 0)))
    feature(doc, part, 'Body', body, (0.18, 0.18, 0.19))
    c14 = Part.makeBox(3.2, 30.5, 23.5, V(-3.2, 17.5 - 15.25, 15 - 11.75))
    c14 = c14.cut(Part.makeBox(2.5, 20, 15, V(-3.2, 17.5 - 10, 15 - 7.5)))
    feature(doc, part, 'C14', c14, (0.08, 0.08, 0.08))
    guard = Part.makeCylinder(20, 0.6, V(L - 0.6, H - 20.35, 34), V(1, 0, 0)).cut(  # flush stamped grille
        Part.makeCylinder(18.5, 0.6, V(L - 0.6, H - 20.35, 34), V(1, 0, 0)))
    feature(doc, part, 'FanGuard', guard, (0.55, 0.55, 0.57))
    feature(doc, part, 'ModularPlugs', Part.makeBox(20, 24, 50, V(L, 10, 6)), (0.05, 0.05, 0.05))
    doc.Comment = ('Enhance ENP-8345L-OVT modular Flex ATX PSU (165 x 81.5 x 40.5), simplified; AC face as the '
                   'Flex ATX FSP drawing, modular plugs on the DC face as one block.')
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'psu_flex_atx.FCStd'))
    return doc


def build_hub():
    # Anker 4-port USB hub (A7516 / A8309), 108 x 31 x 10. Local frame: x along the hub from the cable
    # end, y from the port face (0) back to 31, z through the thickness.
    doc = App.newDocument('usb_hub_anker')
    part = doc.addObject('App::Part', 'Hub')
    f = Part.Face(Part.Wire(Part.makePolygon([V(0, 0, 0), V(108, 0, 0), V(108, 31, 0), V(0, 31, 0), V(0, 0, 0)])))
    body = f.extrude(V(0, 0, 10))
    body = body.makeFillet(4, [e for e in body.Edges if abs(e.BoundBox.ZLength - 10) < 1e-6 and e.BoundBox.YMin > 1])
    for i in range(4):
        x = 37.6 + i * 19.95
        body = body.cut(Part.makeBox(12.7, 12, 5.1, V(x - 6.35, 0, 2.35)))
    feature(doc, part, 'Body', body, (0.12, 0.12, 0.13))
    cable = Part.makeCylinder(2, 15, V(0, 15.5, 5), V(-1, 0, 0))
    feature(doc, part, 'Cable', cable, (0.05, 0.05, 0.05))
    doc.Comment = 'Anker 4-port USB hub (A7516 / A8309 size), simplified.'
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'usb_hub_anker.FCStd'))
    return doc


def build_button():
    # mosfet.party 16 mm backlit power button (latching adapter built in), simplified from the usual 16 mm
    # anti-vandal pushbutton:
    # 18 mm flat head with a white LED ring, M16 x 1 body, 19 mm hex nut, plug-in connector with four
    # leads. Local frame: panel face at z=0, head toward +z, body behind the panel toward -z.
    doc = App.newDocument('power_button_16mm')
    part = doc.addObject('App::Part', 'Button')
    head = Part.makeCylinder(9.0, 2.0)
    head = head.makeChamfer(0.5, [e for e in head.Edges if abs(e.BoundBox.ZMin - 2.0) < 1e-6])
    head = head.cut(Part.makeCylinder(6.6, 0.6, V(0, 0, 1.4)))
    head = head.fuse(Part.makeCylinder(7.9, 16, V(0, 0, -16))).removeSplitter()
    feature(doc, part, 'Body', head, (0.06, 0.06, 0.07))
    feature(doc, part, 'LedRing', Part.makeCylinder(6.6, 0.5, V(0, 0, 1.4)).cut(Part.makeCylinder(5.9, 0.5, V(0, 0, 1.4))),
            (0.95, 0.95, 0.97))
    feature(doc, part, 'Cap', Part.makeCylinder(5.8, 0.5, V(0, 0, 1.4)), (0.18, 0.18, 0.2))
    r = 19.0 / 2 / math.cos(math.radians(30))
    nut = Part.Face(Part.makePolygon([V(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), -7)
                                      for a in range(0, 361, 60)])).extrude(V(0, 0, 3))
    feature(doc, part, 'Nut', nut.cut(Part.makeCylinder(8, 3, V(0, 0, -7))), (0.75, 0.75, 0.78))
    feature(doc, part, 'Connector', Part.makeBox(18, 13, 22, V(-9, -6.5, -38)), (0.25, 0.62, 0.85))
    feature(doc, part, 'Leads', Part.makeCylinder(2.2, 20, V(0, 0, -58)), (0.75, 0.15, 0.1))
    doc.Comment = 'mosfet.party 16 mm backlit power button with built-in latching adapter, simplified.'
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'power_button_16mm.FCStd'))
    return doc


# ------------------------------------------------------------------ M3 hardware
def build_hardware():
    doc = App.newDocument('hardware_m3')
    # Heat-set insert, Voron M3x5x4: entry face at z=0, body toward +z.
    ins = doc.addObject('App::Part', 'Insert_M3x5x4')
    band = lambda z0, h, r: Part.makeCylinder(r, h, V(0, 0, z0))
    body = band(0, 1.3, 2.5).fuse(band(1.3, 1.4, 2.15)).fuse(band(2.7, 1.3, 2.5))
    body = body.cut(Part.makeCylinder(1.25, 4, V(0, 0, 0))).removeSplitter()
    feature(doc, ins, 'Insert', body, (0.85, 0.66, 0.28))

    def bhcs(length):
        # ISO 7380 M3: head dia 5.7, height 1.65, 2.0 hex socket. Bearing face at z=0, shank to -length.
        p = doc.addObject('App::Part', f'BHCS_M3x{length}')
        head = Part.makeCylinder(2.85, 0.4).fuse(Part.makeCone(2.85, 1.7, 1.25, V(0, 0, 0.4)))
        r = 1.0 / math.cos(math.radians(30))
        hexw = Part.makePolygon([V(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0.65)
                                 for a in range(0, 361, 60)])
        s = head.cut(Part.Face(hexw).extrude(V(0, 0, 1.1)))
        s = s.fuse(Part.makeCylinder(1.5, length, V(0, 0, -length))).removeSplitter()
        feature(doc, p, 'Screw', s, (0.10, 0.10, 0.11))
    def fhcs(name, length, dk, angle, d, socket=None):
        # Flat head (countersunk) screw: head top at z=0 (flush), cone of included angle down to the shank,
        # to -length.
        p = doc.addObject('App::Part', name)
        k = (dk - d) / 2 / math.tan(math.radians(angle / 2))
        s = Part.makeCone(d / 2, dk / 2, k, V(0, 0, -k))
        if socket:
            r = socket / 2 / math.cos(math.radians(30))
            hexw = Part.makePolygon([V(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), -1.1)
                                     for a in range(0, 361, 60)])
            s = s.cut(Part.Face(hexw).extrude(V(0, 0, 1.1)))
        s = s.fuse(Part.makeCylinder(d / 2, length - k, V(0, 0, -length))).removeSplitter()
        feature(doc, p, 'Screw', s, (0.10, 0.10, 0.11) if socket else (0.6, 0.6, 0.62))
    for length in (25, 20, 10):
        bhcs(length)
    for length in (40, 12):  # ISO 10642 M3: head dia 6.72 (theoretical), 90 deg, 2.0 hex socket
        fhcs(f'FHCS_M3x{length}', length, 6.72, 90, 3.0, 2.0)
    fhcs('FHCS_6_32x3_8', 9.525, 6.6, 82, 3.5)  # #6-32 x 3/8" flat head (82 deg), for the PSU
    doc.recompute()
    doc.saveAs(os.path.join(CAD, 'hardware_m3.FCStd'))
    return doc


def tidy_printed(name, rgb):
    doc = App.openDocument(os.path.join(CAD, name + '.FCStd'))
    for o in doc.Objects:
        if o.TypeId.startswith('PartDesign::') and o.TypeId != 'PartDesign::Body':
            o.Visibility = False
        if o.TypeId == 'Sketcher::SketchObject':
            o.Visibility = False
    for body in [o for o in doc.Objects if o.TypeId == 'PartDesign::Body']:
        body.Visibility = True
        color(body, rgb)
        body.Tip.Visibility = True
    # Part::Cut chains (the case halves: body -> seam trim -> hex pattern): show only the last cut
    cuts = [o for o in doc.Objects if o.TypeId == 'Part::Cut']
    for o in cuts:
        o.Base.Visibility = o.Tool.Visibility = False
    for o in cuts:
        if not any(c.Base == o for c in cuts):
            o.Visibility = True
            color(o, rgb)
    doc.recompute()
    doc.save()
    return doc


# ------------------------------------------------------------------ assembly
def build_assembly(board, fan, slim, psu, hub, button, hw, s_push, s_pull, clamp, mount, tpu, case):
    doc = App.newDocument('fish_tank')
    doc.saveAs(os.path.join(CAD, 'fish_tank.FCStd'))  # so links are stored relative
    lay = doc.addObject('Spreadsheet::Sheet', 'Layout')
    rows = [('BoardLength', 308.0, 'PCB length (I/O edge to far edge)'),
            ('BoardWidth', 122.5, 'PCB width without the power extension'),
            ('BoardY0', -0.5, 'Y of the PCB main edge (the power extension is beyond it, at -Y)'),
            ('BoardPcbT', 1.6, 'PCB thickness')]
    for i, (a, v, c) in enumerate(rows, start=1):
        lay.set(f'A{i}', a); lay.set(f'B{i}', str(v)); lay.setAlias(f'B{i}', a); lay.set(f'C{i}', c)

    asm = doc.addObject('Assembly::AssemblyObject', 'Assembly')
    asm.Label = 'FishTank'

    def link(parent, name, target, rot=Rot(), base=(0, 0, 0)):
        lk = doc.addObject('App::Link', name)
        lk.setLink(target)
        lk.Placement = App.Placement(V(*[0 if isinstance(b, str) else b for b in base]), rot)
        parent.addObject(lk)
        for axis, val in zip('xyz', base):
            if isinstance(val, str):
                lk.setExpression(f'.Placement.Base.{axis}', val)
        return lk

    brd = link(asm, 'BC250', board.getObject('BC250'))

    insert = hw.getObject('Insert_M3x5x4')
    m3x40, m3x25, m3x20 = hw.getObject('FHCS_M3x40'), hw.getObject('BHCS_M3x25'), hw.getObject('BHCS_M3x20')
    m3x10 = hw.getObject('BHCS_M3x10')
    K = case.Name + '#Params.'
    T = tpu.Name + '#Params.'
    far_face = f'-26 - {T}GasketT'  # fan far face (pads compressed to nothing)
    flip = Rot(V(1, 0, 0), 180)

    def side(name, sdoc, fan_rot, fan_z, clamps_side, end_clamp, mount_clamp):
        # mount_clamp: the side clamp whose screws come from the backplate fan mount instead
        P = sdoc.Name + '#Params.'
        C = clamp.Name + '#Params.'
        grp = doc.addObject('App::Part', name)
        asm.addObject(grp)
        link(grp, name + '_Shroud', sdoc.getObject('Body'))
        link(grp, name + '_FanGasket', tpu.getObject('Body'), flip, (0, 0, 0))
        link(grp, name + '_WallGasket', tpu.getObject('Body'), flip, (0, 0, far_face))
        link(grp, name + '_Fan', fan.getObject('Fan'), fan_rot, (0, 0, fan_z))
        h = P + 'FanHoleSpacing / 2'
        for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)], start=1):
            x, y = ('' if sx > 0 else '-') + h, ('' if sy > 0 else '-') + h
            link(grp, f'{name}_FanInsert{i}', insert, Rot(), (x, y, 0))
            # countersunk fan screws, flush with the case wall, through it, the TPU gasket and the fan
            wall_out = f'{far_face} - {T}GasketT - {K}FanStackClear - {K}CaseT'
            link(grp, f'{name}_FanScrew{i}_M3x40', m3x40, flip, (x, y, wall_out))
        n = 0
        top = f'{P}Height + {P}PcbT'
        for cx in clamps_side:
            for sgn, rz in (('', 90), ('-', -90)):
                n += 1
                hy = f'{sgn}{P}ClampHoleOff'
                link(grp, f'{name}_ClampBar{n}', clamp.getObject('Body'), Rot(V(0, 0, 1), rz),
                     (P + cx, f'{sgn}({P}ClampHoleOff - {C}HoleX)', top))  # bar hole on the block hole
                link(grp, f'{name}_ClampInsert{n}', insert, flip, (P + cx, hy, P + 'ClampTopZ'))
                if cx != mount_clamp:
                    link(grp, f'{name}_ClampScrew{n}_M3x10', m3x10, Rot(), (P + cx, hy, f'{top} + {C}BarT'))
        if end_clamp:
            n += 1
            hx = f'{P}EndClampX0 + {P}ClampBlock / 2'
            link(grp, f'{name}_ClampBar{n}', clamp.getObject('Body'), Rot(),
                 (f'{P}PcbEndX - {C}ClampReach', 0, top))
            link(grp, f'{name}_ClampInsert{n}', insert, flip, (hx, 0, P + 'ClampTopZ'))
            link(grp, f'{name}_ClampScrew{n}_M3x10', m3x10, Rot(), (hx, 0, f'{top} + {C}BarT'))
        return grp

    # Push shroud on the far (power) end; fan outlet (struts) faces the shroud.
    push = side('Push', s_push, flip, f'-1.5 - {tpu.Name}#Params.GasketT', ['ClampX1'], True, 'ClampX1')
    push.Placement = App.Placement(V(0, 0, 0), Rot(V(1, 0, 0), 180))
    push.setExpression('.Placement.Base.x', f'Layout.BoardLength - {s_push.Name}#Params.PcbEndX')
    push.setExpression('.Placement.Base.y', 'Layout.BoardY0 + Layout.BoardWidth / 2')
    push.setExpression('.Placement.Base.z', f'{s_push.Name}#Params.Height + Layout.BoardPcbT')
    # Pull shroud on the I/O end; fan inlet faces the shroud.
    pull = side('Pull', s_pull, Rot(), f'-24.5 - {tpu.Name}#Params.GasketT', ['ClampX1', 'ClampX2'], False, 'ClampX1')
    pull.Placement = App.Placement(V(0, 0, 0), Rot(V(0, 1, 0), 180))
    pull.setExpression('.Placement.Base.x', f'{s_pull.Name}#Params.EndWallX + {s_pull.Name}#Params.XEnd')
    pull.setExpression('.Placement.Base.y', 'Layout.BoardY0 + Layout.BoardWidth / 2')
    pull.setExpression('.Placement.Base.z', f'{s_pull.Name}#Params.Height + Layout.BoardPcbT')

    # Backplate fan: mount plate (fan face z=0, feet toward +z) standing on the clamp bars of
    # pull shroud ClampX1 and push shroud ClampX1; fan below it blowing toward the board (+Z).
    M = mount.Name + '#Params.'
    back = doc.addObject('App::Part', 'BackFan')
    asm.addObject(back)
    link(back, 'BackFan_Mount', mount.getObject('Body'))
    link(back, 'BackFan_Gasket', tpu.getObject('Body'), flip, (0, 0, 0))
    link(back, 'BackFan_Fan', slim.getObject('Fan'), flip, (0, 0, f'-{T}GasketT'))
    h = M + 'FanHoleSpacing / 2'
    far = f'-{T}GasketT - 15'  # slim fan far face
    for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)], start=1):
        x, y = ('' if sx > 0 else '-') + h, ('' if sy > 0 else '-') + h
        link(back, f'BackFan_FanInsert{i}', insert, Rot(), (x, y, 0))
        link(back, f'BackFan_FanWasher{i}', tpu.getObject('Washer'), flip, (x, y, far))
        link(back, f'BackFan_FanScrew{i}_M3x25', m3x25, flip, (x, y, f'{far} - {T}WasherT'))
        fx, fy = ('' if sx > 0 else '-') + M + 'FootSpanX / 2', ('' if sy > 0 else '-') + M + 'FootSpanY / 2'
        link(back, f'BackFan_FootScrew{i}_M3x20', m3x20, flip, (fx, fy, 0))
    push_cx = f'(Layout.BoardLength - {s_push.Name}#Params.PcbEndX + {s_push.Name}#Params.ClampX1)'
    pull_cx = f'({s_pull.Name}#Params.EndWallX + {s_pull.Name}#Params.XEnd - {s_pull.Name}#Params.ClampX1)'
    back.setExpression('.Placement.Base.x', f'({push_cx} + {pull_cx}) / 2')
    back.setExpression('.Placement.Base.y', 'Layout.BoardY0 + Layout.BoardWidth / 2')
    back.setExpression('.Placement.Base.z', f'-{clamp.Name}#Params.BarT - {M}PlateT - {M}FootH')
    doc.recompute()
    span = (lay.BoardLength - s_push.Params.PcbEndX + s_push.Params.ClampX1) - (s_pull.Params.EndWallX + s_pull.Params.XEnd - s_pull.Params.ClampX1)
    log('BackFan foot span X: clamps %.2f, mount FootSpanX %.2f' % (span, mount.Params.FootSpanX))

    # Case: halves, glue-in grills, hub retainer, PSU, USB hub and their hardware (case = board frame)
    cgrp = doc.addObject('App::Part', 'Case')
    asm.addObject(cgrp)
    link(cgrp, 'CaseFront', case.getObject('CaseFront'))
    link(cgrp, 'CaseBack', case.getObject('CaseBack'))
    roty = Rot(V(0, 1, 0), 180)
    # fan grills point toward the split (their +x): -X for the push fan, +X for the pull fan
    link(cgrp, 'PushGrill', case.getObject('FanGrill'), roty, (K + 'PushFanX', K + 'FanY', K + 'ZLeft'))
    link(cgrp, 'PullGrill', case.getObject('FanGrill'), Rot(V(1, 0, 0), 180), (K + 'PullFanX', K + 'FanY', K + 'ZLeft'))
    link(cgrp, 'RearGrill', case.getObject('RearGrill'), Rot(), (K + 'RearFanX', K + 'FanY', K + 'ZRight'))
    vent_rot = Rot(V(1, 0, 0), 90)  # grill +x (its point) -> +X, visible face up
    for n, x, rot in (('Back', 'VentBackX', vent_rot), ('Front', 'VentFrontX', Rot(V(0, 1, 0), 180).multiply(vent_rot))):
        link(cgrp, f'TopVent{n}', case.getObject('TopVentGrill'), rot, (K + x, K + 'YTop', K + 'VentZ'))
    link(cgrp, 'HubRetainer', case.getObject('HubRetainer'), Rot(V(0, 1, 0), 90), (f'{K}HubBackX - {K}RetT', 0, 0))
    link(cgrp, 'PSU', psu.getObject('PSU'), Rot(), (K + 'PsuX0', K + 'PsuY0', K + 'PsuZ0'))
    link(cgrp, 'PowerButton', button.getObject('Button'), Rot(V(0, 1, 0), 90), (K + 'XFront', K + 'ButtonY', K + 'ButtonZ'))
    link(cgrp, 'USB_Hub', hub.getObject('Hub'), Rot(V(0, 0, 1), 90),
         (K + 'HubFaceX', K + 'HubY0', f'{K}HubZ - {K}HubT / 2'))
    m3x10b, m3x12c = hw.getObject('BHCS_M3x10'), hw.getObject('FHCS_M3x12')
    down, up = Rot(V(1, 0, 0), 90), Rot(V(1, 0, 0), -90)  # z axis -> -Y / +Y
    for i in (1, 2):
        zt, zb = K + f'RibZTop{i}', K + f'RibZBot{i}'
        # inserts pressed in from the rib's inner face (the screw pulls them against the tongue)
        rib = f'{K}CaseT + {K}TongueClear + {K}TongueT + {K}RibH'
        link(cgrp, f'JointInsertTop{i}', insert, up, (K + 'JointX', f'{K}YTop - ({rib})', zt))
        link(cgrp, f'JointInsertBottom{i}', insert, down, (K + 'JointX', f'{K}YBot + {rib}', zb))
        link(cgrp, f'JointScrewTop{i}_M3x12', m3x12c, up, (K + 'JointX', K + 'YTop', zt))
        link(cgrp, f'JointScrewBottom{i}_M3x12', m3x12c, down, (K + 'JointX', K + 'YBot', zb))
    # feet: inserts in the bottom and the right side; short feet on the bottom (standing, shown) and
    # tall ones on the right side (lying on that side, hidden; the renders show both)
    for a in (1, 2):
        x = K + f'FootX{a}'
        for b in (1, 2):
            z, y = K + f'FootBotZ{b}', K + f'FootSideY{b}'
            link(cgrp, f'FootInsertBot{a}{b}', insert, up, (x, K + 'YBot', z))
            link(cgrp, f'FootInsertSide{a}{b}', insert, Rot(), (x, y, K + 'ZRight'))
            link(cgrp, f'StandFoot{a}{b}', case.getObject('TpuFootShort'), up, (x, f'{K}YBot - {K}FootShortH', z))
            link(cgrp, f'StandFootScrew{a}{b}_M3x12', m3x12c, down,
                 (x, f'{K}YBot - {K}FootShortH + {K}FootShortRecess', z))
            for o in (link(cgrp, f'LyingFoot{a}{b}', case.getObject('TpuFootTall'), Rot(), (x, y, f'{K}ZRight - {K}FootTallH')),
                      link(cgrp, f'LyingFootScrew{a}{b}_M3x12', m3x12c, flip,
                           (x, y, f'{K}ZRight - {K}FootTallH + {K}FootTallRecess'))):
                o.Visibility = False
    link(cgrp, 'TabInsert', insert, down, (K + 'TabX', K + 'TabUnderY', K + 'TabZ'))
    link(cgrp, 'TabScrew_M3x10', m3x10b, up, (K + 'TabX', f'{K}TabUnderY + 1.1', K + 'TabZ'))
    for n, z in (('A', 'HubRibZA'), ('B', 'HubRibZB')):
        for i, y in ((1, 'RetY1'), (2, 'RetY2')):
            link(cgrp, f'HubInsert{n}{i}', insert, Rot(V(0, 1, 0), 90), (K + 'HubBackX', K + y, K + z))
            link(cgrp, f'HubScrew{n}{i}_M3x10', m3x10b, Rot(V(0, 1, 0), -90),
                 (f'{K}HubBackX - {K}RetT', K + y, K + z))
    for i, y in ((1, 'PsuHoleY1'), (2, 'PsuHoleY2')):
        link(cgrp, f'PsuScrew{i}', hw.getObject('FHCS_6_32x3_8'), Rot(V(0, 1, 0), -90),
             (K + 'XBack', f'{K}PsuY0 + {K}{y}', K + 'PsuHoleZ'))
    doc.recompute()

    import JointObject
    joints = asm.newObject('Assembly::JointGroup', 'Joints')
    for obj in (brd, push, pull, back, cgrp):
        g = joints.newObject('App::FeaturePython', 'Grounded_' + obj.Name)
        JointObject.GroundedJoint(g, obj)
        JointObject.ViewProviderGroundedJoint(g.ViewObject)
    doc.recompute()
    doc.save()
    return doc, asm, brd, push, pull, back, cgrp


# ------------------------------------------------------------------ bill of materials
# Everything to buy, keyed by the object the assembly links to: (document, object) -> (group, item).
# Printed parts (stls/) aren't listed.
BUY = {
    ('bc250_board', 'BC250'): ('Components', 'AMD BC-250 board, with its stock heatsink'),
    ('fan_120x25', 'Fan'): ('Components', 'ARCTIC P12 Pro PWM, 120 x 25 mm fan'),
    ('fan_120x15', 'Fan'): ('Components', 'Thermalright TL-C12015B, 120 x 15 mm slim fan'),
    ('psu_flex_atx', 'PSU'): ('Components', 'Enhance ENP-8345L-OVT 450 W modular Flex ATX PSU (165 x 81.5 x 40.5 mm)'),
    ('usb_hub_anker', 'Hub'): ('Components', 'Anker 4-port USB 3.0 hub, 2 ft cable version (A7516 / A8309)'),
    ('power_button_16mm', 'Button'): ('Components', 'mosfet.party 16 mm backlit power button with built-in latching adapter'),
    ('hardware_m3', 'Insert_M3x5x4'): ('Hardware', 'M3 heat-set insert, Voron spec (M3 x 5 mm OD x 4 mm)'),
    ('hardware_m3', 'FHCS_M3x40'): ('Hardware', 'FHCS M3x40 (ISO 10642 / DIN 7991)'),
    ('hardware_m3', 'FHCS_M3x12'): ('Hardware', 'FHCS M3x12 (ISO 10642 / DIN 7991)'),
    ('hardware_m3', 'FHCS_6_32x3_8'): ('Hardware', 'FHCS #6-32 x 3/8" (82 deg), for the PSU'),
    ('hardware_m3', 'BHCS_M3x25'): ('Hardware', 'BHCS M3x25 (ISO 7380)'),
    ('hardware_m3', 'BHCS_M3x20'): ('Hardware', 'BHCS M3x20 (ISO 7380)'),
    ('hardware_m3', 'BHCS_M3x10'): ('Hardware', 'BHCS M3x10 (ISO 7380)'),
}
# Where to buy, for the items that have a link (BOM.md only).
LINKS = {
    ('fan_120x25', 'Fan'): 'https://www.amazon.co.uk/dp/B0DJDC74BP',
    ('fan_120x15', 'Fan'): 'https://www.amazon.co.uk/dp/B0CBLT3PK7',
    ('usb_hub_anker', 'Hub'): 'https://www.amazon.co.uk/dp/B07L32B9C2',
    ('power_button_16mm', 'Button'): 'https://mosfet.party/products/adapter-3',
    ('hardware_m3', 'Insert_M3x5x4'): 'https://jb3d.uk/product/50-threaded-heat-set-inserts-m3-x-d5-0-x-l4-0/',
}
# Bought but not modelled in the assembly: (group, item, qty, link).
UNMODELLED = [
    ('Components', 'Right-angle USB-A adapter, for the hub cable', 1, 'https://www.amazon.co.uk/dp/B0F99CJS12'),
]


def bom(doc):
    """Count the bought parts linked into the assembly; write them to a BOM sheet and BOM.md."""
    count = {}
    for o in doc.Objects:
        if o.TypeId != 'App::Link':
            continue
        t = o.LinkedObject
        key = (t.Document.Name, t.Name)
        if key in BUY:
            count[key] = count.get(key, 0) + 1
        elif key[0] == 'hardware_m3':
            raise KeyError(f'{o.Name}: {key} missing from BUY')
    natural = lambda s: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]  # M3x8 before M3x10
    rows = sorted([(BUY[k][0], BUY[k][1], n, LINKS.get(k)) for k, n in count.items()] + UNMODELLED,
                  key=lambda r: (r[0], natural(r[1])))
    sheet = doc.addObject('Spreadsheet::Sheet', 'BOM')
    for c, h in zip('ABC', ('Qty', 'Item', 'Group')):
        sheet.set(f'{c}1', h)
    for i, (group, item, n, _) in enumerate(rows, start=2):
        sheet.set(f'A{i}', str(n)); sheet.set(f'B{i}', item); sheet.set(f'C{i}', group)
    sheet.setColumnWidth('B', 520)
    lines = ['# The Fish Tank: parts to buy', '',
             'The script scripts/build_assembly.py makes this file from the assembly (cad/fish_tank.FCStd).',
             'For the parts to print, refer to [stls/README.md](stls/README.md).', '']
    for group in ('Components', 'Hardware'):
        lines += [f'## {group}', '', '| Qty | Item |', '|---:|---|']
        lines += [f'| {n} | ' + (f'[{item}]({url})' if url else item) + ' |'
                  for g, item, n, url in rows if g == group]
        lines.append('')
    with open(os.path.join(OUT, 'BOM.md'), 'w') as f:
        f.write('\n'.join(lines))
    for r in rows:
        log('BOM %s: %d x %s' % (r[0], r[2], r[1]))


# ------------------------------------------------------------------ checks + pictures
def global_shape(obj, group=None):
    s = Part.getShape(obj, '', transform=True).copy()
    if group is not None:
        s.Placement = group.Placement.multiply(s.Placement)
    return s


def interference(board, groups):
    """Pairwise solid overlap between every part of the assembly, except the pairs that are meant to
    share material: inserts and the screws threaded into them, and a screw and the insert it's in."""
    parts = [(o.Name, o.Shape) for o in board.getObject('BC250').Group
             if hasattr(o, 'Shape') and o.Visibility]
    for g in groups:
        for o in g.Group:
            if o.TypeId == 'App::Link':
                parts.append((o.Name, global_shape(o, g)))
    parts = [(n, s) for n, s in parts if not s.isNull() and s.Volume > 1e-6 and 'Insert' not in n]
    log('checking', len(parts), 'parts')
    res = []
    boxes = [s.BoundBox for _, s in parts]
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if not boxes[i].intersect(boxes[j]):
                continue
            (na, a), (nb, b) = parts[i], parts[j]
            try:
                v = a.common(b).Volume
            except Exception:
                v = float('nan')
            if not (v < 0.05):
                res.append((na, nb, v))
    return res


def look(v, cam, up=(0, 1, 0)):
    """Camera from direction cam (board frame), Y up unless given."""
    z = V(*cam).normalize()
    x = V(*up).cross(z).normalize()
    y = z.cross(x)
    m = App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0)
    v.setCameraOrientation(App.Rotation(m).Q)
    v.fitAll()
    Gui.updateGui()


def render_style():
    """Render-only looks, applied after the files are saved: matte surfaces, and edges tinted toward each
    part's colour (lighter on dark parts, darker on light ones) so the hex grooves read without hard
    black lines."""
    for d in App.listDocuments().values():
        for o in d.Objects:
            vo = getattr(o, 'ViewObject', None)
            if vo is None or not hasattr(vo, 'ShapeAppearance'):
                continue
            mats = list(vo.ShapeAppearance)
            for m in mats:
                m.Shininess = 0.12; m.SpecularColor = (0.15, 0.15, 0.15, 1.0)
            vo.ShapeAppearance = mats
            if hasattr(vo, 'LineColor') and hasattr(vo, 'ShapeColor'):
                c = vo.ShapeColor[:3]
                dark = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] < 0.3
                vo.LineColor = tuple(min(1.0, x + 0.16) for x in c) if dark else tuple(x * 0.62 for x in c)
                vo.LineWidth = 1.0


def compose(raw, dst, size, margin=0.07):
    """Crop a transparent render to the model, centre it with a margin on a soft gradient and scale it
    down to size (rendering at twice the size and scaling down anti-aliases the edges)."""
    import numpy as np
    img = QtGui.QImage(raw).convertToFormat(QtGui.QImage.Format_ARGB32)
    W, H = img.width(), img.height()
    alpha = np.frombuffer(img.constBits(), np.uint8, W * H * 4).reshape(H, W, 4)[:, :, 3]
    rows, cols = np.flatnonzero(alpha.any(1)), np.flatnonzero(alpha.any(0))
    box = QtCore.QRect(int(cols[0]), int(rows[0]), int(cols[-1] - cols[0] + 1), int(rows[-1] - rows[0] + 1))
    k = min(W * (1 - 2 * margin) / box.width(), H * (1 - 2 * margin) / box.height())
    model = img.copy(box).scaled(int(box.width() * k), int(box.height() * k), QtCore.Qt.KeepAspectRatio,
                                 QtCore.Qt.SmoothTransformation)
    out = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32)
    p = QtGui.QPainter(out)
    g = QtGui.QRadialGradient(W / 2, H * 0.4, W * 0.75)
    g.setColorAt(0, QtGui.QColor(250, 251, 252)); g.setColorAt(1, QtGui.QColor(208, 214, 222))
    p.fillRect(out.rect(), g)
    p.drawImage((W - model.width()) // 2, (H - model.height()) // 2, model)
    p.end()
    out.scaled(*size, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation).save(dst)
    os.remove(raw)


def shots(doc, case_grp):
    """Render the images and write renders/README.md listing them."""
    out = os.environ['SHOTS']
    Gui.setActiveDocument(doc.Name)
    v = Gui.activeDocument().activeView()
    render_style()
    v.setCameraType('Perspective')
    Gui.updateGui()
    for o in doc.Objects:  # grounded-joint markers
        if o.TypeId == 'Assembly::JointGroup':
            o.Visibility = False
    show = lambda keep: [setattr(o, 'Visibility', keep(o.Name)) for o in case_grp.Group]
    # (heading, note, setup, camera up, [(file, caption, camera direction)])
    sections = [
        ('Standing', '', lambda: show(lambda n: not n.startswith('LyingFoot')), (0, 1, 0),
         [('case_front_left', 'Front left', (1, 0.55, 1)), ('case_back_right', 'Back right', (-1, 0.55, -1)),
          ('case_front', 'Front', (1, 0, 0)), ('case_back', 'Back', (-1, 0, 0)),
          ('case_left', 'Left', (0, 0, 1)), ('case_right', 'Right', (0, 0, -1)),
          ('case_bottom', 'Bottom', (0.4, -1, 0.3))]),
        # on the right side, push-pull fans up, on the tall feet
        ('Lying flat', '', lambda: show(lambda n: not n.startswith('StandFoot')), (0, 0, 1),
         [('lying_front', 'Front', (1, 0.9, 0.7)), ('lying_side', 'Side', (0.25, 1, 0.12))]),
        # hide the case shell and grills, keep PSU, hub and hardware
        ('Inside', 'These views do not show the case and the grills.',
         lambda: show(lambda n: not n.startswith(('LyingFoot', 'CaseFront', 'CaseBack', 'PushGrill', 'PullGrill',
                                                  'RearGrill', 'TopVent', 'HubRetainer'))), (0, 1, 0),
         [('asm_iso', 'Front left', (1, 0.55, 1)), ('asm_top', 'Top', (0, 1, 0.001)),
          ('asm_push_end', 'Push fan end', (1, 0.8, -0.3)), ('asm_pull_end', 'Pull fan end', (-1, 0.8, 0.6)),
          ('asm_back', 'Backplate side', (0.3, 0.5, -1))]),
    ]
    lines = ['# Renders', '',
             'The script scripts/build_assembly.py makes these images from the assembly (cad/fish_tank.FCStd).', '']
    for heading, note, setup, up, views in sections:
        setup()
        lines += [f'## {heading}', ''] + ([note, ''] if note else [])
        for name, caption, cam in views:
            look(v, cam, up)
            raw = os.path.join(out, f'{name}.raw.png')
            v.saveImage(raw, 3200, 2000, 'Transparent')
            compose(raw, os.path.join(out, f'{name}.png'), (1600, 1000))
        for i in range(0, len(views), 2):  # two to a row
            row = views[i:i + 2]
            lines += ['| ' + ' | '.join(c for _, c, _ in row) + ' |', '|' + '---|' * len(row),
                      '| ' + ' | '.join(f'![{heading}, {c.lower()}]({n}.png)' for n, c, _ in row) + ' |', '']
    show(lambda n: not n.startswith('LyingFoot'))
    with open(os.path.join(out, 'README.md'), 'w') as f:
        f.write('\n'.join(lines))

def main():
    prefs = App.ParamGet('User parameter:BaseApp/Preferences/Document')
    backups = prefs.GetBool('CreateBackupFiles', True)
    prefs.SetBool('CreateBackupFiles', False)  # every file here is regenerated; restored below
    # renders: a back light to separate the dark faces (restored below too)
    view = App.ParamGet('User parameter:BaseApp/Preferences/View')
    lights = (view.GetBool('EnableBacklight', False), view.GetInt('BacklightIntensity', 100),
              view.GetInt('HeadlightIntensity', 100))
    view.SetBool('EnableBacklight', True); view.SetInt('BacklightIntensity', 60); view.SetInt('HeadlightIntensity', 90)
    try:
        board = build_board(); log('board ok')
        fan = build_fan(); log('fan ok')
        slim = build_slim_fan(); log('slim fan ok')
        psu = build_psu(); hub = build_hub(); button = build_button(); log('psu + hub + button ok')
        hw = build_hardware(); log('hardware ok')
        white, black, blue = (0.93, 0.93, 0.91), (0.11, 0.11, 0.12), (0.09, 0.17, 0.42)  # print colours
        s_push = tidy_printed('fan_shroud_push', white)
        s_pull = tidy_printed('fan_shroud_pull', white)
        clamp = tidy_printed('pcb_clamp', (0.15, 0.45, 0.85))
        mount = tidy_printed('backfan_mount', white)
        tpu = tidy_printed('fan_isolation_tpu', (0.20, 0.20, 0.22))
        case = tidy_printed('fish_tank_case', black)
        for g in ('FanGrill', 'RearGrill', 'TopVentGrill'):
            color(case.getObject(g), blue)
        for g in ('TpuFootShort', 'TpuFootTall'):
            color(case.getObject(g), (0.20, 0.20, 0.22))  # TPU, like the fan gaskets
        case.save()
        log('printed parts ok')
        doc, asm, brd, push, pull, back, cgrp = build_assembly(board, fan, slim, psu, hub, button, hw, s_push, s_pull, clamp,
                                                              mount, tpu, case)
        bom(doc)
        bad = [(o.Name, o.State) for o in doc.Objects if 'Invalid' in o.State or 'Error' in o.State]
        log('assembly ok; bad objects:', bad)
        for o in (brd, push, pull, back, cgrp):
            log(o.Name, 'placement', o.Placement, 'bbox', Part.getShape(o).BoundBox)
        for r in interference(board, [push, pull, back, cgrp]):
            log('INTERFERENCE %s vs %s: %.2f mm3' % r)
        log('interference check done')
        for d in (board, fan, slim, psu, hub, button, hw, s_push, s_pull, clamp, mount, tpu, case, doc):
            d.save()
        shots(doc, cgrp); log('shots done')  # after saving: the render styling stays out of the files
    except Exception:
        log(traceback.format_exc())
    finally:
        prefs.SetBool('CreateBackupFiles', backups)
        view.SetBool('EnableBacklight', lights[0]); view.SetInt('BacklightIntensity', lights[1])
        view.SetInt('HeadlightIntensity', lights[2])
        LOG.close()
        os._exit(0)


QtCore.QTimer.singleShot(3000, main)
