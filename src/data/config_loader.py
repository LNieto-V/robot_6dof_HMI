import json
from pathlib import Path
from typing import List, Optional
from ..core.models import RobotConfig, RobotLink, RobotGripper

class ConfigLoader:
    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)

    def load_robot_config(self, robot_filename: str) -> RobotConfig:
        """Loads a robot configuration from a JSON file."""
        if not robot_filename.endswith('.json'):
            robot_filename += '.json'
            
        path = self.config_dir / 'robots' / robot_filename
        
        if not path.exists():
            raise FileNotFoundError(f"Robot config not found: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse Links
        links = []
        for l in data.get('links', []):
            link = RobotLink(
                name=l['name'],
                id=l['id'],
                dh=tuple(l['dh']),
                limits=tuple(l['limits']),
                center=l['center'],
                axis=l.get('axis', 'z')
            )
            links.append(link)
            
        # Parse Gripper
        if 'gripper' in data:
            g_data = data['gripper']
            gripper = RobotGripper(
                name=g_data['name'],
                id=g_data['id'],
                limits=tuple(g_data['limits']),
                center=g_data['center']
            )
        else:
            # Default dummy gripper if missing
            gripper = RobotGripper("None", 0, (0,0), 0)
        
        return RobotConfig(
            name=data['name'],
            version=data.get('version', '1.0'),
            dof=data['dof'],
            unit_scale_deg=data.get('unit_scale_deg', 0.293),
            links=links,
            gripper=gripper,
            home_position=data.get('home_position', [l.center for l in links])
        )

    def list_available_robots(self) -> List[str]:
        """Lists all available robot configuration files."""
        robots_dir = self.config_dir / 'robots'
        if not robots_dir.exists():
            return []
        return [f.stem for f in robots_dir.glob('*.json')]
