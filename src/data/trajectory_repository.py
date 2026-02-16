import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from ..core.models import Trajectory, Waypoint

class TrajectoryRepository:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, trajectory: Trajectory, filename: Optional[str] = None) -> str:
        """Saves trajectory to JSON file."""
        if not filename:
            filename = f"trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        path = self.data_dir / filename
        
        data = {
            "metadata": {
                "id": trajectory.id,
                "name": trajectory.name,
                "description": trajectory.description,
                "export_time": datetime.now().isoformat(),
                "waypoints_count": len(trajectory.waypoints)
            },
            "waypoints": [
                {
                    "index": wp.index,
                    "positions": wp.positions,
                    "dt": wp.dt
                }
                for wp in trajectory.waypoints
            ]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        return str(path)

    def load_json(self, path: str) -> Trajectory:
        """Loads trajectory from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        metadata = data.get('metadata', {})
        waypoints_data = data.get('waypoints', [])
        
        waypoints = [
            Waypoint(
                positions=wp['positions'],
                index=wp['index'],
                dt=wp.get('dt', 1.0)
            )
            for wp in waypoints_data
        ]
        
        return Trajectory(
            id=metadata.get('id', 0),
            name=metadata.get('name', 'Imported'),
            description=metadata.get('description', ''),
            waypoints=waypoints
        )

    def export_txt(self, trajectory: Trajectory, filename: Optional[str] = None) -> str:
        """Exports trajectory to simple TXT format for hardware."""
        if not filename:
            filename = f"trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
        path = self.data_dir / filename
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# Trajectory: {trajectory.name}\n")
            f.write(f"# Export Time: {datetime.now().isoformat()}\n")
            f.write(f"# Waypoints: {len(trajectory.waypoints)}\n")
            f.write("# Format: Joint1,Joint2,...,JointN\n\n")
            
            for wp in trajectory.waypoints:
                # Convert list of ints to comma-separated string
                line = ",".join(map(str, wp.positions))
                f.write(f"{line}\n")
                
        return str(path)
