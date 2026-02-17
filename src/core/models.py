from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

@dataclass
class RobotLink:
    name: str
    id: int
    # DH Parameters: [theta_offset, d, a, alpha]
    dh: Tuple[float, float, float, float] 
    # Servo Limits: [min, max]
    limits: Tuple[int, int]  
    center: int
    axis: str = "z"

@dataclass
class RobotGripper:
    name: str
    id: int
    limits: Tuple[int, int]
    center: int

@dataclass
class RobotConfig:
    name: str
    version: str
    dof: int
    unit_scale_deg: float
    links: List[RobotLink]
    gripper: Optional[RobotGripper]
    home_position: List[int]

@dataclass
class Waypoint:
    positions: List[int]
    index: int
    dt: float = 1.0 # time from previous point, placeholder

@dataclass
class Trajectory:
    id: int
    name: str
    description: str
    waypoints: List[Waypoint]
