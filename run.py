
import sys
import os
from pathlib import Path

# Add the project root to sys.path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

if __name__ == "__main__":
    from src.main import main
    main()
