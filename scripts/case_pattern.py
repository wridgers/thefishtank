# Hex deboss pattern wrapped round the case's four long faces, and the zigzag seam between the two
# halves that runs along its grooves, so the joint disappears into the pattern. Plain Part geometry,
# rebuilt from the case parameters each time gen_case.py runs.
#
# Unfolded coordinates: u = X (along the case) and s = distance round the outer octagon section,
# going bottom -> left -> top -> right. The hexagons point along u, which is up when the halves
# print, so every groove wall is vertical or 60 deg from it. HexCells cells fit exactly round the
# perimeter, so the lattice closes on itself, and the seam is the zigzag between lattice columns 0
# and 1 (column 0 is the last one in the back half).
import math
import FreeCAD as App, Part

V = App.Vector
COS30 = math.cos(math.radians(30))
BOTTOM, LEFT, TOP, RIGHT = 0, 2, 4, 6  # flat faces in the octagon (odd ones are the edge chamfers)


class Lattice:
    def __init__(self, P):
        self.P = P
        yb, yt, zr, zl, c = (P[k] for k in ('YBot', 'YTop', 'ZRight', 'ZLeft', 'CaseChamfer'))
        corners = [(yb, zr + c), (yb, zl - c), (yb + c, zl), (yt - c, zl), (yt, zl - c), (yt, zr + c),
                   (yt - c, zr), (yb + c, zr)]  # (y, z)
        self.faces, s = [], 0.0
        for i, a in enumerate(corners):
            b = corners[(i + 1) % 8]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            t = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            self.faces.append({'s0': s, 'L': L, 'a': a, 't': t, 'n': (-t[1], t[0])})
            s += L
        self.perimeter = s
        self.n = int(round(P['HexCells']))
        self.p = P['HexP']
        assert abs(self.p * self.n - s) < 1e-6, 'HexP must be the perimeter / HexCells'
        self.tip = P['HexTip']
        self.x0 = P['JointX']  # column 0 centres
        left = self.faces[LEFT]
        # column-1 cells centred on the left face: then column 0 (and every even column) has three cells
        # across the bottom and top, which spreads the joint screws and the feet
        self.s_phase = (left['s0'] + left['L'] / 2 + self.p / 2) % self.p

    # --- coordinates
    def face_of(self, s):
        s %= self.perimeter
        for i, f in enumerate(self.faces):
            if s < f['s0'] + f['L'] or i == 7:
                return i, s - f['s0']

    def point(self, i, u, w, out=0.0):
        f = self.faces[i]
        return V(u, f['a'][0] + w * f['t'][0] + out * f['n'][0], f['a'][1] + w * f['t'][1] + out * f['n'][1])

    def normal(self, i):
        return V(0, *self.faces[i]['n'])

    def column_x(self, j):
        return self.x0 + 1.5 * self.tip * j

    def cell_s(self, j, m):
        return self.s_phase + (j % 2) * self.p / 2 + m * self.p

    def hexagon(self, j, m):
        """Corners (u, s) of cell (j, m), anticlockwise from the +u tip."""
        u, s, t, h = self.column_x(j), self.cell_s(j, m), self.tip, self.p / 2
        return [(u + t, s), (u + t / 2, s + h), (u - t / 2, s + h), (u - t, s), (u - t / 2, s - h), (u + t / 2, s - h)]

    def seam(self, s):
        """Seam X at s: the zigzag between columns 0 and 1, SplitX +- SeamA."""
        q = ((s - self.s_phase) % self.p) / self.p  # 0 at a column-0 cell centre (zigzag at its +u tip)
        a = self.P['SeamA']
        return self.P['SplitX'] + a * (1 - 4 * q if q < 0.5 else 4 * q - 3)

    def cells_on_face(self, i, j, margin):
        """Centres (s, w) of the column-j cells whose whole outline (+ margin) lies on flat face i."""
        f, h = self.faces[i], self.p / 2 + margin
        out = []
        for m in range(-1, self.n + 1):
            s = self.cell_s(j, m) % self.perimeter
            if f['s0'] + h <= s <= f['s0'] + f['L'] - h:
                out.append((s, s - f['s0']))
        return sorted({(round(s, 6), round(w, 6)) for s, w in out})

    def face_coord(self, i, w):
        """The Y or Z coordinate (whichever varies along flat face i) at w."""
        f = self.faces[i]
        return f['a'][0] + w * f['t'][0] if abs(f['t'][0]) > 0.5 else f['a'][1] + w * f['t'][1]

    # --- pieces of a straight (u, s) segment on each face it crosses
    def pieces(self, u1, s1, u2, s2):
        cuts = [0.0, 1.0]
        if abs(s2 - s1) > 1e-9:
            lo, hi = min(s1, s2), max(s1, s2)
            k0 = math.floor(lo / self.perimeter) - 1
            for k in range(k0, k0 + 3):
                for f in self.faces:
                    b = f['s0'] + k * self.perimeter
                    if lo + 1e-9 < b < hi - 1e-9:
                        cuts.append((b - s1) / (s2 - s1))
        cuts.sort()
        out = []
        for ta, tb in zip(cuts, cuts[1:]):
            sm = s1 + (s2 - s1) * (ta + tb) / 2
            i, wm = self.face_of(sm)
            ua, ub = u1 + (u2 - u1) * ta, u1 + (u2 - u1) * tb
            wa, wb = wm + (s2 - s1) * (ta - (ta + tb) / 2), wm + (s2 - s1) * (tb - (ta + tb) / 2)
            out.append((i, ua, wa, ub, wb, ta > 0, tb < 1))  # flags: end is on a face boundary
        return out

    def wedge(self, i, x0, x1, out=3.0, depth=None):
        """Prism over face i between the bisector planes of its two edges (mitres neighbouring faces)."""
        depth = depth if depth is not None else self.P['CaseT'] + 1.5
        f, fp, fn = self.faces[i], self.faces[i - 1], self.faces[(i + 1) % 8]
        bis = lambda n1, n2: (lambda b: (b[0] / math.hypot(*b), b[1] / math.hypot(*b)))((n1[0] + n2[0], n1[1] + n2[1]))
        b0, b1 = bis(fp['n'], f['n']), bis(f['n'], fn['n'])
        cos = b0[0] * f['n'][0] + b0[1] * f['n'][1]
        ko, ki = out / cos, depth / cos
        a = f['a']
        e = (a[0] + f['L'] * f['t'][0], a[1] + f['L'] * f['t'][1])
        quad = [(a[0] + b0[0] * ko, a[1] + b0[1] * ko), (e[0] + b1[0] * ko, e[1] + b1[1] * ko),
                (e[0] - b1[0] * ki, e[1] - b1[1] * ki), (a[0] - b0[0] * ki, a[1] - b0[1] * ki)]
        pts = [V(x0, y, z) for y, z in quad]
        return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(x1 - x0, 0, 0))


# ------------------------------------------------------------------ grooves
def edges(lat, j_range):
    """Unique lattice edges ((u1, s1), (u2, s2)) of the cells in columns j_range, with the cells of
    each edge (so callers can tell seam edges and foot cells)."""
    out = {}
    key = lambda q: (round(q[0], 4), round(q[1] % lat.perimeter, 4))
    for j in j_range:
        for m in range(lat.n):
            h = lat.hexagon(j, m)
            for a, b in zip(h, h[1:] + h[:1]):
                k = tuple(sorted((key(a), key(b))))
                out.setdefault(k, [a, b, set()])[2].add((j, m % lat.n))
    return list(out.values())


def groove(lat, i, ua, wa, ub, wb, cut_a, cut_b):
    """V-groove (45 deg walls) along a segment on face i, from slightly above the surface. Each end
    either slopes up at 45 deg past the end point (as a V-bit plunging in leaves: no flat ceiling when
    printed, and all planar, so the booleans stay robust) or, on a face boundary (cut_*), runs on
    square for the face wedge to mitre."""
    return vgroove(lat.P, lat.point(i, ua, wa), lat.point(i, ub, wb), lat.normal(i), cut_a, cut_b)


def vgroove(P, pa, pb, n, cut_a, cut_b):
    """groove() for a segment pa -> pb on a surface with outward normal n."""
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


def grooves(lat, keepouts, protect):
    """The pattern cutter: a groove along every lattice edge on the long faces, masked like a texture:
    a groove stops (with a sloped end) PatternClear short of the keep-out faces (openings,
    countersinks) and of the end chamfers. Edges protect(cells) says to keep are never masked."""
    P = lat.P
    x_lo = P['XBack'] + P['CaseChamfer'] + P['PatternClear'] + P['GrooveW'] / 2
    x_hi = P['XFront'] - P['CaseChamfer'] - P['PatternClear'] - P['GrooveW'] / 2
    clear = P['PatternClear'] + P['GrooveW'] / 2
    j0 = math.floor((P['XBack'] - lat.x0) / (1.5 * lat.tip)) - 1
    j1 = math.ceil((P['XFront'] - lat.x0) / (1.5 * lat.tip)) + 1
    per_face = {i: [] for i in range(8)}
    n_full = n_part = 0
    for a, b, cells in edges(lat, range(j0, j1 + 1)):
        keep = protect(cells)
        for i, ua, wa, ub, wb, cut_a, cut_b in lat.pieces(a[0], a[1], b[0], b[1]):
            at = lambda t: (ua + (ub - ua) * t, wa + (wb - wa) * t)
            pa, pb = lat.point(i, ua, wa), lat.point(i, ub, wb)
            box = Part.LineSegment(pa, pb).toShape().BoundBox
            box.enlarge(clear)
            near = [] if keep else [k for k in keepouts if box.intersect(k.BoundBox)]

            def ok(t):
                u, w = at(t)
                if not keep and not x_lo <= u <= x_hi:
                    return False
                q = Part.Vertex(lat.point(i, u, w))
                return all(q.distToShape(k)[0] >= clear for k in near)
            spans = mask(ok, (pb - pa).Length)
            if spans == [(0.0, 1.0)]:
                n_full += 1
            elif spans:
                n_part += 1
            for t0, t1 in spans:
                (u0, w0), (u1, w1) = at(t0), at(t1)
                end0, end1 = t0 == 0.0 and cut_a, t1 == 1.0 and cut_b  # runs on over a face boundary
                if not (end0 or end1) and (t1 - t0) * (pb - pa).Length < min(P['PatternMinRun'], 0.99 * (pb - pa).Length):
                    continue  # no dashes (a whole short piece, e.g. by a face boundary, stays)
                per_face[i].append(groove(lat, i, u0, w0, u1, w1, end0, end1))
    print(f'  hex pattern: {n_full} whole grooves, {n_part} stopped short of openings / screws / ends')
    return per_face_solids(lat, per_face)


def per_face_solids(lat, per_face):
    """Fuse each face's cutters and mitre them to the face; returned as a compound of one solid per
    face (one big fuse across the faces gives OCC an invalid shape, and a cut with it fails quietly)."""
    P = lat.P
    solids = []
    for i, gs in per_face.items():
        if gs:
            g = gs[0].fuse(gs[1:]) if len(gs) > 1 else gs[0]
            g = g.common(lat.wedge(i, P['XBack'] - 5, P['XFront'] + 5)).removeSplitter()
            if not g.isValid():
                g.fix(1e-7, 1e-7, 1e-7)
            assert g.isValid(), f'pattern cutter for face {i} is not a valid solid'
            solids.extend(g.Solids)
    return Part.makeCompound(solids)


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


def front_grooves(P, keepouts):
    """The same pattern on the front end face. That face prints on the bed, so the grooves print
    upside down: their 45 deg walls and sloped ends keep within the overhang limit. The hexagons
    point across the face (u = Z, v = Y), so they read flat-topped like the ones on the long faces,
    and the lattice is centred on the face; grooves are masked like the long faces' (grooves())."""
    p, t, c = P['HexP'], P['HexTip'], P['CaseChamfer']
    x, yc, zc = P['XFront'], (P['YTop'] + P['YBot']) / 2, (P['ZLeft'] + P['ZRight']) / 2
    hy, hz = (P['YTop'] - P['YBot']) / 2 - c, (P['ZLeft'] - P['ZRight']) / 2 - c  # flat face (octagon)
    clear = P['PatternClear'] + P['GrooveW'] / 2
    diag = hy + hz + c * (1 - math.sqrt(2)) - clear * math.sqrt(2)

    def ok(y, z):
        dy, dz = abs(y - yc), abs(z - zc)
        if dy > hy - clear or dz > hz - clear or dy + dz > diag:
            return False
        q = Part.Vertex(V(x, y, z))
        return all(q.distToShape(k)[0] >= clear for k in keepouts)
    segs = {}
    jn, mn = math.ceil(hz / (1.5 * t)) + 1, math.ceil(hy / p) + 1
    for j in range(-jn, jn + 1):
        for m in range(-mn, mn + 1):
            u, v, h = zc + 1.5 * t * j, yc + (j % 2) * p / 2 + m * p, p / 2
            hexa = [(u + t, v), (u + t / 2, v + h), (u - t / 2, v + h), (u - t, v), (u - t / 2, v - h), (u + t / 2, v - h)]
            for a, b in zip(hexa, hexa[1:] + hexa[:1]):
                segs[tuple(sorted(((round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4)))))] = (a, b)
    gs, n = [], V(1, 0, 0)
    for (za, ya), (zb, yb) in segs.values():
        L = math.hypot(zb - za, yb - ya)
        for t0, t1 in mask(lambda k: ok(ya + (yb - ya) * k, za + (zb - za) * k), L):
            if (t1 - t0) * L >= min(P['PatternMinRun'], 0.99 * L):
                gs.append(vgroove(P, V(x, ya + (yb - ya) * t0, za + (zb - za) * t0),
                                  V(x, ya + (yb - ya) * t1, za + (zb - za) * t1), n, False, False))
    g = gs[0].fuse(gs[1:]).removeSplitter()
    if not g.isValid():
        g.fix(1e-7, 1e-7, 1e-7)
    assert g.isValid(), 'front pattern cutter is not a valid solid'
    print(f'  front hex pattern: {len(gs)} grooves')
    return g.Solids


def teeth(lat, front):
    """Cutter that trims a half's walls to the seam: for the front half everything at X below the
    zigzag (+ SeamGap / 2), for the back half everything above it (- SeamGap / 2)."""
    P = lat.P
    g = P['SeamGap'] / 2
    x_far = P['SplitX'] + (-1 if front else 1) * (P['SeamA'] + 3)
    depth, over = P['CaseT'] + 0.1, 1.0
    parts = {}
    for i, f in enumerate(lat.faces):
        e = 4.0
        ws = [-e] + [w for w in (k * lat.p / 2 + ((lat.s_phase - f['s0']) % (lat.p / 2)) - lat.p
                                 for k in range(int((f['L'] + 2 * e) / (lat.p / 2)) + 4)) if -e < w < f['L'] + e] + [f['L'] + e]
        zig = [(lat.seam(f['s0'] + w) + (g if front else -g), w) for w in ws]
        poly = [(x_far, ws[0])] + zig + [(x_far, ws[-1])]
        pts = [lat.point(i, u, w, over) for u, w in poly]
        prism = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(lat.normal(i) * -(over + depth))
        parts[i] = [prism]
    return per_face_solids(lat, parts)


# ------------------------------------------------------------------ keep-out outlines
def outline_face(pts2d, plane, at):
    """Planar face from (u, v) points on a wall: plane 'XY' (u, v = X, Y at Z = at), 'XZ' (X, Z at
    Y = at) or 'YZ' (Y, Z at X = at)."""
    to3 = {'XY': lambda u, v: V(u, v, at), 'XZ': lambda u, v: V(u, at, v), 'YZ': lambda u, v: V(at, u, v)}[plane]
    pts = [to3(u, v) for u, v in pts2d]
    return Part.Face(Part.makePolygon(pts + [pts[0]]))


def circle_pts(cu, cv, r, n=48):
    return [(cu + r * math.cos(2 * math.pi * k / n), cv + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def pill_pts(cu, cv, length, width, tip=0, psi=0.0, n=24):
    """Outline of gen_case's pill shape (a teardrop when length = width): tip +1 / -1 puts the point
    toward +u / -u, 0 leaves both ends round."""
    r, sg, ct = width / 2, tip or 1, length / 2 - width / 2
    near = [-90 + 180 * k / n for k in range(n + 1)]
    if tip:
        near = sorted([a for a in near if abs(a) >= psi] + [-psi, psi])
    pts = []
    for a in near:  # near end, -90 -> 90 deg
        if tip and a == psi:
            pts.append((cu + sg * (ct + r / math.cos(math.radians(psi))), cv))
        pts.append((cu + sg * (ct + r * math.cos(math.radians(a))), cv + r * math.sin(math.radians(a))))
    for k in range(1, n):  # far end, 90 -> 270 deg
        a = math.radians(90 + 180 * k / n)
        pts.append((cu + sg * (-ct + r * math.cos(a)), cv + r * math.sin(a)))
    return pts
