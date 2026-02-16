import numpy as np
from typing import List, Tuple, Optional
from scipy.optimize import minimize
from .models import RobotConfig

class KinematicsService:
    def __init__(self, robot_config: RobotConfig):
        self.config = robot_config
        self.dof = len(self.config.links)
        
        # Pre-compute values for performance
        self.centers = np.array([link.center for link in self.config.links], dtype=float)
        self.limits = [link.limits for link in self.config.links]
        
    def _dh_matrix(self, theta, d, a, alpha):
        """Computes homogeneous transformation matrix using DH convention."""
        ct, st = np.cos(theta), np.sin(theta)
        ca, sa = np.cos(alpha), np.sin(alpha)
        return np.array([
            [ct, -st*ca,  st*sa, a*ct],
            [st,  ct*ca, -ct*sa, a*st],
            [0,   sa,     ca,    d],
            [0,   0,      0,     1]
        ])

    def forward_kinematics(self, units: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes forward kinematics from joint units (servo values).
        Returns:
            points: List of 3D points [base, joint1, ..., end_effector]
            T_end: 4x4 Transformation matrix of the end effector
        """
        # Ensure we check based on DOF, ignoring extra values (like gripper)
        n = min(len(units), self.dof)
        
        # Convert units to radians
        # (units - centers) * degrees_per_unit * deg_to_rad
        current_units = np.array(units[:n], dtype=float)
        rads = (current_units - self.centers[:n]) * np.radians(self.config.unit_scale_deg)
        
        points = []
        T = np.eye(4)
        points.append(T[:3, 3]) # Add base point (0,0,0) usually

        for i in range(n):
            link = self.config.links[i]
            theta_offset, d, a, alpha = link.dh
            
            # Apply joint rotation
            theta = rads[i] + theta_offset
            
            T_i = self._dh_matrix(theta, d, a, alpha)
            T = T @ T_i
            points.append(T[:3, 3])

        return np.array(points), T

    def compute_gripper_geometry(self, units: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """Computes 3D positions of gripper fingers."""
        # 1. Get End Effector Transform
        _, T_end = self.forward_kinematics(units)
        
        # 2. Calculate opening based on gripper unit value
        # Assuming gripper unit is after the arm joints
        if len(units) <= self.dof:
            gripper_val = self.config.gripper.center
        else:
            gripper_val = units[self.dof]
            
        g_min, g_max = self.config.gripper.limits
        
        # Normalize to 0-1 range (approx) then scale to physical width
        # Logic from unificado.py: opening = ((val - 250) / (550 - 250)) * 3.0
        opening = ((gripper_val - g_min) / (g_max - g_min)) * 3.0
        half_opening = opening / 2.0
        
        finger_length = 2.5
        
        # Define finger geometry in local frame
        # Left finger
        left_start = np.array([0, half_opening, 0, 1])
        left_end = np.array([0, half_opening, -finger_length, 1])
        
        # Right finger
        right_start = np.array([0, -half_opening, 0, 1])
        right_end = np.array([0, -half_opening, -finger_length, 1])
        
        # Transform to world frame
        left_start_world = (T_end @ left_start)[:3]
        left_end_world = (T_end @ left_end)[:3]
        right_start_world = (T_end @ right_start)[:3]
        right_end_world = (T_end @ right_end)[:3]
        
        left_finger = np.array([left_start_world, left_end_world])
        right_finger = np.array([right_start_world, right_end_world])
        
        return left_finger, right_finger

    def _check_self_collision(self, points, min_distance=2.0) -> bool:
        """Simple self-collision check based on point distances."""
        n = len(points)
        # Check non-adjacent links
        for i in range(n - 1):
            for j in range(i + 3, n):
                dist = np.linalg.norm(points[i] - points[j])
                if dist < min_distance:
                    return True
        return False

    def _check_ground_collision(self, points, ground_level=-3.0) -> bool:
        """Check if any point hits the ground."""
        return np.any(points[:, 2] < ground_level)

    def inverse_kinematics(self, target_pos: np.ndarray, current_units: List[float]) -> Optional[np.ndarray]:
        """
        Solves IK for target position. 
        Returns array of joint units if successful, None otherwise.
        """
        current_units_arr = np.array(current_units[:self.dof], dtype=float)
        
        # Weights for movement minimization
        # Give higher weight to base joints
        weights = np.ones(self.dof)
        if self.dof >= 1: weights[0] = 2.0
        if self.dof >= 2: weights[1] = 1.5
        
        target_pos = np.array(target_pos)

        def objective(units):
            pts, _ = self.forward_kinematics(units)
            tip = pts[-1]
            
            dist_error = np.linalg.norm(tip - target_pos)
            
            # Regularization: minimize movement from current position
            change_penalty = np.linalg.norm((units - current_units_arr) * weights) * 0.0003
            
            # Soft constraints for collision
            if dist_error < 10.0:
                if self._check_self_collision(pts, min_distance=2.0):
                    return dist_error + 100.0
                if self._check_ground_collision(pts, ground_level=-3.0):
                    return dist_error + 100.0
            
            return dist_error + change_penalty

        best_solution = None
        best_error = float('inf')
        
        # Try multiple starting positions to avoid local minima
        starting_positions = [
            current_units_arr,
            self.centers, # Home position
            current_units_arr * 0.7 + self.centers * 0.3, # Interpolated
        ]
        
        for start_pos in starting_positions:
            try:
                res = minimize(
                    objective, 
                    start_pos, 
                    bounds=self.limits, 
                    method='L-BFGS-B',
                    options={'maxiter': 300, 'ftol': 1e-6}
                )
                
                if res.fun < best_error:
                    best_error = res.fun
                    best_solution = res.x
                    
                if res.fun < 1.5: # Found good enough solution
                    break
                    
            except Exception:
                continue
        
        if best_solution is not None and best_error < 3.0:
            return best_solution
        
        return None
