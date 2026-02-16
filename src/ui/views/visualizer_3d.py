import matplotlib
import sys

# Set backend based on OS/Environment if needed, but TkAgg is generally best for Tkinter integration.
# On some Mac systems, this might need adjustment, but TkAgg is the standard for embedding.
matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
import numpy as np
from typing import Tuple, List, Optional


class Visualizer3D(ctk.CTkFrame):
    """Center panel: 3D robot visualization (no controls)."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # ── Matplotlib Figure ──
        self.fig = plt.Figure(figsize=(10, 8), facecolor='#2b2b2b')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#1e1e1e')

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ── Plot Elements ──
        self.line, = self.ax.plot([], [], [], '-o', lw=6, color='#3498db',
                                  mfc='#f1c40f', ms=8, label='Robot Arm')
        self.shadow_xy, = self.ax.plot([], [], [], '-', color='#3498db',
                                       alpha=0.25, lw=4, label='Floor Shadow')
        self.shadow_lines: list = []

        self.target_dot, = self.ax.plot([], [], [], 'rx', ms=12,
                                        markeredgewidth=2, label='IK Target')

        self.traj_line, = self.ax.plot([], [], [], '-', lw=3, color='#2ecc71',
                                       alpha=0.8, label='Planned Path')
        self.traj_points, = self.ax.plot([], [], [], 'o', color='#27ae60',
                                         ms=8, markeredgewidth=2,
                                         markeredgecolor='white')

        self.gripper_left, = self.ax.plot([], [], [], '-', lw=3, color='#e74c3c')
        self.gripper_right, = self.ax.plot([], [], [], '-', lw=3, color='#e74c3c')

        # ── Defaults ──
        self.base_limits = ([-25, 25], [-25, 25], [0, 35])
        self.scale = 1.0
        self._setup_axes()

    def _setup_axes(self):
        self.ax.set_xlabel('X (cm)', color='white', fontsize=10, labelpad=8)
        self.ax.set_ylabel('Y (cm)', color='white', fontsize=10, labelpad=8)
        self.ax.set_zlabel('Z (cm)', color='white', fontsize=10, labelpad=8)
        self.ax.set_title('Robot Manipulator', color='white',
                          fontsize=14, weight='bold', pad=15)
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        for pane in (self.ax.xaxis.pane, self.ax.yaxis.pane, self.ax.zaxis.pane):
            pane.fill = True
            pane.set_alpha(0.05)

        self.ax.view_init(elev=20, azim=-60)
        self.ax.legend(loc='upper right', fontsize=9, facecolor='#2b2b2b',
                       edgecolor='white', labelcolor='white', framealpha=0.8)
        self._apply_scale()

    # ═══════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════

    def set_title(self, title: str):
        self.ax.set_title(title, color='white', fontsize=14, weight='bold', pad=15)

    def set_scale(self, scale: float):
        self.scale = scale
        self._apply_scale()

    def _apply_scale(self):
        for lim, setter in zip(self.base_limits,
                               [self.ax.set_xlim, self.ax.set_ylim, self.ax.set_zlim]):
            c = (lim[0] + lim[1]) / 2
            r = (lim[1] - lim[0]) / self.scale
            setter(c - r / 2, c + r / 2)
        self.canvas.draw_idle()

    def set_perspective(self, elev: float, azim: float):
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw_idle()

    def reset_view(self):
        self.set_scale(1.0)
        self.set_perspective(20, -60)

    def update_robot(self, points: np.ndarray,
                     gripper: Tuple[np.ndarray, np.ndarray],
                     has_collision: bool = False):
        if points is None or len(points) == 0:
            return

        color = '#e74c3c' if has_collision else '#3498db'
        gripper_color = '#c0392b' if has_collision else '#e74c3c'

        # Arm
        self.line.set_data(points[:, 0], points[:, 1])
        self.line.set_3d_properties(points[:, 2])
        self.line.set_color(color)

        # Dynamic shadow lines
        n = len(points)
        while len(self.shadow_lines) < n:
            ln, = self.ax.plot([], [], [], ':', color='gray', alpha=0.4, lw=1.5)
            self.shadow_lines.append(ln)

        for i, pt in enumerate(points):
            self.shadow_lines[i].set_data([pt[0], pt[0]], [pt[1], pt[1]])
            self.shadow_lines[i].set_3d_properties([pt[2], 0])
        for i in range(n, len(self.shadow_lines)):
            self.shadow_lines[i].set_data([], [])
            self.shadow_lines[i].set_3d_properties([])

        # Floor shadow
        self.shadow_xy.set_data(points[:, 0], points[:, 1])
        self.shadow_xy.set_3d_properties(np.zeros_like(points[:, 2]))

        # Gripper
        left, right = gripper
        if left is not None and len(left) > 0:
            self.gripper_left.set_data(left[:, 0], left[:, 1])
            self.gripper_left.set_3d_properties(left[:, 2])
            self.gripper_left.set_color(gripper_color)
            self.gripper_right.set_data(right[:, 0], right[:, 1])
            self.gripper_right.set_3d_properties(right[:, 2])
            self.gripper_right.set_color(gripper_color)

        self.canvas.draw_idle()

    def show_trajectory_waypoints(self, cartesian_points: Optional[List] = None):
        """Draw/clear planned waypoint markers."""
        if cartesian_points and len(cartesian_points) > 0:
            pts = np.array(cartesian_points)
            self.traj_line.set_data(pts[:, 0], pts[:, 1])
            self.traj_line.set_3d_properties(pts[:, 2])
            self.traj_points.set_data(pts[:, 0], pts[:, 1])
            self.traj_points.set_3d_properties(pts[:, 2])
        else:
            self.traj_line.set_data([], [])
            self.traj_line.set_3d_properties([])
            self.traj_points.set_data([], [])
            self.traj_points.set_3d_properties([])
        self.canvas.draw_idle()

    def set_trajectory_visible(self, visible: bool):
        a = 0.8 if visible else 0.0
        self.traj_line.set_alpha(a)
        self.traj_points.set_alpha(1.0 if visible else 0.0)
        self.canvas.draw_idle()
