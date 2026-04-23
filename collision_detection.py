

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Rect:
    """A simple axis-aligned rectangular obstacle."""

    x: float
    y: float
    w: float
    h: float
    padding:Optional[float] = 0.0 # Optional padding for collision checks



    def contains(self, px: float, py: float) -> bool:
        """Return True if point (px,py) lies inside the rectangle."""
        return self.x - self.padding <= px <= self.x + self.w + self.padding and self.y - self.padding <= py <= self.y + self.h + self.padding

    def edges(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Return a list of 4 edges (as point pairs) defining the rectangle."""
        x0, y0, x1, y1 = self.x - self.padding, self.y - self.padding, self.x + (self.w + self.padding), self.y + (self.h + self.padding)
        return [((x0, y0), (x1, y0)),
                ((x1, y0), (x1, y1)),
                ((x1, y1), (x0, y1)),
                ((x0, y1), (x0, y0))]

# Circular obstacles
@dataclass
class Circle:

    x: float
    y: float
    r: float
    padding: Optional[float] = 0.0  # Optional padding for collision checks


    def contains(self, px: float, py: float) -> bool:
        """Return True if point (px,py) lies inside the circle."""
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= (self.r + self.padding) ** 2


EPSILON = 1e-9
SELF_MATCH_TOL = 1e-6
CONTACT_BACKOFF = 1e-6


def _as_point(point) -> np.ndarray:
    """Return a 2D point as a flat float array."""
    arr = np.asarray(point, dtype=np.float64).ravel()
    if arr.size != 2:
        raise ValueError(f"Expected a 2D point, got shape {arr.shape}")
    return arr


def _as_centers(labels) -> np.ndarray:
    """Return obstacle centers as an (N, 2) float array."""
    arr = np.asarray(labels, dtype=np.float64)
    if arr.size == 0:
        return np.empty((0, 2), dtype=np.float64)
    return arr.reshape(-1, 2)


def _effective_collision_radius(object_width: float, padding: float) -> float:
    """
    Treat labels as particle centers and object_width as the effective stop distance.

    The caller currently passes the particle diameter here; for equal-sized particles
    that is also the center-to-center contact distance. Negative padding from older
    rectangle-based logic is ignored so we stop on first contact instead of allowing
    visible overlap.
    """
    collision_radius = float(object_width)
    if padding > 0:
        collision_radius += float(padding)
    return max(collision_radius, 0.0)


def _self_indices_to_ignore(initial: np.ndarray, labels: np.ndarray) -> set[int]:
    """
    Ignore one obstacle that is effectively the moving particle's current position.

    prediction_utils tries to remove the active particle before calling into this file,
    but if that exact match fails because of float noise we still do not want the
    particle to collide with itself immediately.
    """
    if len(labels) == 0:
        return set()

    distances = np.linalg.norm(labels - initial, axis=1)
    matches = np.where(distances <= SELF_MATCH_TOL)[0]
    if len(matches) == 1:
        return {int(matches[0])}
    return set()


def _segment_circle_contact_t(
    initial: np.ndarray,
    final: np.ndarray,
    center: np.ndarray,
    radius: float,
) -> Optional[float]:
    """Return the earliest contact parameter t in [0, 1], or None if no contact."""
    direction = final - initial
    a = float(np.dot(direction, direction))
    if a <= EPSILON:
        return 0.0 if np.dot(initial - center, initial - center) <= radius * radius + EPSILON else None

    relative = initial - center
    c = float(np.dot(relative, relative) - radius * radius)
    if c <= EPSILON:
        return 0.0

    b = float(2.0 * np.dot(relative, direction))
    disc = b * b - 4.0 * a * c
    if disc < -EPSILON:
        return None

    disc = max(disc, 0.0)
    sqrt_disc = math.sqrt(disc)
    roots = [(-b - sqrt_disc) / (2.0 * a), (-b + sqrt_disc) / (2.0 * a)]
    valid_roots = [min(max(t, 0.0), 1.0) for t in roots if -EPSILON <= t <= 1.0 + EPSILON]
    if not valid_roots:
        return None

    return min(valid_roots)


def _contact_point(initial: np.ndarray, final: np.ndarray, t: float) -> np.ndarray:
    """
    Return a point on the segment just before contact to avoid tiny numerical overlap.
    """
    if t <= 0.0:
        return initial.copy()

    direction = final - initial
    segment_length = float(np.linalg.norm(direction))
    if segment_length <= EPSILON:
        return initial.copy()

    safe_t = max(0.0, t - CONTACT_BACKOFF / segment_length)
    return initial + safe_t * direction



def orientation(a, b, c) -> int:
    """Helper for segment intersection: orientation of triplet (a,b,c)."""

    val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(val) < 1e-12:
        return 0
    return 1 if val > 0 else 2


def on_segment(a, b, c) -> bool:
    """Return True if point b lies on segment a–c."""
    return (min(a[0], c[0]) - 1e-12 <= b[0] <= max(a[0], c[0]) + 1e-12 and
            min(a[1], c[1]) - 1e-12 <= b[1] <= max(a[1], c[1]) + 1e-12)


def segments_intersect(p1, q1, p2, q2) -> bool:
    """Check if line segments p1–q1 and p2–q2 intersect."""
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_segment(p1, p2, q1): return True
    if o2 == 0 and on_segment(p1, q2, q1): return True
    if o3 == 0 and on_segment(p2, p1, q2): return True
    if o4 == 0 and on_segment(p2, q1, q2): return True
    return False


def segment_hits_rect(p, q, rect: Rect) -> bool:
    """Return True if segment p–q intersects rectangle or lies inside it."""
    # Check if segment endpoints are inside the rectangle
    if rect.contains(*p) or rect.contains(*q):
        return True

    # Check for intersections with rectangle edges
    for e in rect.edges():
        if segments_intersect(p, q, e[0], e[1]):
            return True

    return False


def get_collision_indices(initial, final, labels, object_width, padding = 0):

    """
    Check whether motion from initial to final hits any particle centers in labels.
    Inputs:
        - initial: initial coordinates
        - final: final coordinates
        - labels: array of shape (N, 2) containing obstacle center coordinates
        - object_width: effective center-to-center stop distance
        - padding: optional extra collision slack

    Outputs:
        - collision_indices: list of indices of labels that collide with the path from initial to final coordinates
    """


    initial = _as_point(initial)
    final = _as_point(final)
    labels = _as_centers(labels)
    collision_radius = _effective_collision_radius(object_width, padding)
    ignored_indices = _self_indices_to_ignore(initial, labels)
    collision_indices = []
    for i, label in enumerate(labels):
        if i in ignored_indices:
            continue
        if _segment_circle_contact_t(initial, final, label, collision_radius) is not None:
            collision_indices.append(i)
    
    return collision_indices






def segment_rect_intersection_point(p, q, rect: Rect) -> Optional[Tuple[float, float]]:
    """
    Return the first intersection point (closest to p) between segment p–q and a rectangle's edges.
    Returns None if no edge intersection is found.
    """
    px, py = p
    qx, qy = q
    dx, dy = qx - px, qy - py

    earliest_t = float('inf')
    earliest_point = None

    for (x1, y1), (x2, y2) in rect.edges():
        ex, ey = x2 - x1, y2 - y1

        denom = dx * ey - dy * ex
        if abs(denom) < 1e-12:
            continue  # Parallel

        t = ((x1 - px) * ey - (y1 - py) * ex) / denom
        u = ((x1 - px) * dy - (y1 - py) * dx) / denom

        if -1e-9 <= t <= 1.0 + 1e-9 and -1e-9 <= u <= 1.0 + 1e-9:
            if t < earliest_t:
                earliest_t = t
                earliest_point = (px + t * dx, py + t * dy)

    return earliest_point



def get_first_collision_point(
    initial,
    final,
    labels,
    object_width: float,
    padding: float = 0,
):
    """
    Return the first center position along the segment where a moving particle should stop.

    Inputs:
        - initial:      initial coordinates
        - final:        final coordinates
        - labels:       array of shape (N, 2) with obstacle center positions
        - object_width: effective center-to-center stop distance
        - padding:      optional extra collision slack

    Outputs:
        - The (x, y) point of first collision, or None if the path is clear.
    """
    initial = _as_point(initial)
    final = _as_point(final)
    labels = _as_centers(labels)
    collision_radius = _effective_collision_radius(object_width, padding)
    ignored_indices = _self_indices_to_ignore(initial, labels)

    if len(labels) == 0:
        return None

    best_t = float("inf")
    best_point = None

    for i, label in enumerate(labels):
        if i in ignored_indices:
            continue

        t = _segment_circle_contact_t(initial, final, label, collision_radius)
        if t is None:
            continue

        if t < best_t:
            best_t = t
            best_point = _contact_point(initial, final, t)

    return np.asarray(best_point, dtype=np.float32).ravel() if best_point is not None else None
