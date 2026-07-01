import sys
import math
import argparse
import traceback
import numpy as np
from scipy.optimize import minimize
from typing import List, Tuple, Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial is not installed. Serial communication will be disabled.")
    print("Install it via: pip install pyserial")

# ==========================================
# ROBOT CONFIGURATION (Embedded Data)
# ==========================================
ROBOT_CONFIG = {
    "name": "OpenBot 5-DOF",
    "version": "1.0",
    "dof": 5,
    "unit_scale_deg": 0.293,
    "links": [
        {"name": "Base",     "id": 1, "dh": [0,           14.35, 0,    1.570796327], "limits": [0,   1023], "center": 512},
        {"name": "Shoulder", "id": 2, "dh": [1.570796327, 0,     11.0, 0          ], "limits": [182, 925],  "center": 512},
        {"name": "Elbow",    "id": 3, "dh": [0,           0,     9.0,  0          ], "limits": [50,  945],  "center": 512},
        {"name": "WristRot", "id": 4, "dh": [0,           0,     0,    1.570796327], "limits": [0,   1023], "center": 512},
        {"name": "WristPit", "id": 5, "dh": [0,           2.9,   7.3,  0          ], "limits": [386, 959],  "center": 512}
    ],
    "gripper": {
        "name": "Gripper", "id": 6, "limits": [250, 550], "center": 400
    },
    "home_position": [512, 512, 512, 512, 512, 400]
}

# ==========================================
# KINEMATICS ENGINE
# ==========================================
class KinematicsEngine:
    def __init__(self, config: dict):
        self.config = config
        self.dof = config["dof"]
        self.scale_deg = config["unit_scale_deg"]
        
        # Pre-compute
        self.centers = np.array([link["center"] for link in self.config["links"]], dtype=float)
        self.limits = [tuple(link["limits"]) for link in self.config["links"]]
        self.dh_params = [link["dh"] for link in self.config["links"]]

    def _dh_matrix(self, theta, d, a, alpha):
        ct, st = np.cos(theta), np.sin(theta)
        ca, sa = np.cos(alpha), np.sin(alpha)
        return np.array([
            [ct, -st*ca,  st*sa, a*ct],
            [st,  ct*ca, -ct*sa, a*st],
            [0,   sa,     ca,    d],
            [0,   0,      0,     1]
        ])

    def forward_kinematics(self, units: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        n = min(len(units), self.dof)
        current_units = np.array(units[:n], dtype=float)
        
        # Convert units (0-1023) to radians
        rads = (current_units - self.centers[:n]) * np.radians(self.scale_deg)
        
        points = []
        T = np.eye(4)
        points.append(T[:3, 3])

        for i in range(n):
            theta_offset, d, a, alpha = self.dh_params[i]
            theta = rads[i] + theta_offset
            T_i = self._dh_matrix(theta, d, a, alpha)
            T = T @ T_i
            points.append(T[:3, 3])

        return np.array(points), T

    def inverse_kinematics(self, target_pos: List[float], current_units: List[float]) -> Optional[np.ndarray]:
        current_units_arr = np.array(current_units[:self.dof], dtype=float)
        
        weights = np.ones(self.dof)
        if self.dof >= 1: weights[0] = 2.0
        if self.dof >= 2: weights[1] = 1.5
        
        target_pos = np.array(target_pos)

        def objective(units):
            pts, _ = self.forward_kinematics(units)
            tip = pts[-1]
            dist_error = np.linalg.norm(tip - target_pos)
            
            # Minimize change from current position
            change_penalty = np.linalg.norm((units - current_units_arr) * weights) * 0.0003
            
            # Simple ground collision check (soft constraint)
            if np.any(pts[:, 2] < -3.0):
                return dist_error + 100.0
                
            return dist_error + change_penalty

        best_solution = None
        best_error = float('inf')
        
        starting_positions = [
            current_units_arr,
            self.centers,
            current_units_arr * 0.7 + self.centers * 0.3
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
                    
                if res.fun < 1.0: # Close enough
                    break
            except Exception:
                pass
                
        if best_solution is not None and best_error < 3.0:
            return np.round(best_solution).astype(int)
        return None


# ==========================================
# SERIAL CONTROLLER
# ==========================================
class RobotController:
    def __init__(self):
        self.ser = None
        self.connected = False

    def connect(self, port: str, baudrate: int = 1000000) -> bool:
        if not SERIAL_AVAILABLE:
            print("pyserial not available.")
            return False
            
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.connected = True
            print(f"Connected to {port} at {baudrate} baud.")
            return True
        except Exception as e:
            print(f"Failed to connect to {port}: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            print("Disconnected.")

    def send_positions(self, positions: List[int]):
        """
        Sends the joint positions to OpenCM.
        Modify this protocol format depending on what your OpenCM sketch expects.
        Example format: "id1,pos1;id2,pos2;...\n" mapping [1:pos[0], 2:pos[1], ...]
        """
        if not self.connected:
            print("Warning: Not connected to any serial port. Command ignored.")
            return
            
        try:
            # Simple delimited string protocol for OpenCM parsing:
            # Example: "P 1:512 2:512 3:512 4:512 5:512"
            parts = []
            for i, pos in enumerate(positions):
                parts.append(f"{i+1}:{int(pos)}")
            command = "P " + " ".join(parts) + "\\n"
            
            self.ser.write(command.encode('utf-8'))
            print(f"> Sent to Serial: {command.strip()}")
            
            # Optional: read response
            # line = self.ser.readline().decode('utf-8').strip()
            # if line: print(f"< Receive: {line}")
            
        except Exception as e:
            print(f"Error sending command: {e}")


# ==========================================
# CLI INTERFACE
# ==========================================
def main_loop():
    print("="*50)
    print(f" OpenBot 5-DOF Terminal Controller ")
    print("="*50)
    print("Commands:")
    print("  connect <port>    --> Connect to OpenCM/Dynamixel (e.g. connect /dev/ttyUSB0)")
    print("  fk <j1> ... <j5>  --> Forward Kinematics (e.g. fk 512 512 512 512 512)")
    print("  ik <x> <y> <z>    --> Inverse Kinematics (e.g. ik 10 0 15)")
    print("  home              --> Move to home position")
    print("  exit              --> Close application")
    print("="*50)

    kin = KinematicsEngine(ROBOT_CONFIG)
    robot = RobotController()
    
    current_units = ROBOT_CONFIG["home_position"][:]

    while True:
        try:
            cmd_input = input("\n[OpenBot] > ").strip().split()
            if not cmd_input:
                continue
                
            cmd = cmd_input[0].lower()
            args = cmd_input[1:]

            if cmd == "exit":
                robot.disconnect()
                print("Exiting...")
                break

            elif cmd == "connect":
                if len(args) < 1:
                    print("Usage: connect <port> [baudrate]")
                    continue
                port = args[0]
                baud = int(args[1]) if len(args) > 1 else 1000000
                robot.connect(port, baud)

            elif cmd == "disconnect":
                robot.disconnect()

            elif cmd == "home":
                print("Moving to Home...")
                current_units = ROBOT_CONFIG["home_position"][:]
                pts, T = kin.forward_kinematics(current_units)
                end_pos = T[:3, 3]
                print(f"Home Position (X,Y,Z): {end_pos[0]:.2f}, {end_pos[1]:.2f}, {end_pos[2]:.2f}")
                robot.send_positions(current_units)

            elif cmd == "fk":
                if len(args) < kin.dof:
                    print(f"Usage: fk {' '.join([f'<j{i+1}>' for i in range(kin.dof)])}")
                    continue
                try:
                    target_units = [int(a) for a in args[:kin.dof]]
                    pts, T = kin.forward_kinematics(target_units)
                    end_pos = T[:3, 3]
                    print(f"FK Result: -> End Effector Position (X,Y,Z): {end_pos[0]:.2f}, {end_pos[1]:.2f}, {end_pos[2]:.2f}")
                    
                    # Also append gripper if it exists (keep current state)
                    if len(current_units) > kin.dof:
                        target_units.append(current_units[-1])
                        
                    current_units = target_units
                    robot.send_positions(current_units)
                except ValueError:
                    print("Error: Joint values must be integers.")

            elif cmd == "ik":
                if len(args) < 3:
                    print("Usage: ik <x> <y> <z>")
                    continue
                try:
                    target_pos = [float(args[0]), float(args[1]), float(args[2])]
                    print(f"Solving IK for X={target_pos[0]:.2f}, Y={target_pos[1]:.2f}, Z={target_pos[2]:.2f}...")
                    
                    new_units = kin.inverse_kinematics(target_pos, current_units)
                    if new_units is not None:
                        print(f"IK Solved! Joint Units: {new_units.tolist()}")
                        
                        target_units = new_units.tolist()
                        # Also append gripper if it exists
                        if len(current_units) > kin.dof:
                            target_units.append(current_units[-1])
                            
                        current_units = target_units
                        robot.send_positions(current_units)
                    else:
                        print("IK Failed to find a valid solution within limits!")
                except ValueError:
                    print("Error: Coordinates must be numbers.")
                    
            else:
                print(f"Unknown command: {cmd}")

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to close.")
        except Exception as e:
            print(f"Error executing command: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main_loop()
