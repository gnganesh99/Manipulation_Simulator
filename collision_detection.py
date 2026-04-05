

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
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
    Check for collisions across the manipulation path from initial to final coordinates with given labels (obstacles).
    Inputs:
        - initial: initial coordinates
        - final: final coordinates
        - labels: array of shape (N, 2) containing the coordinates of the labels (obstacles)
        - object_width: width of the object being manipulated (float)
        - padding: additional padding to consider around the obstacles (float)

    Outputs:
        - collision_indices: list of indices of labels that collide with the path from initial to final coordinates
    """


    initial = np.array(initial).ravel()
    final = np.array(final).ravel() 
    collision_indices = []
    for i, label in enumerate(labels):
        obstacle = Rect(label[0], label[1], object_width, object_width, padding)
        if segment_hits_rect(initial, final, obstacle):
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
    Return the first point of collision along the segment from initial to final.

    Inputs:
        - initial:      initial coordinates
        - final:        final coordinates
        - labels:       array of shape (N, 2) with obstacle positions
        - object_width: width of each square obstacle
        - padding:      additional padding around each obstacle

    Outputs:
        - The (x, y) point of first collision, or None if the path is clear.
    """
    initial = np.array(initial).ravel()
    final = np.array(final).ravel()
    labels = np.array(labels).reshape(-1, 2)

    collision_indices = get_collision_indices(initial, final, labels, object_width, padding)
    if not collision_indices or len(collision_indices) == 0:
        return None

    best_point = None
    best_dist = float('inf')

    for i in collision_indices:
        label = labels[i]
        obstacle = Rect(label[0], label[1], object_width, object_width, padding)

        # If initial is already inside the obstacle, it is the collision point
        if obstacle.contains(*initial):
            return tuple(initial)

        point = segment_rect_intersection_point(initial, final, obstacle)
        point = np.asarray(point).ravel() if point is not None else None
        if point is not None:
            dist = (point[0] - initial[0]) ** 2 + (point[1] - initial[1]) ** 2
            if dist < best_dist:
                best_dist = dist
                best_point = point

    return np.asarray(best_point, dtype=np.float32).ravel() if best_point is not None else None