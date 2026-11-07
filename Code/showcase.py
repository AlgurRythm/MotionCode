# ============================================================
# MotionCode Studio Advanced - Capability Showcase
# 1920x1080 | 30 FPS | 50 seconds
# All motion is computed directly from t (scrub-safe).
# Requires claude_spark.obj in the working folder for the 3D hero.
# ============================================================
import math
import os

W, H = 1920, 1080
FPS = 30
DURATION = 50.0
TAU = 2.0 * math.pi

BG = "#050812"
WHITE = "#FFFFFF"
CYAN = "#00E5FF"
BLUE = "#2D7BFF"
DEEP = "#0B2A5A"
PURPLE = "#9B5CFF"
GRAY = "#7F93AD"
CORAL = "#E96C4A"

SPARK_SCALE = 0.22

CX, CY = W / 2.0, H / 2.0

# ------------------------------------------------------------
# Math / easing helpers
# ------------------------------------------------------------
def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def lerp(a, b, k):
    return a + (b - a) * k

def ease_out(k):
    k = clamp(k)
    return 1.0 - (1.0 - k) ** 3

def ease_in_out(k):
    k = clamp(k)
    if k < 0.5:
        return 4.0 * k * k * k
    return 1.0 - ((-2.0 * k + 2.0) ** 3) / 2.0

def seg(t, a, b, ease=ease_in_out):
    """Eased 0..1 progress between a and b seconds."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return ease((t - a) / (b - a))

def vis(t, a, b, fin=0.5, fout=0.5):
    """Fade in from a, hold, fade out before b. Zero outside [a, b]."""
    if t < a or t > b:
        return 0.0
    i = ease_out((t - a) / max(fin, 1e-6))
    o = 1.0 - ease_in_out((t - (b - fout)) / max(fout, 1e-6))
    return clamp(min(i, o))

def pulse(t, freq, phase=0.0):
    return math.sin(TAU * freq * t + phase)

# ------------------------------------------------------------
# Object registry
# ------------------------------------------------------------
ALL = []      # every object name, in creation order
KIND = {}     # name -> "text" | "other"

def _reg(name, kind="other"):
    if name in KIND:
        raise ValueError("Duplicate object name: " + name)
    ALL.append(name)
    KIND[name] = kind

# Every shape below is placed with x/y at its own center, and its points
# are stored relative to that center. This makes rotation and scale pivot
# around the shape's middle instead of the screen's middle.

def c_circle(scene, n, x, y, r, color, stroke=2, filled=False):
    _reg(n)
    scene.add_circle(n, x=x, y=y, radius=r, color=color, stroke=stroke, filled=filled)

def c_rect(scene, n, x, y, w, h, color, stroke=2, filled=False):
    _reg(n)
    scene.add_rect(n, x=x, y=y, width=w, height=h, color=color, stroke=stroke, filled=filled)

def c_rrect(scene, n, x, y, w, h, color, stroke=2, filled=False):
    _reg(n)
    r = min(22.0, w / 4.0, h / 4.0)
    pts = []
    for cx, cy, start in ((w/2-r, -h/2+r, -90), (w/2-r, h/2-r, 0),
                          (-w/2+r, h/2-r, 90), (-w/2+r, -h/2+r, 180)):
        for j in range(7):
            a = math.radians(start + j * 90 / 6)
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    scene.add_polygon(n, x=x, y=y, points=pts, color=color, stroke=stroke,
                      filled=filled, closed=True)

def c_ellipse(scene, n, x, y, rx, ry, color, stroke=2, filled=False):
    _reg(n)
    pts = [(rx*math.cos(TAU*i/48), ry*math.sin(TAU*i/48)) for i in range(48)]
    scene.add_polygon(n, x=x, y=y, points=pts, color=color, stroke=stroke,
                      filled=filled, closed=True)

def c_line(scene, n, x, y, x2, y2, color, stroke=2):
    # x2/y2 are absolute end coordinates; the line pivots at its start point.
    _reg(n)
    scene.add_line(n, x=x, y=y, x2=x2 - x, y2=y2 - y, color=color, stroke=stroke)

def c_star(scene, n, x, y, r, color, stroke=2, filled=False):
    _reg(n)
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = -math.pi/2 + i * math.pi/5
        pts.append((rr*math.cos(a), rr*math.sin(a)))
    scene.add_polygon(n, x=x, y=y, points=pts, color=color, stroke=stroke,
                      filled=filled, closed=True)

def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def c_poly(scene, n, pts, color, stroke=2, filled=False, closed=True):
    _reg(n)
    cx, cy = _centroid(pts)
    local = [(px - cx, py - cy) for px, py in pts]
    scene.add_polygon(n, x=cx, y=cy, points=local, color=color, stroke=stroke,
                      filled=filled, closed=closed)

def c_polyline(scene, n, pts, color, stroke=2):
    _reg(n)
    cx, cy = _centroid(pts)
    local = [(px - cx, py - cy) for px, py in pts]
    scene.add_polyline(n, x=cx, y=cy, points=local, color=color, stroke=stroke)

def c_text(scene, n, text, x, y, size, color, bold=True, align="center"):
    _reg(n, "text")
    scene.add_text(n, text, x=x, y=y, size=size, color=color, bold=bold, align=align)

def c_mesh(scene, adder, n, **kw):
    _reg(n)
    adder(n, **kw)

# ------------------------------------------------------------
# Polygon point helpers (absolute screen coordinates)
# ------------------------------------------------------------
def ngon_points(cx, cy, r, n):
    return [(cx + r * math.cos(-math.pi / 2 + i * TAU / n),
             cy + r * math.sin(-math.pi / 2 + i * TAU / n)) for i in range(n)]

# ------------------------------------------------------------
# build(scene)
# ------------------------------------------------------------
def build(scene):
    scene.width = W
    scene.height = H
    scene.fps = FPS
    scene.duration = DURATION
    scene.background = BG

    # ---------- Scene 1: identity ----------
    for i in range(8):
        a = TAU * i / 8.0
        c_circle(scene, "id_dot_%d" % i, CX + 260 * math.cos(a), CY + 260 * math.sin(a),
                 10, CYAN, 2, True)
    c_circle(scene, "id_ring_outer", CX, CY, 260, BLUE, 2)
    c_circle(scene, "id_ring_inner", CX, CY, 180, CYAN, 1)
    c_rect(scene, "id_square", CX, CY, 140, 140, BLUE, 2)
    c_text(scene, "id_title", "MOTIONCODE", CX, 500, 120, WHITE)
    c_text(scene, "id_sub", "Animation through Python.", CX, 620, 40, CYAN, False)

    # ---------- Scene 2: 2D capabilities ----------
    c_text(scene, "s2_label", "2D ENGINE", 960, 110, 44, CYAN)
    c_circle(scene, "s2_ring_a", 420, 460, 150, BLUE, 2)
    c_circle(scene, "s2_ring_b", 420, 460, 110, CYAN, 2)
    c_circle(scene, "s2_ring_c", 420, 460, 70, WHITE, 1)
    c_rrect(scene, "s2_rrect", 960, 460, 260, 160, CYAN, 3)
    c_ellipse(scene, "s2_ellipse", 1500, 460, 170, 90, PURPLE, 3)
    c_star(scene, "s2_star", 960, 760, 120, WHITE, 2)
    c_poly(scene, "s2_poly", ngon_points(1500, 760, 120, 6), BLUE, 3)
    c_polyline(scene, "s2_polyline", [(260, 760), (380, 680), (520, 820), (660, 700)], CYAN, 2)
    c_text(scene, "s2_lbl_rings", "CIRCLES AND RINGS", 420, 680, 26, GRAY, False)
    c_text(scene, "s2_lbl_rrect", "ROUNDED RECTANGLES", 960, 580, 26, GRAY, False)
    c_text(scene, "s2_lbl_ellipse", "ELLIPSES", 1500, 600, 26, GRAY, False)
    c_text(scene, "s2_lbl_star", "STARS", 960, 920, 26, GRAY, False)
    c_text(scene, "s2_lbl_poly", "CUSTOM POLYGONS", 1500, 930, 26, GRAY, False)

    # ---------- Scene 3: typography ----------
    c_text(scene, "s3_big", "PRECISION", CX, 420, 150, WHITE, True, "center")
    c_text(scene, "s3_mid", "COMPOSITION", CX, 560, 80, CYAN, False, "center")
    c_text(scene, "s3_left", "ALIGN LEFT", 300, 760, 40, BLUE, True, "left")
    c_text(scene, "s3_right", "ALIGN RIGHT", 1620, 760, 40, BLUE, True, "right")
    c_rect(scene, "s3_frame", CX, 480, 1300, 520, CYAN, 1)
    c_line(scene, "s3_guide_h", 300, 540, 1620, 540, DEEP, 1)
    c_line(scene, "s3_guide_v", 960, 240, 960, 840, DEEP, 1)

    # ---------- Scene 4: 3D wireframes ----------
    obj3d = [
        ("w_cube",     "cube",     380, 320, 150),
        ("w_sphere",   "sphere",   760, 320, 150),
        ("w_pyramid",  "pyramid", 1160, 320, 150),
        ("w_cone",     "cone",    1540, 320, 150),
        ("w_cylinder", "cylinder", 380, 760, 150),
        ("w_torus",    "torus",    760, 760, 150),
        ("w_plane",    "plane",   1160, 760, 150),
    ]
    for n, kind, x, y, s in obj3d:
        if kind == "cube":
            c_mesh(scene, scene.add_cube, n, x=x, y=y, z=0, size=s, color=CYAN)
        elif kind == "sphere":
            c_mesh(scene, scene.add_sphere, n, x=x, y=y, z=0, size=s, color=BLUE)
        elif kind == "pyramid":
            c_mesh(scene, scene.add_pyramid, n, x=x, y=y, z=0, size=s, color=PURPLE)
        elif kind == "cone":
            c_mesh(scene, scene.add_cone, n, x=x, y=y, z=0, radius=s * 0.5, height=s, color=CYAN)
        elif kind == "cylinder":
            c_mesh(scene, scene.add_cylinder, n, x=x, y=y, z=0, radius=s * 0.45, height=s, color=BLUE)
        elif kind == "torus":
            c_mesh(scene, scene.add_torus, n, x=x, y=y, z=0, size=s, color=WHITE)
        elif kind == "plane":
            c_mesh(scene, scene.add_plane, n, x=x, y=y, z=0, size=s, color=CYAN)
    c_text(scene, "s4_title", "3D WIREFRAME MESHES", CX, 120, 56, WHITE)
    c_text(scene, "s4_note", "Rendered as wireframes, not solid models", CX, 1010, 28, GRAY, False)

    # Hero: the supplied Claude spark OBJ mesh (fades in late in scene 4)
    # If claude_spark.obj is not beside the script, use a torus so the scene still runs.
    if os.path.exists("claude_spark.obj"):
        c_mesh(scene, lambda n, **kw: scene.add_obj(n, path="claude_spark.obj", **kw),
               "Claude_Spark_3D", x=CX, y=CY, z=0, scale=SPARK_SCALE, color=CORAL, stroke=2)
    else:
        c_mesh(scene, scene.add_torus, "Claude_Spark_3D", x=CX, y=CY, z=0,
               size=340, color=CORAL, stroke=2)

    # ---------- Scene 5: procedural geometry ----------
    for i in range(12):
        a = TAU * i / 12.0
        c_star(scene, "p_star_%d" % i, CX + 330 * math.cos(a), CY + 330 * math.sin(a),
               40, CYAN if i % 2 == 0 else BLUE, 2)
    for ring in range(3):
        c_poly(scene, "p_hex_%d" % ring, ngon_points(CX, CY, 120 + ring * 90, 6),
               [CYAN, BLUE, PURPLE][ring], 2)
    c_circle(scene, "p_core", CX, CY, 60, WHITE, 2)
    for i in range(6):
        a = TAU * i / 6.0
        c_line(scene, "p_spoke_%d" % i, CX, CY,
               CX + 420 * math.cos(a), CY + 420 * math.sin(a), DEEP, 1)
    c_text(scene, "s5_title", "PROCEDURAL GEOMETRY", CX, 110, 52, WHITE)

    # ---------- Scene 6: final composition ----------
    c_text(scene, "s6_tag", "YOUR CODE. YOUR MOTION.", CX, 470, 96, WHITE)
    c_text(scene, "s6_brand", "MOTIONCODE STUDIO", CX, 640, 72, CYAN)
    c_text(scene, "s6_sub", "Built with Python.", CX, 740, 36, GRAY, False)
    c_circle(scene, "s6_ring", CX, 860, 60, BLUE, 2)
    c_rect(scene, "s6_bar", CX, 860, 240, 4, CYAN, 1, True)

# ------------------------------------------------------------
# animate(scene, t)
# ------------------------------------------------------------
def animate(scene, t):
    t = clamp(t, 0.0, DURATION)
    F = {}   # name -> (opacity, props)

    def show(name, op, **props):
        F[name] = (clamp(op), props)

    master = 1.0 - seg(t, 48.8, 50.0)

    # ---------- Scene 1 ----------
    s1_out = 1.0 - seg(t, 5.2, 6.0)
    for i in range(8):
        a0 = TAU * i / 8.0
        e = seg(t, 0.3 + 0.1 * i, 1.6 + 0.1 * i, ease_out)
        r = lerp(520, 260, e)
        a = a0 + 0.25 * (1.0 - e) + TAU * t / 40.0
        show("id_dot_%d" % i, e * s1_out,
             x=CX + r * math.cos(a), y=CY + r * math.sin(a))
    e = seg(t, 0.8, 2.0, ease_out)
    show("id_ring_outer", e * s1_out, scale=lerp(1.6, 1.0, e), rotation=t * 6.0)
    show("id_ring_inner", seg(t, 1.2, 2.4, ease_out) * s1_out,
         scale=lerp(1.4, 1.0, seg(t, 1.2, 2.4, ease_out)), rotation=-t * 9.0)
    e = seg(t, 1.6, 2.8, ease_out)
    show("id_square", e * s1_out, rotation=45.0 * (1.0 - e) + t * 4.0, scale=lerp(0.5, 1.0, e))
    e = seg(t, 2.8, 3.9, ease_out)
    show("id_title", e * s1_out, y=500 + lerp(40, 0, e), scale=lerp(0.9, 1.0, e))
    e = seg(t, 3.8, 4.9, ease_out)
    show("id_sub", e * s1_out, y=620 + lerp(20, 0, e))

    # ---------- Scene 2 (6-15 s) ----------
    show("s2_label", vis(t, 5.8, 15.6, 0.6, 0.7))
    show("s2_ring_a", vis(t, 6.2, 15.6, 0.5, 0.6) * (0.75 + 0.25 * pulse(t, 0.5)),
         rotation=t * 20.0, scale=1.0 + 0.04 * pulse(t, 0.5))
    show("s2_ring_b", vis(t, 6.6, 15.6, 0.5, 0.6), rotation=-t * 30.0,
         scale=1.0 + 0.05 * pulse(t, 0.5, 1.0))
    show("s2_ring_c", vis(t, 7.0, 15.6, 0.5, 0.6), rotation=t * 45.0)
    show("s2_rrect", vis(t, 7.2, 15.6, 0.5, 0.6), rotation=8.0 * pulse(t, 0.2),
         scale=lerp(0.7, 1.0, seg(t, 7.2, 8.4, ease_out)))
    show("s2_ellipse", vis(t, 7.6, 15.6, 0.5, 0.6), rotation=t * 15.0,
         scale=lerp(0.6, 1.0, seg(t, 7.6, 8.8, ease_out)))
    show("s2_star", vis(t, 8.0, 15.6, 0.5, 0.6), rotation=t * 25.0,
         scale=1.0 + 0.06 * pulse(t, 0.4))
    show("s2_poly", vis(t, 8.4, 15.6, 0.5, 0.6), rotation=-t * 18.0)
    show("s2_polyline", vis(t, 8.8, 15.6, 0.5, 0.6))
    show("s2_lbl_rings", vis(t, 7.0, 15.6, 0.5, 0.6))
    show("s2_lbl_rrect", vis(t, 7.6, 15.6, 0.5, 0.6))
    show("s2_lbl_ellipse", vis(t, 8.0, 15.6, 0.5, 0.6))
    show("s2_lbl_star", vis(t, 8.4, 15.6, 0.5, 0.6))
    show("s2_lbl_poly", vis(t, 8.8, 15.6, 0.5, 0.6))

    # ---------- Scene 3 (15-22 s) ----------
    s3 = vis(t, 14.8, 22.6, 0.6, 0.7)
    e = seg(t, 15.2, 16.4, ease_out)
    show("s3_big", e * s3, scale=lerp(1.25, 1.0, e), y=420 + lerp(30, 0, e))
    e = seg(t, 15.8, 16.9, ease_out)
    show("s3_mid", e * s3, x=CX + lerp(-120, 0, e))
    show("s3_left", seg(t, 16.4, 17.5, ease_out) * s3, x=300 + lerp(-60, 0, seg(t, 16.4, 17.5, ease_out)))
    show("s3_right", seg(t, 16.6, 17.7, ease_out) * s3, x=1620 + lerp(60, 0, seg(t, 16.6, 17.7, ease_out)))
    show("s3_frame", vis(t, 17.0, 22.6, 0.6, 0.6) * 0.6, scale=1.0 + 0.01 * pulse(t, 0.4))
    show("s3_guide_h", vis(t, 17.4, 22.6, 0.6, 0.6))
    show("s3_guide_v", vis(t, 17.8, 22.6, 0.6, 0.6))

    # ---------- Scene 4 (22-33 s) ----------
    s4 = vis(t, 21.8, 33.6, 0.6, 0.7)
    show("s4_title", s4)
    show("s4_note", s4 * 0.8)
    obj_names = ["w_cube", "w_sphere", "w_pyramid", "w_cone",
                 "w_cylinder", "w_torus", "w_plane"]
    for i, n in enumerate(obj_names):
        e = seg(t, 22.4 + 0.25 * i, 23.6 + 0.25 * i, ease_out)
        g = seg(t, 30.0, 32.6)
        show(n, e * s4 * (1.0 - 0.7 * g),
             rotation_x=t * (20 + 5 * i), rotation_y=t * (30 - 3 * i),
             rotation_z=t * (10 + 2 * i), scale=lerp(0.6, 1.0, e) * (1.0 - 0.5 * g))

    # Claude spark hero: rises in as the wireframes gather, then exits.
    hero = seg(t, 31.0, 32.4, ease_out) * (1.0 - seg(t, 33.0, 33.6))
    show("Claude_Spark_3D", hero,
         rotation_x=12 + 5 * math.sin(t * 0.8),
         rotation_y=t * 28.0,
         rotation_z=4 * math.sin(t * 0.45),
         scale=SPARK_SCALE * (1.0 + 0.035 * math.sin(t * 1.5)))

    # ---------- Scene 5 (33-41 s) ----------
    s5 = vis(t, 32.8, 41.6, 0.6, 0.7)
    show("s5_title", s5)
    show("p_core", s5 * (0.6 + 0.4 * pulse(t, 0.8)), scale=1.0 + 0.1 * pulse(t, 0.8))
    for i in range(12):
        e = seg(t, 33.2 + 0.1 * i, 34.2 + 0.1 * i, ease_out)
        show("p_star_%d" % i, e * s5, rotation=t * 40.0 * (1 if i % 2 == 0 else -1),
             scale=0.8 + 0.3 * pulse(t, 0.5, i * 0.5))
    for ring in range(3):
        e = seg(t, 34.0 + 0.4 * ring, 35.4 + 0.4 * ring, ease_out)
        show("p_hex_%d" % ring, e * s5, rotation=t * (15 - 8 * ring),
             scale=0.9 + 0.1 * ring)
    for i in range(6):
        show("p_spoke_%d" % i, vis(t, 35.0, 41.6, 0.6, 0.6) * 0.6,
             rotation=t * 10.0 + i * 60.0)

    # ---------- Scene 6 (41-50 s) ----------
    e = seg(t, 41.4, 42.8, ease_out)
    show("s6_tag", e * (1.0 - seg(t, 47.0, 48.0)), y=470 + lerp(30, 0, e))
    e = seg(t, 42.6, 43.8, ease_out)
    show("s6_brand", e, y=640 + lerp(20, 0, e))
    show("s6_sub", seg(t, 44.0, 45.0, ease_out))
    show("s6_ring", seg(t, 44.6, 45.8, ease_out), rotation=t * 30.0)
    show("s6_bar", seg(t, 44.6, 45.8, ease_out), width=lerp(0.0, 240.0, seg(t, 44.6, 45.8, ease_out)))

    # ---------- Apply everything ----------
    for name in ALL:
        obj = scene.get_optional(name)
        if obj is None:
            continue
        op, props = F.get(name, (0.0, {}))
        obj.opacity = clamp(op * master)
        for key, val in props.items():
            setattr(obj, key, val)
