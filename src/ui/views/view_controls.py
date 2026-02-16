import customtkinter as ctk
from datetime import datetime

class ViewControls(ctk.CTkFrame):
    """
    Right panel with Card layout, NO BORDERS.
    Controls camera, options, and logs.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", border_width=0, **kwargs)
        
        self.on_scale_change = None
        self.on_perspective_change = None
        self.on_trajectory_toggle = None
        self.on_reset_view = None
        
        self._build_ui()

    def _build_ui(self):
        # 1. Camera Card
        self._build_camera_card()
        
        # 2. Options Card
        self._build_options_card()

    def _build_camera_card(self):
        card = ctk.CTkFrame(self, fg_color=None, border_width=0)
        card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(card, text="Camera Settings", 
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        # Scale
        f1 = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
        f1.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(f1, text="Zoom", font=("Arial", 11)).pack(anchor="w")
        self.scale_slider = ctk.CTkSlider(f1, from_=0.5, to=2.0, number_of_steps=50,
                                          command=self._on_scale, border_width=0)
        self.scale_slider.set(1.0)
        self.scale_slider.pack(fill="x", pady=(2, 0))

        # Perspective
        f2 = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
        f2.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(f2, text="Elevation / Azimuth", font=("Arial", 11)).pack(anchor="w")
        
        self.elev_slider = ctk.CTkSlider(f2, from_=-10, to=90, number_of_steps=50,
                                         command=self._on_perspective, border_width=0)
        self.elev_slider.set(20)
        self.elev_slider.pack(fill="x", pady=(2, 6))
        
        self.azim_slider = ctk.CTkSlider(f2, from_=-180, to=180, number_of_steps=90,
                                         command=self._on_perspective, border_width=0)
        self.azim_slider.set(-60)
        self.azim_slider.pack(fill="x")

        # Reset button
        ctk.CTkButton(card, text="Reset View", height=28, border_width=0,
                      command=self._on_reset).pack(fill="x", padx=10, pady=(5, 10))

    def _build_options_card(self):
        card = ctk.CTkFrame(self, fg_color=None, border_width=0)
        card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(card, text="Visualization", 
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.show_traj_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(card, text="Show Planned Path", variable=self.show_traj_var,
                        command=self._on_traj_toggle, border_width=1).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Status
        self.status_bar = ctk.CTkLabel(card, text="Ready", text_color="#2ecc71",
                                       font=("Courier", 12, "bold"), anchor="w")
        self.status_bar.pack(fill="x", padx=10, pady=(0, 10))

    # ── Logic ──

    def _on_scale(self, val):
        if self.on_scale_change: self.on_scale_change(val)

    def _on_perspective(self, val=None):
        if self.on_perspective_change:
            self.on_perspective_change(self.elev_slider.get(), self.azim_slider.get())

    def _on_traj_toggle(self):
        if self.on_trajectory_toggle:
            self.on_trajectory_toggle(self.show_traj_var.get())

    def _on_reset(self):
        self.scale_slider.set(1.0)
        self.elev_slider.set(20)
        self.azim_slider.set(-60)
        if self.on_reset_view: self.on_reset_view()

    # Public API
    def set_status(self, message: str, color: str = ""):
        self.status_bar.configure(text=f"STATUS: {message.upper()}",
                                   text_color=color if color else "#f8fafc")

    def get_view_params(self):
        return {
            "scale": self.scale_slider.get(),
            "elev": self.elev_slider.get(),
            "azim": self.azim_slider.get(),
            "show_traj": self.show_traj_var.get()
        }
