import tkinter as tk
from tkinter import ttk
import sys
import os

MAIN_DIR = os.path.dirname(os.path.abspath(__file__))  # combined_ui
ROOT_DIR = os.path.dirname(MAIN_DIR)  # TRACK_AND_TRAIN

# Get absolute paths
MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
TRACK_MODEL_DIR = os.path.join(MAIN_DIR, "Track_Model")
TRAIN_MODEL_DIR = os.path.join(MAIN_DIR, "Train_Model")

# Add directories to path for imports BEFORE importing
sys.path.insert(0, TRACK_MODEL_DIR)
sys.path.insert(0, TRAIN_MODEL_DIR)

# Now import after paths are set
TrackModelUI = None
TrainModelUI = None


def load_modules():
    global TrackModelUI, TrainModelUI
    from track_model_UI import TrackModelUI as _TrackModelUI
    from train_model_ui import TrainModelUI as _TrainModelUI

    TrackModelUI = _TrackModelUI
    TrainModelUI = _TrainModelUI


load_modules()


class MainUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train & Track System")
        self.geometry("1800x1000")
        self.configure(bg="white")

        # Track visibility states
        self.track_visible = False
        self.train_visible = False

        # Create button bar at top
        self.create_button_bar()

        # Create main content area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Create frames for each panel
        self.track_container = ttk.Frame(self.content_frame)
        self.train_container = ttk.Frame(self.content_frame)

        # Initialize the UI components
        self.track_ui = TrackModelUI(self.track_container)
        self.train_ui = TrainModelUI(self.train_container)

    def create_button_bar(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=5, pady=5)

        self.btn_track = ttk.Button(
            button_frame, text="Show Track", command=self.toggle_track
        )
        self.btn_track.pack(side="left", padx=5)

        self.btn_train = ttk.Button(
            button_frame, text="Show Train Model", command=self.toggle_train
        )
        self.btn_train.pack(side="left", padx=5)

    def toggle_track(self):
        if self.track_visible:
            self.track_container.grid_forget()
            self.btn_track.config(text="Show Track")
            self.track_visible = False
        else:
            self.track_container.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
            self.btn_track.config(text="Hide Track")
            self.track_visible = True
        self.update_column_weights()

    def toggle_train(self):
        if self.train_visible:
            self.train_container.grid_forget()
            self.btn_train.config(text="Show Train Model")
            self.train_visible = False
        else:
            self.train_container.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
            self.train_container.config(width=680)
            self.train_container.grid_propagate(False)
            self.btn_train.config(text="Hide Train Model")
            self.train_visible = True
        self.update_column_weights()

    def update_column_weights(self):
        # Reset all weights
        for i in range(2):
            self.content_frame.grid_columnconfigure(i, weight=0)

        # Set weights for visible columns
        if self.track_visible:
            self.content_frame.grid_columnconfigure(0, weight=5)
        if self.train_visible:
            self.content_frame.grid_columnconfigure(1, weight=0)


if __name__ == "__main__":
    app = MainUI()
    app.mainloop()
