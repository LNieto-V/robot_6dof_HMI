import customtkinter as ctk
from datetime import datetime

class BottomPanel(ctk.CTkFrame):
    """
    Bottom panel for system logs, spanning the full width.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", border_width=0, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_ui()

    def _build_ui(self):
        # Container with a title
        card = ctk.CTkFrame(self, fg_color=None, border_width=0)
        card.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        header = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
        header.pack(fill="x", padx=10, pady=(5, 5))

        ctk.CTkLabel(header, text="System Log / Console", 
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        
        ctk.CTkButton(header, text="Clear", width=60, height=20, border_width=0,
                      fg_color="#555", hover_color="#333",
                      command=self.clear).pack(side="right")

        self.console = ctk.CTkTextbox(card, font=("Courier", 13), border_width=0, height=120)
        self.console.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.insert("end", f"[{ts}] {message}\n")
        self.console.see("end")

    def clear(self):
        self.console.delete("1.0", "end")
