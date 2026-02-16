import sys
import os
import customtkinter as ctk
from pathlib import Path

def main():
    # Determine project root
    root_dir = Path(__file__).resolve().parent.parent
    config_dir = root_dir / 'config'
    theme_path = config_dir / 'roshi_theme.json'
    
    print(f"Starting Robot HMI...")
    print(f"Root: {root_dir}")
    print(f"Config: {config_dir}")
    
    # Ensure src is in python path
    src_path = str(root_dir / 'src')
    if src_path not in sys.path:
        sys.path.append(src_path)
        
    # Import after path setup
    from src.ui.views.main_window import MainWindow

    # Apply theme
    ctk.set_appearance_mode("dark")
    if theme_path.exists():
        ctk.set_default_color_theme(str(theme_path))
        print(f"Theme: {theme_path.name}")
    else:
        ctk.set_default_color_theme("blue")
    
    app = MainWindow(str(config_dir))
    app.mainloop()

if __name__ == "__main__":
    main()
