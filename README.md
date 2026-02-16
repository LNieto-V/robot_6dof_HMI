# Modular Robot HMI (Clean Architecture)

A flexible, modular Human-Machine Interface for controlling serial robotic manipulators. 
Refactored from `openbot_5dof` to support **multiple robot designs** via configuration files.

## 🌟 Features

- **Multiple Robot Support**: Define new robots in `config/robots/*.json`.
- **Clean Architecture**: Decoupled logic (Domain) from UI (Interface) and Data (Infrastructure).
- **Dynamic UI**: Control panels and 3D visualization adapt automatically to the loaded robot's Degrees of Freedom (DOF).
- **Legacy Compatibility**: Includes the original 10 demo trajectories for OpenBot 5-DOF.
- **Export**: Save trajectories to JSON or TXT for hardware deployment.

## 🚀 Getting Started

### Prerequisites

-   **Python 3.12+**
-   **Git**

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/robot-6dof-hmi.git
    cd robot-6dof-hmi
    ```

2.  **Set up the environment**:

    **Option A: Using `uv` (Recommended)**
    ```bash
    # Install uv if not installed
    pip install uv
    
    # Run directly
    uv run run.py
    ```

    **Option B: Standard Python (pip)**
    ```bash
    # Create virtual environment
    # Windows:
    python -m venv .venv
    .venv\Scripts\activate
    
    # Linux/Mac:
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Run
    python run.py
    ```

### 🍎 Mac OS Users Note
If you encounter issues with Matplotlib, you might need to use a different backend or ensure `tkinter` is correctly installed. The current implementation defaults to `TkAgg` which is standard, but some Mac setups require:
```bash
brew install python-tk
```


## 📂 Project Structure

```
robot_6dof_HMI/
├── config/                 # Configuration files
│   └── robots/             # Robot definitions (JSON)
├── src/
│   ├── core/               # Domain Logic (Kinematics, Models)
│   ├── services/           # Application Services (Controller, Simulation)
│   ├── data/               # Data Access (Config Loader, Repo)
│   ├── ui/                 # GUI (CustomTkinter Views)
│   └── main.py             # Entry Point
```

## 🏗️ Architecture

The project follows a **Clean Architecture** pattern to ensure modularity and maintainability:

-   **`src/core`** (Domain): Core models (`RobotConfig`, `Trajectory`, `KinematicsService`) and business logic.
-   **`src/services`** (Application): Application logic (`RobotController`, `SimulationService`).
-   **`src/data`** (Infrastructure): Data persistence and configuration loaders (`ConfigLoader`, `DemoLoader`).
-   **`src/ui`** (Interface): The User Interface (`MainWindow`, `SidePanel`, `Visualizer3D`).

### Key Components

-   **SidePanel**: Left panel containing Kinematics controls (FK/IK), Trajectory management, and Export features.
-   **Visualizer3D**: Center panel providing real-time 3D rendering of the robot using Matplotlib.
-   **ViewControls**: Top-right panel for Camera and Visualization settings.
-   **BottomPanel**: Bottom-right panel for System logs and status messages.

## 🚀 How to Use

### 1. Robot Configuration
Robots are defined in `config/robots/*.json`. To add a new robot:
1.  Create a new JSON file (e.g., `config/robots/my_robot.json`).
2.  Define the links (DH parameters), limits, and name.
3.  Restart the app; it will appear in the "Robot Model" dropdown.

### 2. Kinematics Controls
-   **Inverse Kinematics (IK)**: Enter Target X, Y, Z coordinates and click "Solve".
-   **Forward Kinematics (FK)**: Use the sliders to adjust individual joint angles.
-   **Get Pose**: Click **Get Pose** to copy the current end-effector position into the IK fields.

### 3. Trajectory Management
-   **Record**: Move the robot to a desired pose, then click **Record Point**. Repeat to build a path.
-   **Play**: Execute your recorded points in sequence.
-   **Import/Export**: Save your custom paths to JSON or TXT files, or load existing ones.
-   **Demos**: Use buttons **1-10** to run pre-loaded example trajectories.
-   **Export Demos**: Save the built-in demo trajectories to a JSON file for external use.

## 🛠 Adding a New Robot

1.  Create a JSON file in `config/robots/` (e.g., `my_robot.json`).
2.  Define the links (DH parameters), limits, and name.
3.  Restart the app and select your robot from the dropdown!
