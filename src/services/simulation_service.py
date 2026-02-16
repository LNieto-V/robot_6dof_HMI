import numpy as np
from typing import List, Optional, Callable
import time
import threading
from .robot_controller import RobotController

class SimulationService:
    def __init__(self, robot_controller: RobotController):
        self.controller = robot_controller
        self.running = False
        self.current_trajectory: Optional[List[List[float]]] = None
        self.trajectory_index = 0
        self.target_joints: Optional[List[float]] = None
        
        # Callbacks
        self.on_status_change: Optional[Callable[[str, str], None]] = None
        self.on_completion: Optional[Callable[[], None]] = None

    def execute_trajectory(self, waypoints: List[List[float]]):
        """Starts executing a list of joint configurations."""
        if not waypoints:
            return
            
        self.current_trajectory = waypoints
        self.trajectory_index = 0
        self.target_joints = waypoints[0]
        self.running = True
        
        if self.on_status_change:
            self.on_status_change(f"Executing waypoint 1/{len(waypoints)}", "cyan")

    def move_to(self, target_joints: List[float]):
        """Moves to a single target configuration."""
        self.execute_trajectory([target_joints])

    def stop(self):
        """Stops current movement."""
        self.running = False
        self.current_trajectory = None
        if self.on_status_change:
            self.on_status_change("Stopped", "red")

    def update(self):
        """
        Updates robot state towards target. 
        Should be called periodically (e.g. 30 FPS).
        """
        if not self.running or self.target_joints is None:
            return

        current = np.array(self.controller.current_joints)
        target = np.array(self.target_joints)
        
        # Handle different array sizes (e.g. if config changed mid-flight, though unlikely)
        min_len = min(len(current), len(target))
        current = current[:min_len]
        target = target[:min_len]
        
        diff = target - current
        dist = np.linalg.norm(diff)
        
        # Interpolation logic
        if dist > 2.0:
            step = diff * 0.15
        elif dist > 0.1:
            step = diff * 0.5
        else:
            step = diff  # Snap to target
            self.controller.current_joints[:min_len] = (current + step).tolist()
            self._advance_waypoint()
            return

        self.controller.current_joints[:min_len] = (current + step).tolist()

    def _advance_waypoint(self):
        self.trajectory_index += 1
        
        if self.current_trajectory and self.trajectory_index < len(self.current_trajectory):
            self.target_joints = self.current_trajectory[self.trajectory_index]
            if self.on_status_change:
                self.on_status_change(f"Executing waypoint {self.trajectory_index + 1}/{len(self.current_trajectory)}", "cyan")
        else:
            self.running = False
            # NOTE: Do NOT clear current_trajectory here — keep it for export
            if self.on_status_change:
                self.on_status_change("Trajectory complete", "green")
            if self.on_completion:
                self.on_completion()

