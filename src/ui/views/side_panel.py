import customtkinter as ctk
from typing import Callable, List
import threading
from ...services.robot_controller import RobotController
from ...data.config_loader import ConfigLoader
from pathlib import Path
from tkinter import filedialog, messagebox
import json
import shutil

class PanelCard(ctk.CTkFrame):
    """A styled container with a separate title area, NO BORDERS."""
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, border_width=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text=title, 
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        fg_color="transparent",
                                        corner_radius=6,
                                        anchor="w")
        self.title_label.pack(fill="x", padx=10, pady=(8, 2))
        
        self.content = ctk.CTkFrame(self, fg_color="transparent", border_width=0)
        self.content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

class SidePanel(ctk.CTkFrame):
    """
    Left panel with NO borders anywhere.
    Updated to include Recording and Import/Export features.
    """

    def __init__(self, parent, controller: RobotController,
                 config_loader: ConfigLoader, **kwargs):
        super().__init__(parent, fg_color="transparent", border_width=0, **kwargs)
        
        self.controller = controller
        self.config_loader = config_loader
        
        # Events
        self.on_robot_change: Callable = None
        self.on_solve_ik: Callable = None
        self.on_go_home: Callable = None
        self.on_run_trajectory: Callable = None
        self.on_joint_change: Callable = None 
        self.on_stop: Callable = None
        self.on_export: Callable = None
        self.on_import: Callable = None
        self.on_export: Callable = None
        self.on_import: Callable = None
        self.on_get_fk: Callable = None
        self.on_export_demos: Callable = None # New event
        
        # Recording state
        self.recorded_waypoints = []
        self.on_play_recording: Callable = None

        self.sliders: List[ctk.CTkSlider] = []
        self.joint_vars: List[ctk.StringVar] = []
        
        self._build_ui()

    def _build_ui(self):
        # 1. Header
        self._build_header()
        
        # 2. IK Card
        self._build_ik()
        
        # 3. Actions / Demo
        self._build_actions()

        # 5. Recording & Management (Bottom)
        self._build_management()
        
        # 4. FK Card (Expands)
        self._build_fk()

    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color=None, border_width=0) 
        frame.pack(fill="x", pady=(0, 15))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent", border_width=0)
        inner.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(inner, text="Robot Model:", 
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 2))
        
        row = ctk.CTkFrame(inner, fg_color="transparent", border_width=0)
        row.pack(fill="x")
        
        self.robot_var = ctk.StringVar()
        self.robot_combo = ctk.CTkComboBox(row, variable=self.robot_var,
                                           command=self._on_robot_selected, 
                                           height=32, border_width=1)
        self.robot_combo.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(row, text="📂", width=40, height=32, border_width=0,
                      command=self._import_config).pack(side="left")

    def _build_ik(self):
        card = PanelCard(self, title="Inverse Kinematics")
        card.pack(fill="x", pady=(0, 15))
        
        row1 = ctk.CTkFrame(card.content, fg_color="transparent", border_width=0)
        row1.pack(fill="x", pady=(0, 5))
        
        self.ik_entries = {}
        for coord in ['X', 'Y', 'Z']:
            f = ctk.CTkFrame(row1, fg_color="transparent", border_width=0)
            f.pack(side="left", fill="x", expand=True, padx=2)
            
            ctk.CTkLabel(f, text=coord, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            e = ctk.CTkEntry(f, height=32, placeholder_text="0.0", border_width=1, font=("Arial", 14))
            e.pack(fill="x")
            self.ik_entries[coord] = e
            if coord == 'X': e.insert(0, "15")
            if coord == 'Z': e.insert(0, "20")

        row2 = ctk.CTkFrame(card.content, fg_color="transparent", border_width=0)
        row2.pack(fill="x")
        
        ctk.CTkButton(row2, text="🎯 Solve", height=32, border_width=0,
                      command=self._solve_ik).pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        ctk.CTkButton(row2, text="📍 Get FK", height=32, border_width=0, fg_color="#d97706", hover_color="#b45309",
                      command=self._get_fk).pack(side="left", fill="x", expand=True, padx=(2, 2))

        ctk.CTkButton(row2, text="🏠 Home", height=32, fg_color="gray", border_width=0,
                      command=self._go_home).pack(side="left", fill="x", expand=True, padx=(2, 0))

    def _build_fk(self):
        self.fk_card = PanelCard(self, title="Forward Kinematics")
        self.fk_card.pack(fill="both", expand=True, pady=(0, 15))
        
        self.sliders_frame = ctk.CTkFrame(self.fk_card.content, fg_color="transparent", border_width=0)
        self.sliders_frame.pack(fill="both", expand=True)

    def _build_actions(self):
        # Rebranded as "Demo & Control"
        card = PanelCard(self, title="Demo Trajectories")
        card.pack(fill="x", pady=(0, 15))
        
        # Export Demos Button
        self.btn_export_demos = ctk.CTkButton(card.content, text="⬇ Export Demos JSON", height=24, 
                      fg_color="#475569", hover_color="#334155", border_width=0,
                      command=self._export_demos_json)
        self.btn_export_demos.pack(fill="x", pady=(0, 5))

        grid = ctk.CTkFrame(card.content, fg_color="transparent", border_width=0)
        grid.pack(fill="x")
        
        # 1-10 Buttons
        self.demo_buttons = []
        for i in range(1, 11):
            btn = ctk.CTkButton(grid, text=str(i), width=30, height=30, border_width=0,
                                command=lambda x=i: self._run_traj(x))
            r, c = (i-1)//5, (i-1)%5
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="ew")
            grid.columnconfigure(c, weight=1)
            self.demo_buttons.append(btn)
        
        ctk.CTkButton(card.content, text="⏹ EMERGENCY STOP", height=36, 
                      fg_color="#e74c3c", hover_color="#c0392b", border_width=0,
                      command=self._stop).pack(fill="x", pady=(10, 0))

    def _build_management(self):
        card = PanelCard(self, title="Trajectory Management")
        card.pack(side="bottom", fill="x")
        
        # Row 1: Recording
        row1 = ctk.CTkFrame(card.content, fg_color="transparent", border_width=0)
        row1.pack(fill="x", pady=(0, 5))
        
        ctk.CTkButton(row1, text="➕ Record Point", height=32, border_width=0, fg_color="#10b981", hover_color="#059669",
                      command=self._record_point).pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.lbl_points = ctk.CTkLabel(row1, text="0 pts", width=50, font=("Arial", 14, "bold"))
        self.lbl_points.pack(side="left", padx=2)

        ctk.CTkButton(row1, text="🗑️ Eliminar Punto", height=32, width=80, border_width=0, fg_color="#ef4444", hover_color="#dc2626",
                      command=self._delete_last_point).pack(side="left", padx=(2, 2))

        ctk.CTkButton(row1, text="▶ Play", height=32, border_width=0, fg_color="#8b5cf6", hover_color="#7c3aed",
                      command=self._play_recording).pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Row 2: File IO
        row2 = ctk.CTkFrame(card.content, fg_color="transparent", border_width=0)
        row2.pack(fill="x", pady=(5, 0))
        
        ctk.CTkButton(row2, text="📂 Import", height=28, border_width=0, fg_color="#64748b",
                      command=self._import_traj).pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        ctk.CTkButton(row2, text="💾 Export", height=28, border_width=0, fg_color="#64748b",
                      command=self._export_menu).pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.lbl_status = ctk.CTkLabel(card.content, text="", font=("Arial", 12), text_color="gray")
        self.lbl_status.pack(pady=(2, 0))

    # ── Logic ──
    
    def set_ik_values(self, x, y, z):
        self.ik_entries['X'].delete(0, "end")
        self.ik_entries['X'].insert(0, f"{x:.1f}")
        self.ik_entries['Y'].delete(0, "end")
        self.ik_entries['Y'].insert(0, f"{y:.1f}")
        self.ik_entries['Z'].delete(0, "end")
        self.ik_entries['Z'].insert(0, f"{z:.1f}")

    def _get_fk(self):
        if hasattr(self, 'on_get_fk') and self.on_get_fk: self.on_get_fk()

    def _record_point(self):
        # Get current joints from controller via callback or direct access? 
        # Better to ask parent to get current joints.
        # But we don't have direct access to controller joints here easily unless we passed controller.
        # We did pass controller!
        if self.controller.is_ready():
            joints = list(self.controller.current_joints)
            self.recorded_waypoints.append(joints)
            self.lbl_points.configure(text=f"{len(self.recorded_waypoints)} pts")
            self.set_export_status(f"Recorded pt {len(self.recorded_waypoints)}", "cyan")

    def _delete_last_point(self):
        if self.recorded_waypoints:
            self.recorded_waypoints.pop()
            self.lbl_points.configure(text=f"{len(self.recorded_waypoints)} pts")
            self.set_export_status(f"Deleted. {len(self.recorded_waypoints)} pts remain", "orange")
        else:
            self.set_export_status("No points to delete", "red")

    def _play_recording(self):
        if not self.recorded_waypoints:
            messagebox.showwarning("Empty", "No points recorded!")
            return
        if self.on_play_recording:
            self.on_play_recording(self.recorded_waypoints)

    def _import_traj(self):
        if self.on_import: self.on_import()

    def _export_menu(self):
        # Default to JSON export as it preserves structure better
        if self.on_export: self.on_export("json")

    def build_sliders(self, robot):
        for w in self.sliders_frame.winfo_children(): w.destroy()
        self.sliders.clear()
        self.joint_vars.clear()
        
        if not robot: return
        
        container = self.sliders_frame
        for i, link in enumerate(robot.links):
            self._add_slider_row(container, f"J{i+1}", link.limits, i)
        
        if robot.gripper:
             self._add_slider_row(container, "Gripper", robot.gripper.limits, len(robot.links), is_gripper=True)

    def _add_slider_row(self, parent, label, limits, idx, is_gripper=False):
        row = ctk.CTkFrame(parent, fg_color="transparent", border_width=0)
        row.pack(fill="x", pady=2)
        
        lbl_row = ctk.CTkFrame(row, fg_color="transparent", border_width=0)
        lbl_row.pack(fill="x")
        ctk.CTkLabel(lbl_row, text=label, font=("Arial", 12, "bold")).pack(side="left")
        
        var = ctk.StringVar(value="0")
        self.joint_vars.append(var)
        ctk.CTkLabel(lbl_row, textvariable=var, font=("Arial", 12), 
                      text_color="cyan").pack(side="right")
        
        mn, mx = limits
        color = None if not is_gripper else "#e74c3c"
        
        slider = ctk.CTkSlider(row, from_=mn, to=mx, height=16, border_width=0) 
        if color: slider.configure(progress_color=color, button_color="#c0392b")
        
        slider.set(0)
        slider.configure(command=lambda v, x=idx: self._on_slider(x, v))
        slider.pack(fill="x", pady=(2, 2))
        self.sliders.append(slider)

    def update_joints(self, values: List[float]):
        if len(values) != len(self.sliders): return
        for val, slider, var in zip(values, self.sliders, self.joint_vars):
            slider.set(val)
            var.set(f"{int(val)}")

    def _on_slider(self, idx, val):
        self.joint_vars[idx].set(f"{int(val)}")
        if self.on_joint_change: self.on_joint_change(idx, val)

    def _refresh_robots(self):
        robots = self.config_loader.list_available_robots()
        self.robot_combo.configure(values=robots)

    def _on_robot_selected(self, name):
        # Restriction: Only enable demos for "OpenBot 5-DOF"
        # We can check the string name.
        if "OpenBot" in name or "5-DOF" in name:
            self.btn_export_demos.configure(state="normal", fg_color="#475569")
            for btn in self.demo_buttons:
                btn.configure(state="normal", fg_color="#3b8ed0") # default blueish
        else:
            self.btn_export_demos.configure(state="disabled", fg_color="gray")
            for btn in self.demo_buttons:
                btn.configure(state="disabled", fg_color="gray")

        if self.on_robot_change: self.on_robot_change(name)

    def _import_config(self):
        f = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if f:
            try:
                dest = Path(self.config_loader.config_dir)/"robots"/Path(f).name
                shutil.copy2(f, str(dest))
                self.config_loader.load_robot_config(Path(f).stem)
                self._refresh_robots()
                self.robot_combo.set(Path(f).stem)
                self._on_robot_selected(Path(f).stem)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _solve_ik(self):
        if self.on_solve_ik:
            try:
                x = float(self.ik_entries['X'].get())
                y = float(self.ik_entries['Y'].get())
                z = float(self.ik_entries['Z'].get())
                self.on_solve_ik(x,y,z)
            except: pass

    def _go_home(self):
        if self.on_go_home: self.on_go_home()

    def _run_traj(self, idx):
        if self.on_run_trajectory: self.on_run_trajectory(idx)

    def _stop(self):
        if self.on_stop: self.on_stop()

    def _export_demos_json(self):
        if self.on_export_demos: self.on_export_demos()

    def _export(self, fmt):
        if self.on_export: self.on_export(fmt)
    
    def refresh_robot_list(self): self._refresh_robots()
    def set_export_status(self, text, color=""):
        self.lbl_status.configure(text=text, text_color=color if color else "gray")
