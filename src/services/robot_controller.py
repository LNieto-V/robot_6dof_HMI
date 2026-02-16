import numpy as np
from typing import List, Tuple, Optional
from ..core.models import RobotConfig
from ..core.kinematics import KinematicsService
from ..data.config_loader import ConfigLoader

class RobotController:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.active_robot: Optional[RobotConfig] = None
        self.kinematics: Optional[KinematicsService] = None
        
        # State (in units)
        self.current_joints: List[float] = [] 
        
    def load_robot(self, robot_name: str):
        """Loads a robot configuration and initializes kinematics."""
        self.active_robot = self.config_loader.load_robot_config(robot_name)
        self.kinematics = KinematicsService(self.active_robot)
        # Initialize to home position
        self.current_joints = list(self.active_robot.home_position)

    def get_dof(self) -> int:
        return self.active_robot.dof if self.active_robot else 0

    def get_forward_kinematics(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns joint points and end-effector transform."""
        if not self.kinematics:
            return np.array([]), np.eye(4)
        return self.kinematics.forward_kinematics(self.current_joints)
        
    def get_gripper_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns gripper geometry points."""
        if not self.kinematics:
            return np.array([]), np.array([])
        return self.kinematics.compute_gripper_geometry(self.current_joints)

    def solve_ik(self, x: float, y: float, z: float) -> Tuple[bool, str, Optional[List[float]]]:
        """Tries to solve IK for target position."""
        if not self.kinematics:
            return False, "No robot loaded", None
            
        target_pos = np.array([x, y, z])
        solution = self.kinematics.inverse_kinematics(target_pos, self.current_joints)
        
        if solution is not None:
            # Verify solution accuracy
            pts, _ = self.kinematics.forward_kinematics(solution)
            error = np.linalg.norm(pts[-1] - target_pos)
            
            if error < 3.0:
                 return True, f"Solution found (error: {error:.2f} cm)", solution.tolist()
            else:
                 return False, f"Solution imprecise (error: {error:.2f} cm)", None
        
        return False, "Target unreachable", None

    def set_joint_value(self, joint_idx: int, value: float):
        """Sets a single joint value directly."""
        if 0 <= joint_idx < len(self.current_joints):
            self.current_joints[joint_idx] = value
            
    def get_joint_value(self, joint_idx: int) -> float:
        if 0 <= joint_idx < len(self.current_joints):
            return self.current_joints[joint_idx]
        return 0.0

    def plan_path(self, points: List[Tuple[float, float, float]]) -> Tuple[bool, List[List[float]]]:
        """
        Plans a trajectory through a sequence of cartesian points.
        Returns (success, list_of_joint_configs).
        """
        if not self.kinematics:
            return False, []
            
        solutions = []
        # Start from current position
        current_guess = np.array(self.current_joints, dtype=float)
        
        for i, (x, y, z) in enumerate(points):
            target = np.array([x, y, z])
            # Use Kinematics directly to pass custom start guess
            sol = self.kinematics.inverse_kinematics(target, current_guess)
            
            if sol is not None:
                # Verify
                pts, _ = self.kinematics.forward_kinematics(sol)
                if np.linalg.norm(pts[-1] - target) < 3.0:
                    solutions.append(sol.tolist())
                    current_guess = sol # Use this as start for next point
                else:
                    return False, [] # imprecise
            else:
                return False, [] # unreachable
                
        # Return to home at end? unificado.py did matches matching waypoints.
        # It added home at the VERY end.
        solutions.append(list(self.active_robot.home_position))
        
        return True, solutions

    def is_ready(self) -> bool:
        return self.active_robot is not None
