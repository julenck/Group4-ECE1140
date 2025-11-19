import tkinter as tk
from tkinter import ttk
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the UI classes
from Track_Model.track_model_UI import TrackModelUI
from Train_Model.train_model_ui import TrainModelUI


class MainUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train & Track System")
        self.geometry("1800x1000")
        self.configure(bg="white")

        # Track which frames are visible
        self.track_left_visible = False
        self.track_right_visible = False
        self.train_visible = False

        # Create button bar at top
        self.create_button_bar()

        # Create main content area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(2, weight=1)

        # Create the embedded frames (but don't show them yet)
        self.create_track_left_frame()
        self.create_track_right_frame()
        self.create_train_frame()

    def create_button_bar(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=5, pady=5)

        # Track Model buttons
        self.btn_track_left = ttk.Button(
            button_frame, text="Show Track Left", command=self.toggle_track_left
        )
        self.btn_track_left.pack(side="left", padx=5)

        self.btn_track_right = ttk.Button(
            button_frame, text="Show Track Right", command=self.toggle_track_right
        )
        self.btn_track_right.pack(side="left", padx=5)

        # Train Model button
        self.btn_train = ttk.Button(
            button_frame, text="Show Train Model", command=self.toggle_train
        )
        self.btn_train.pack(side="left", padx=5)

    def create_track_left_frame(self):
        """Create the track visualizer frame (left panel from TrackModelUI)"""
        self.track_left_frame = ttk.LabelFrame(
            self.content_frame, text="Track Layout Interactive Diagram"
        )
        # Will be gridded when shown

    def create_track_right_frame(self):
        """Create the track controls/info frame (right panel from TrackModelUI)"""
        self.track_right_frame = ttk.LabelFrame(
            self.content_frame, text="Track Model Controls"
        )
        # Will be gridded when shown

    def create_train_frame(self):
        """Create the train model frame"""
        self.train_frame = ttk.LabelFrame(self.content_frame, text="Train Model")
        # Will be gridded when shown

    def toggle_track_left(self):
        if self.track_left_visible:
            self.track_left_frame.grid_forget()
            self.btn_track_left.config(text="Show Track Left")
            self.track_left_visible = False
        else:
            self.track_left_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
            self.btn_track_left.config(text="Hide Track Left")
            self.track_left_visible = True
        self.update_column_weights()

    def toggle_track_right(self):
        if self.track_right_visible:
            self.track_right_frame.grid_forget()
            self.btn_track_right.config(text="Show Track Right")
            self.track_right_visible = False
        else:
            self.track_right_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
            self.btn_track_right.config(text="Hide Track Right")
            self.track_right_visible = True
        self.update_column_weights()

    def toggle_train(self):
        if self.train_visible:
            self.train_frame.grid_forget()
            self.btn_train.config(text="Show Train Model")
            self.train_visible = False
        else:
            self.train_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)
            self.btn_train.config(text="Hide Train Model")
            self.train_visible = True
        self.update_column_weights()

    def update_column_weights(self):
        """Adjust column weights based on what's visible"""
        visible_count = sum(
            [self.track_left_visible, self.track_right_visible, self.train_visible]
        )

        # Reset all weights
        for i in range(3):
            self.content_frame.grid_columnconfigure(i, weight=0)

        # Set weights for visible columns
        if self.track_left_visible:
            self.content_frame.grid_columnconfigure(0, weight=2)
        if self.track_right_visible:
            self.content_frame.grid_columnconfigure(1, weight=1)
        if self.train_visible:
            self.content_frame.grid_columnconfigure(2, weight=1)


if __name__ == "__main__":
    app = MainUI()
    app.mainloop()
