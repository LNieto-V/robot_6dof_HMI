
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

class DemoLoader:
    """Loads demo trajectories from a JSON configuration file."""
    
    def __init__(self, config_dir: Path):
        self.config_path = config_dir / "demos.json"
        
    def load_demos(self) -> Dict[int, Tuple[str, List[List[float]], str]]:
        """
        Returns a dictionary of demo definitions.
        Format: {id: (name, points, description)}
        """
        if not self.config_path.exists():
            return {}
            
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                
            demos = {}
            for item in data.get("demos", []):
                # Convert points to list of lists (if not already)
                # JSON stores as [[x,y,z], ...] which is compatible
                demos[item["id"]] = (
                    item["name"],
                    item["points"],
                    item["description"]
                )
            return demos
        except Exception as e:
            print(f"Error loading demos: {e}")
            return {}
