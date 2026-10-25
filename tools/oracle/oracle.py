"""Makes tests/cases.json: random views put through random sequences of
pans, zooms, turns, resizes, fits and zoom boxes, worked out a different
way from the library (each view is a 3x3 matrix from world to screen, and
each step multiplies it), for the Tessel tests to compare against.

Needs numpy. Run from the library's folder:

    python3 tools/oracle/oracle.py

Each case gives the starting view, the steps, then where some world
points show, which world points some screen points show, and the view's
center, scale and angle at the end.

Author: Alexius Academia
Date: 2026-10-25
"""

import json
import math
import random

import numpy as np

random.seed(20261025)
MIN_SCALE, MAX_SCALE = 1e-9, 1e9


def T(x, y):
    return np.array([[1.0, 0, x], [0, 1.0, y], [0, 0, 1.0]])


def S(f):
    return np.array([[f, 0, 0], [0, f, 0], [0, 0, 1.0]])


def R(a):
    """A turn by a in the screen's y-down coordinates (clockwise as seen)."""
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


class Model:
    def __init__(self, w, h, cx, cy, scale, angle, ydown):
        self.w, self.h, self.ydown = w, h, ydown
        flip = np.diag([1.0, 1.0 if ydown else -1.0, 1.0])
        # Turned counterclockwise as seen: R(-angle) in y-down screen terms.
        self.M = T(w / 2, h / 2) @ R(-angle) @ S(scale) @ flip @ T(-cx, -cy)
        self.content = None
        self.keep = False
        self.sight = 40.0
        self.margin = 20.0

    def scale(self):
        return math.sqrt(abs(np.linalg.det(self.M[:2, :2])))

    def angle(self):
        # Where the world's +x points on the screen, measured counterclockwise.
        v = self.M[:2, :2] @ np.array([1.0, 0.0])
        return math.atan2(-v[1], v[0])

    def screen(self, x, y):
        p = self.M @ np.array([x, y, 1.0])
        return p[0], p[1]

    def world(self, sx, sy):
        p = np.linalg.solve(self.M, np.array([sx, sy, 1.0]))
        return p[0], p[1]

    def center(self):
        return self.world(self.w / 2, self.h / 2)

    def keep_content(self):
        if not self.keep or self.content is None:
            return
        x1, y1, x2, y2 = self.content
        pts = [self.screen(x, y) for x, y in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]]
        lo_x, hi_x = min(p[0] for p in pts), max(p[0] for p in pts)
        lo_y, hi_y = min(p[1] for p in pts), max(p[1] for p in pts)
        need_x, need_y = min(self.sight, hi_x - lo_x), min(self.sight, hi_y - lo_y)
        dx = dy = 0.0
        if hi_x < need_x:
            dx = need_x - hi_x
        elif lo_x > self.w - need_x:
            dx = self.w - need_x - lo_x
        if hi_y < need_y:
            dy = need_y - hi_y
        elif lo_y > self.h - need_y:
            dy = self.h - need_y - lo_y
        self.M = T(dx, dy) @ self.M

    def pan(self, dx, dy):
        self.M = T(dx, dy) @ self.M
        self.keep_content()

    def zoom(self, f, sx, sy):
        s = self.scale()
        f = min(max(s * f, MIN_SCALE), MAX_SCALE) / s
        self.M = T(sx, sy) @ S(f) @ T(-sx, -sy) @ self.M
        self.keep_content()

    def rotate(self, a, sx, sy):
        self.M = T(sx, sy) @ R(-a) @ T(-sx, -sy) @ self.M
        self.keep_content()

    def resize(self, w, h):
        self.M = T((w - self.w) / 2, (h - self.h) / 2) @ self.M
        self.w, self.h = w, h

    def place(self, x, y, scale):
        """Puts world (x, y) at the middle at `scale`, keeping the turn."""
        f = scale / self.scale()
        self.M = S(f) @ self.M
        sx, sy = self.screen(x, y)
        self.M = T(self.w / 2 - sx, self.h / 2 - sy) @ self.M
        self.keep_content()

    def fit(self, box):
        x1, y1, x2, y2 = box
        L = self.M[:2, :2] / self.scale()
        pts = [L @ np.array([x, y]) for x, y in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]]
        across = max(p[0] for p in pts) - min(p[0] for p in pts)
        up = max(p[1] for p in pts) - min(p[1] for p in pts)
        room_x, room_y = max(self.w - 2 * self.margin, 1), max(self.h - 2 * self.margin, 1)
        scale = self.scale()
        if across > 1e-12 and up > 1e-12:
            scale = min(room_x / across, room_y / up)
        elif across > 1e-12:
            scale = room_x / across
        elif up > 1e-12:
            scale = room_y / up
        self.place((x1 + x2) / 2, (y1 + y2) / 2, min(max(scale, MIN_SCALE), MAX_SCALE))

    def screen_box(self, x1, y1, x2, y2):
        w, h = abs(x2 - x1), abs(y2 - y1)
        if w < 1 or h < 1:
            return
        cx, cy = self.world((x1 + x2) / 2, (y1 + y2) / 2)
        scale = min(max(self.scale() * min(self.w / w, self.h / h), MIN_SCALE), MAX_SCALE)
        self.place(cx, cy, scale)


def rnd_box():
    x, y = random.uniform(-500, 500), random.uniform(-500, 500)
    kind = random.random()
    w = random.uniform(1, 400) if kind > 0.1 else 0.0
    h = random.uniform(1, 400) if kind > 0.2 or kind < 0.05 else 0.0
    return [x, y, x + w, y + h]


def case():
    w, h = random.uniform(100, 1200), random.uniform(80, 900)
    start = {
        "width": w, "height": h,
        "centerX": random.uniform(-200, 200), "centerY": random.uniform(-200, 200),
        "scale": math.exp(random.uniform(-4, 4)),
        "angle": random.choice([0.0, 0.0, random.uniform(-3, 3)]),
        "yDown": random.random() < 0.3,
    }
    m = Model(w, h, start["centerX"], start["centerY"], start["scale"], start["angle"], start["yDown"])
    keep = random.random() < 0.25
    content = rnd_box() if keep or random.random() < 0.5 else []
    if content:
        m.content = content
        m.keep = keep
    steps = []
    for _ in range(random.randint(1, 12)):
        op = random.choice(["pan", "pan", "zoom", "zoom", "rotate", "resize", "fit", "box", "scale", "angle"])
        if op == "pan":
            a = [random.uniform(-300, 300), random.uniform(-300, 300)]
            m.pan(*a)
        elif op == "zoom":
            a = [math.exp(random.uniform(-1.5, 1.5)), random.uniform(0, m.w), random.uniform(0, m.h)]
            m.zoom(*a)
        elif op == "rotate":
            a = [random.uniform(-2, 2), random.uniform(0, m.w), random.uniform(0, m.h)]
            m.rotate(*a)
        elif op == "resize":
            a = [random.uniform(100, 1200), random.uniform(80, 900)]
            m.resize(*a)
        elif op == "fit":
            a = rnd_box()
            m.fit(a)
        elif op == "box":
            a = [random.uniform(0, m.w), random.uniform(0, m.h), random.uniform(0, m.w), random.uniform(0, m.h)]
            m.screen_box(*a)
        elif op == "scale":
            a = [math.exp(random.uniform(-4, 4))]
            m.zoom(a[0] / m.scale(), m.w / 2, m.h / 2)
        else:
            a = [random.uniform(-3, 3)]
            d = a[0] - m.angle()
            m.rotate(d, m.w / 2, m.h / 2)
        steps.append({"op": op, "args": a})
    cx, cy = m.center()
    worlds = [[random.uniform(-600, 600), random.uniform(-600, 600)] for _ in range(4)] + [[cx, cy]]
    screens = [[random.uniform(0, m.w), random.uniform(0, m.h)] for _ in range(4)]
    return {
        **start, "content": content, "keepInSight": keep, "steps": steps,
        "worlds": worlds, "toScreen": [list(m.screen(x, y)) for x, y in worlds],
        "screens": screens, "toWorld": [list(m.world(x, y)) for x, y in screens],
        "endCenterX": cx, "endCenterY": cy, "endScale": m.scale(), "endAngle": m.angle(),
    }


def main():
    cases = [case() for _ in range(1500)]
    with open("tests/cases.json", "w") as f:
        json.dump({"cases": cases}, f)
    steps = sum(len(c["steps"]) for c in cases)
    checks = sum(len(c["worlds"]) * 2 + len(c["screens"]) * 2 + 4 for c in cases)
    print(f"{len(cases)} views, {steps} steps, {checks} values -> tests/cases.json")


main()
