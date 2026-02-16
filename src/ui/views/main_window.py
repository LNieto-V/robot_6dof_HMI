# ... existing code ...
import customtkinter as ctk
import threading
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox
import json

from ...services.robot_controller import RobotController
from ...services.simulation_service import SimulationService
from ...data.config_loader import ConfigLoader
from ...data.demo_loader import DemoLoader
from .side_panel import SidePanel
from .visualizer_3d import Visualizer3D
from .view_controls import ViewControls
from .bottom_panel import BottomPanel

class MainWindow(ctk.CTk):
    
    def __init__(self, config_dir: str):
        super().__init__()

        self.title("🤖 Modular Robot HMI v4.0")
        self.geometry("1920x1080")
        # self.resizable(False, False)

        # ── Core ──
        self.config_dir = Path(config_dir)
        self.config_loader = ConfigLoader(config_dir)
        self.controller = RobotController(self.config_loader)
        self.simulation = SimulationService(self.controller)
        self.simulation.on_status_change = self._on_sim_status
        self.simulation.on_completion = self._on_sim_complete

        # ── Grid Layout ──
        # Adjusted for Log relocation to right column
        self.grid_columnconfigure(0, weight=0, minsize=400) # Side Panel
        self.grid_columnconfigure(1, weight=1)              # Visualizer
        self.grid_columnconfigure(2, weight=0, minsize=400) # Controls + Logs (Wider)
        
        self.grid_rowconfigure(0, weight=0)                 # Top Right (Controls) - Auto height
        self.grid_rowconfigure(1, weight=1)                 # Bottom Right (Logs) - Fills rest

        # 1. SIDE PANEL
        self.side_panel = SidePanel(self, self.controller, self.config_loader)
        self.side_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        # Wire Side Panel Events
        self.side_panel.on_robot_change = self._load_robot
        self.side_panel.on_solve_ik = self._solve_ik
        self.side_panel.on_go_home = self._go_home
        self.side_panel.on_run_trajectory = self._run_traj
        self.side_panel.on_joint_change = self._on_joint_change
        self.side_panel.on_stop = self._stop
        self.side_panel.on_export = self._export # Wired to export current playback
        self.side_panel.on_get_fk = self._get_current_pose
        self.side_panel.on_play_recording = self._play_recording_list # New
        self.side_panel.on_import = self._import_traj_file # New
        self.side_panel.on_export_demos = self._export_demos # New

        # 2. CENTRAL VISUALIZER
        self.viz_container = ctk.CTkFrame(self, fg_color=None)
        self.viz_container.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=10)
        self.viz_container.grid_columnconfigure(0, weight=1)
        self.viz_container.grid_rowconfigure(0, weight=1)

        self.visualizer = Visualizer3D(self.viz_container, corner_radius=0)
        self.visualizer.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # 3. RIGHT CONTROLS (Top Right)
        self.view_controls = ViewControls(self)
        self.view_controls.grid(row=0, column=2, sticky="nsew", padx=10, pady=(10, 5))
        
        self.view_controls.on_scale_change = lambda v: self.visualizer.set_scale(float(v))
        self.view_controls.on_perspective_change = lambda e, a: self.visualizer.set_perspective(e, a)
        self.view_controls.on_trajectory_toggle = self.visualizer.set_trajectory_visible
        self.view_controls.on_reset_view = self.visualizer.reset_view

        # 4. BOTTOM PANEL (Logs - Moved to Bottom Right)
        self.bottom_panel = BottomPanel(self)
        self.bottom_panel.grid(row=1, column=2, sticky="nsew", padx=10, pady=(0, 10))

        # ── Startup ──
        self.side_panel.refresh_robot_list()
        robots = self.config_loader.list_available_robots()
        if "openbot_5dof" in robots:
            self._load_robot("openbot_5dof")
            # Move to Home on startup
            self.after(100, self._go_home)
        
        self._update_loop()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Logic ──

    def _log(self, msg):
        self.bottom_panel.log(msg)

    def _load_robot(self, name):
        try:
            self.controller.load_robot(name)
            self.side_panel.build_sliders(self.controller.active_robot)
            self.simulation.stop()
            rname = self.controller.active_robot.name
            self.visualizer.set_title(rname)
            self._log(f"Loaded: {rname}")
            self.view_controls.set_status("Ready", "green")
            self._update_visualization()
            self._get_current_pose()
        except Exception as e:
            self._log(f"Error: {e}")

    def _on_joint_change(self, idx, val):
        self.controller.set_joint_value(idx, val)
        if not self.simulation.running:
            self._update_visualization()

    def _solve_ik(self, x, y, z):
        self._log(f"IK Search: {x}, {y}, {z}")
        self.view_controls.set_status("Solving...", "yellow")
        threading.Thread(target=self._ik_thread, args=(x,y,z), daemon=True).start()

    def _ik_thread(self, x, y, z):
        ok, msg, j = self.controller.solve_ik(x, y, z)
        if ok:
            self.simulation.move_to(j)
            self._log("IK Solved")
            self.view_controls.set_status("Success", "green")
            self.side_panel.update_joints(j)
        else:
            self._log("IK Failed")
            self.view_controls.set_status("Failed", "red")

    def _get_current_pose(self):
        if not self.controller.is_ready(): return
        pts, _ = self.controller.get_forward_kinematics()
        if pts is not None and len(pts) > 0:
            end_effector = pts[-1]
            x, y, z = end_effector
            self.side_panel.set_ik_values(x, y, z)
            self._log(f"📍 Retrieved Pose: X={x:.1f}, Y={y:.1f}, Z={z:.1f}")

    def _run_traj(self, idx):
        if not self.controller.is_ready(): return
        # Use DemoLoader instead of LegacyTrajectoryFactory
        loader = DemoLoader(self.config_dir)
        defn = loader.load_demos().get(idx)
        
        if not defn: return
        name, pts, _ = defn
        self._log(f"Traj: {name} ({len(pts)} pts)")
        self.view_controls.set_status("Planning...", "yellow")
        threading.Thread(target=self._traj_thread, args=(name, pts), daemon=True).start()

    def _traj_thread(self, name, points):
        ok, sol = self.controller.plan_path(points)
        if ok:
            self.visualizer.show_trajectory_waypoints(points)
            self.simulation.execute_trajectory(sol)
            self._log("Executing...")
            self.view_controls.set_status("Running", "cyan")
        else:
            self._log("Planning Failed")
            self.view_controls.set_status("Error", "red")

    def _play_recording_list(self, waypoints):
        """Plays recorded joint configurations directly, enforcing Home start/end."""
        if not waypoints: return
        
        home = self.controller.active_robot.home_position
        # Prepend Home, Append Home
        full_trajectory = [home] + waypoints + [home]
        
        self._log(f"Playing recording ({len(waypoints)} pts + Home)...")
        # Direct execution since they are already joint configs
        self.simulation.execute_trajectory(full_trajectory)
        self.view_controls.set_status("Playing Rec", "cyan")

    def _import_traj_file(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("TXT", "*.txt")])
        if not f: return
        
        try:
            path = Path(f)
            waypoints = []
            if path.suffix == ".json":
                with open(path, 'r') as fh:
                    data = json.load(fh)
                    # Support both list of lists and dict format
                    if isinstance(data, list): waypoints = data
                    elif "waypoints" in data:
                        # Check if waypoints are dicts or lists
                        if data["waypoints"] and isinstance(data["waypoints"][0], dict):
                             waypoints = [wp["positions"] for wp in data["waypoints"]]
                        else:
                             waypoints = data["waypoints"]
            else:
                with open(path, 'r') as fh:
                    for line in fh:
                        if line.startswith("#") or not line.strip(): continue
                        waypoints.append([float(x) for x in line.strip().split(',')])
            
            if waypoints:
                self._log(f"Imported {len(waypoints)} pts from {path.name}")
                self.simulation.execute_trajectory(waypoints)
                self.view_controls.set_status("Playing Import", "cyan")
            else:
                self._log("Import failed: No valid data")
        except Exception as e:
            self._log(f"Import Error: {e}")

    def _go_home(self):
        if self.controller.is_ready():
            self.simulation.move_to(self.controller.active_robot.home_position)
            self._log("Go Home")
            self._get_current_pose()

    def _stop(self):
        self.simulation.stop()
        self._log("Stopped")
        self.view_controls.set_status("Stopped", "red")

    def _export(self, fmt):
        # Prefer recorded waypoints if available?
        # Or current executed trajectory.
        # Let's export what was just played/recorded.
        data = self.simulation.current_trajectory
        if not data and self.side_panel.recorded_waypoints:
             data = self.side_panel.recorded_waypoints
             
        if not data:
            self._log("No data to export")
            return 
            
        ext = f".{fmt}"
        f = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(f"{fmt.upper()} File", f"*{ext}")])
        if f:
            try:
                with open(f, 'w') as fh:
                    if fmt == "json":
                        json.dump({"waypoints": data}, fh, indent=2)
                    else:
                        for row in data:
                            fh.write(",".join(map(str, map(int, row))) + "\n")
                self._log(f"Exported: {Path(f).name}")
            except Exception as e:
                self._log(f"Export Error: {e}")

    def _export_demos(self):
        """Exports the built-in demos.json to a user location."""
        src = self.config_dir / "demos.json"
        if not src.exists():
            self._log("Error: config/demos.json not found")
            return
            
        f = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="demos_export.json",
            filetypes=[("JSON Config", "*.json")]
        )
        if f:
            try:
                import shutil
                shutil.copy2(src, f)
                self._log(f"Exported Demos to {Path(f).name}")
            except Exception as e:
                self._log(f"Export Error: {e}")

    def _on_sim_status(self, msg, color):
        self.view_controls.set_status(msg, color)

    def _on_sim_complete(self):
        self._log("Trajectory Done")
        self.view_controls.set_status("Ready", "green")
        self.visualizer.show_trajectory_waypoints(None)
        self._get_current_pose()
        if self.controller.is_ready():
            self.side_panel.update_joints(self.controller.current_joints)

    def _update_loop(self):
        if self.simulation.running:
            self.simulation.update()
            if self.controller.is_ready():
                 self.side_panel.update_joints(self.controller.current_joints)
        self._update_visualization()
        self.after(30, self._update_loop)

    def _update_visualization(self):
        if not self.controller.is_ready(): return
        pts, _ = self.controller.get_forward_kinematics()
        grp = self.controller.get_gripper_geometry()
        col = False
        if self.controller.kinematics:
            col = (self.controller.kinematics._check_self_collision(pts, 1.5) or 
                   self.controller.kinematics._check_ground_collision(pts, -3.0))
        self.visualizer.update_robot(pts, grp, col)

    def _on_close(self):
        # Move to Home on exit
        try:
            self._go_home()
        except: pass
        
        self.simulation.stop()
        self.destroy()
