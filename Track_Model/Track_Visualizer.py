import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import re
from typing import Dict, List, Tuple
import math

# ---------- EXACT parsing helpers from your code ----------
def extract_station(value: str) -> str:
    text = str(value).upper()
    m = re.search(r"STATION[:;]?\s*([A-Z\s]+)", text)
    return m.group(1).strip().title() if m else "N/A"

def extract_crossing(value: str) -> str:
    return "Yes" if "RAILWAY CROSSING" in str(value).upper() else "No"

def extract_branching(value: str) -> str:
    text = str(value).upper().strip()
    if "SWITCH TO YARD" in text or "SWITCH FROM YARD" in text:
        return "N/A"
    if "SWITCH" not in text:
        return "N/A"
    m = re.search(r"\(([^)]+)\)", text)
    if not m:
        return "N/A"
    inside = m.group(1)
    connected = [c.strip() for c in re.split(r"[;,]", inside) if c.strip()]
    return ", ".join(connected) if connected else "N/A"
# -----------------------------------------------------------

def parse_excel(filepath: str) -> dict:
    """Parse Excel file and return track data for all lines."""
    xl = pd.ExcelFile(filepath)
    track_data = {}
    
    for sheet_name in xl.sheet_names:
        if not sheet_name.endswith("Line"):
            continue
        
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        df = df.fillna("N/A")
        
        # Derive columns from Infrastructure
        if "Infrastructure" in df.columns:
            df["Station"] = df["Infrastructure"].apply(extract_station)
            df["Crossing"] = df["Infrastructure"].apply(extract_crossing)
            df["Branching"] = df["Infrastructure"].apply(extract_branching)
        
        # Block = Section + Block Number (e.g., A + 1 = A1, B + 5 = B5)
        if "Section" in df.columns and "Block Number" in df.columns:
            df["Block"] = df.apply(lambda row: 
                str(row["Section"]).strip() + str(row["Block Number"]).strip() 
                if str(row["Section"]) != "N/A" and str(row["Section"]) != "nan" 
                and str(row["Block Number"]) != "N/A" and str(row["Block Number"]) != "nan"
                else "N/A", axis=1)
        elif "Section" in df.columns:
            df["Block"] = df["Section"].astype(str).str.strip()
            df["Block"] = df["Block"].replace(["nan", ""], "N/A")
        else:
            df["Block"] = "N/A"
        
        track_data[sheet_name] = df
    
    return track_data

class RailwayDiagram:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Railway Diagram - Curved Layout with Blocks")
        self.root.geometry("1400x850")
        
        self.track_data = {}
        self.line_colors = {
            "Blue Line": "#1E90FF",
            "Red Line": "#DC143C",
            "Green Line": "#228B22",
            "Yellow Line": "#FFD700",
            "Orange Line": "#FF8C00",
            "Purple Line": "#9370DB"
        }
        
        self.show_blocks = True
        self.show_stations = True
        self.expanded_sections = {}  # Track which sections are expanded per line: {line_name: set(sections)}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top frame for controls
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(control_frame, text="Load Excel File", 
                   command=self.load_excel).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Line:").pack(side=tk.LEFT, padx=(20, 5))
        self.line_var = tk.StringVar()
        self.line_combo = ttk.Combobox(control_frame, textvariable=self.line_var, 
                                       state="readonly", width=20)
        self.line_combo.pack(side=tk.LEFT, padx=5)
        self.line_combo.bind("<<ComboboxSelected>>", self.on_line_selected)
        
        ttk.Button(control_frame, text="Show All Lines", 
                   command=self.show_all_lines).pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Display options
        self.blocks_var = tk.BooleanVar(value=True)
        self.stations_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(control_frame, text="Show Blocks", 
                       variable=self.blocks_var, 
                       command=self.refresh_display).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(control_frame, text="Show Stations", 
                       variable=self.stations_var, 
                       command=self.refresh_display).pack(side=tk.LEFT, padx=5)
        
        # Legend
        legend_frame = ttk.LabelFrame(control_frame, text="Legend", padding="5")
        legend_frame.pack(side=tk.RIGHT, padx=10)
        
        legend_canvas = tk.Canvas(legend_frame, width=450, height=30, bg="white", 
                                 highlightthickness=0)
        legend_canvas.pack()
        
        # Station symbols
        legend_canvas.create_oval(10, 10, 20, 20, fill="#1E90FF", outline="black", width=2)
        legend_canvas.create_text(25, 15, text="Station", anchor="w", font=("Arial", 8))
        
        # Crossing symbol
        points = [60, 15, 65, 10, 70, 15, 65, 20]
        legend_canvas.create_polygon(points, fill="red", outline="darkred", width=2)
        legend_canvas.create_text(75, 15, text="Crossing", anchor="w", font=("Arial", 8))
        
        # Block dashed line
        legend_canvas.create_line(135, 15, 175, 15, fill="#666", width=2, dash=(5, 3))
        legend_canvas.create_text(180, 15, text="Block Boundary", anchor="w", font=("Arial", 8))
        
        # Branching
        legend_canvas.create_text(300, 15, text="→ Branch", fill="blue", 
                                 anchor="w", font=("Arial", 8, "bold"))
        
        # Canvas with scrollbar
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=1, 
                                highlightbackground="gray")
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, 
                                    command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, 
                                    command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, 
                             yscrollcommand=v_scrollbar.set)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Info panel
        info_frame = ttk.LabelFrame(self.root, text="Information", padding="10")
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.info_text = tk.Text(info_frame, height=5, wrap=tk.WORD, 
                                 font=("Arial", 9))
        self.info_text.pack(fill=tk.BOTH, expand=True)
        self.info_text.insert("1.0", "Load an Excel file to view railway diagram...\n\n"
                             "The diagram shows:\n"
                             "• Click dashed lines to see block details (A1, A2, B4, etc.)\n"
                             "• Hover over blocks and stations for tooltips\n"
                             "• Beautiful curved track layout")
        self.info_text.config(state=tk.DISABLED)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_canvas_hover)
        
        self.hover_id = None
        self.elements = []
        self.current_line = None
        
    def load_excel(self):
        filepath = filedialog.askopenfilename(
            title="Select Railway Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self.track_data = parse_excel(filepath)
            
            if not self.track_data:
                messagebox.showwarning("No Data", 
                    "No sheets ending with 'Line' found in the Excel file.")
                return
            
            # Update line selector
            lines = list(self.track_data.keys())
            self.line_combo['values'] = lines
            if lines:
                self.line_combo.current(0)
                self.on_line_selected()
            
            messagebox.showinfo("Success", 
                f"Loaded {len(self.track_data)} railway lines successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Excel file:\n{str(e)}")
    
    def on_line_selected(self, event=None):
        line_name = self.line_var.get()
        if line_name and line_name in self.track_data:
            self.current_line = line_name
            self.draw_single_line(line_name)
    
    def show_all_lines(self):
        if not self.track_data:
            messagebox.showwarning("No Data", "Please load an Excel file first.")
            return
        self.current_line = None
        self.draw_all_lines()
    
    def refresh_display(self):
        if self.current_line:
            self.draw_single_line(self.current_line)
        elif self.track_data:
            self.draw_all_lines()
    
    def calculate_curved_path(self, num_points: int, start_x: float, start_y: float, 
                             spacing: float, curve_intensity: float = 0.3) -> List[Tuple[float, float]]:
        """Generate a curved path with natural-looking bends and uniform spacing."""
        points = []
        
        for i in range(num_points):
            # Base position with uniform spacing
            x = start_x + i * spacing
            
            # Add sinusoidal curve for natural look
            curve_amplitude = 50 * curve_intensity
            curve_frequency = 0.2
            y = start_y + curve_amplitude * math.sin(i * curve_frequency)
            
            # Add gentle secondary wave
            y += 20 * curve_intensity * math.sin(i * 0.12 + 1.0)
            
            points.append((x, y))
        
        return points
    
    def draw_smooth_curve(self, points: List[Tuple[float, float]], color: str, width: int):
        """Draw a smooth curve through the given points."""
        if len(points) < 2:
            return None
        
        smooth_points = []
        for i in range(len(points)):
            smooth_points.extend([points[i][0], points[i][1]])
        
        if len(smooth_points) >= 4:
            return self.canvas.create_line(smooth_points, fill=color, width=width, 
                                          smooth=True, splinesteps=12, tags="track")
        return None
    
    def draw_single_line(self, line_name: str):
        self.canvas.delete("all")
        self.elements = []
        
        df = self.track_data[line_name]
        color = self.line_colors.get(line_name, "#000000")
        
        show_blocks = self.blocks_var.get()
        show_stations = self.stations_var.get()
        
        # Starting position - adjusted for better fit
        start_x, start_y = 150, 400
        spacing = 65  # Consistent compact spacing throughout
        
        # Collect all elements - SKIP rows where BOTH station AND block are N/A
        elements = []
        for idx, row in df.iterrows():
            station = row.get("Station", "N/A")
            block = row.get("Block", "N/A")
            crossing = row.get("Crossing", "No")
            branching = row.get("Branching", "N/A")
            
            # Skip completely empty rows
            if station == "N/A" and block == "N/A":
                continue
            
            elem = {
                'station': station,
                'block': block,
                'crossing': crossing,
                'branching': branching,
                'index': idx,
                'row': row
            }
            elements.append(elem)
        
        if not elements:
            self.update_info(f"No data found in {line_name}")
            return
        
        # Calculate curved path positions
        positions = self.calculate_curved_path(len(elements), start_x, start_y, spacing)
        
        # Draw curved track line
        self.draw_smooth_curve(positions, color, 6)
        
        # Draw block boundaries as clickable arrows (ABSOLUTELY NO vertical lines)
        if show_blocks:
            current_block = None
            block_start_idx = 0
            block_indices = []  # Track where blocks change
            
            # First pass: identify all block boundaries
            for i, elem in enumerate(elements):
                block_id = elem['block']
                if block_id != "N/A" and block_id != current_block:
                    if current_block is not None:
                        block_indices.append((current_block, block_start_idx, i-1))
                    current_block = block_id
                    block_start_idx = i
            
            # Add the final block
            if current_block is not None:
                block_indices.append((current_block, block_start_idx, len(elements)-1))
            
            # Group blocks by section (A, B, C, etc.)
            sections = {}
            for block_name, start_idx, end_idx in block_indices:
                # Extract section letter (first character)
                section = block_name[0] if block_name != "N/A" else "N/A"
                if section not in sections:
                    sections[section] = []
                sections[section].append((block_name, start_idx, end_idx))
            
            # Get expanded sections for current line
            current_expanded = self.expanded_sections.get(line_name, set())
            
            # Second pass: draw sections and blocks
            for section, blocks in sections.items():
                # Get overall section range
                section_start = blocks[0][1]
                section_end = blocks[-1][2]
                
                # Check if this section is expanded
                is_expanded = section in current_expanded
                
                if is_expanded:
                    # EXPANDED: Show individual blocks with arrows
                    for idx, (block_name, start_idx, end_idx) in enumerate(blocks):
                        # Draw arrow at the END of each block (except the very last one in section)
                        if idx < len(blocks) - 1:
                            x, y = positions[blocks[idx + 1][1]]  # Position at next block start
                            
                            arrow_size = 14
                            arrow_id = self.canvas.create_polygon(
                                x + 3, y,
                                x - arrow_size, y - arrow_size,
                                x - arrow_size, y + arrow_size,
                                fill="#555", outline="#333", width=1, tags="block_boundary_arrow"
                            )
                            
                            self.elements.append({
                                'id': arrow_id,
                                'type': 'block_boundary',
                                'data': {'name': block_name, 'start_idx': start_idx, 'end_idx': end_idx, 'section': section}
                            })
                        
                        # Block label
                        start_x_block = positions[start_idx][0]
                        end_x_block = positions[end_idx][0]
                        mid_x = (start_x_block + end_x_block) / 2
                        mid_y = (positions[start_idx][1] + positions[end_idx][1]) / 2
                        
                        label_id = self.canvas.create_text(
                            mid_x, mid_y - 80,
                            text=block_name,
                            font=("Arial", 10, "bold"), fill="#222",
                            tags="block_label"
                        )
                        
                        self.elements.append({
                            'id': label_id,
                            'type': 'block_label',
                            'data': {'name': block_name, 'start_idx': start_idx, 'end_idx': end_idx, 'section': section}
                        })
                else:
                    # COLLAPSED: Show only section letter - VERY COMPACT
                    # Just use first position in section
                    start_x_section = positions[section_start][0]
                    start_y_section = positions[section_start][1]
                    
                    # Clickable section label (small)
                    label_id = self.canvas.create_text(
                        start_x_section, start_y_section - 80,
                        text=section,
                        font=("Arial", 11, "bold"), fill="#0066CC",
                        tags="section_label"
                    )
                    
                    self.elements.append({
                        'id': label_id,
                        'type': 'section_label',
                        'data': {'section': section, 'blocks': blocks, 'start_idx': section_start, 'end_idx': section_end}
                    })
                
                # Draw arrow at end of section if not last section
                section_list = list(sections.keys())
                if section != section_list[-1]:
                    next_section_start = list(sections.values())[section_list.index(section) + 1][0][1]
                    x, y = positions[next_section_start]
                    
                    arrow_size = 16
                    section_arrow_id = self.canvas.create_polygon(
                        x + 3, y,
                        x - arrow_size, y - arrow_size,
                        x - arrow_size, y + arrow_size,
                        fill="#333", outline="#000", width=2, tags="section_boundary_arrow"
                    )
                    
                    self.elements.append({
                        'id': section_arrow_id,
                        'type': 'section_boundary',
                        'data': {'section': section}
                    })
        
        # Draw stations along the curved path
        if show_stations:
            for i, elem in enumerate(elements):
                if elem['station'] == "N/A":
                    continue
                
                x, y = positions[i]
                
                # Draw station marker
                if elem['crossing'] == "Yes":
                    # Diamond for crossing
                    size = 14
                    points = [x, y-size, x+size, y, x, y+size, x-size, y]
                    marker_id = self.canvas.create_polygon(points, fill="red", 
                                                           outline="darkred", width=2,
                                                           tags="station")
                else:
                    # Circle for normal station
                    size = 12
                    marker_id = self.canvas.create_oval(x-size, y-size, x+size, y+size,
                                                        fill=color, outline="black", width=3,
                                                        tags="station")
                
                # Station name with background for readability
                name_text = elem['station']
                bg_id = self.canvas.create_rectangle(x-50, y+25, x+50, y+50,
                                                     fill="white", outline="gray",
                                                     tags="station_bg")
                name_id = self.canvas.create_text(x, y + 38, text=name_text,
                                                  font=("Arial", 9, "bold"), 
                                                  anchor="center", tags="station_name")
                
                # Branching info
                if elem['branching'] != "N/A":
                    branch_text = elem['branching']
                    branch_bg_id = self.canvas.create_rectangle(x-55, y-50, x+55, y-25,
                                                                fill="#E3F2FD", outline="blue",
                                                                tags="branch_bg")
                    branch_id = self.canvas.create_text(x, y - 38, 
                                                        text=f"→ {branch_text}", 
                                                        font=("Arial", 8, "bold"), 
                                                        fill="blue", anchor="center",
                                                        tags="branch")
                    self.elements.append({
                        'id': branch_bg_id,
                        'type': 'branch',
                        'data': elem
                    })
                    self.elements.append({
                        'id': branch_id,
                        'type': 'branch',
                        'data': elem
                    })
                
                # Store element data for interaction
                self.elements.append({
                    'id': marker_id,
                    'type': 'station',
                    'data': elem
                })
                self.elements.append({
                    'id': bg_id,
                    'type': 'station',
                    'data': elem
                })
                self.elements.append({
                    'id': name_id,
                    'type': 'station',
                    'data': elem
                })
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Count statistics
        station_count = sum(1 for e in elements if e['station'] != "N/A")
        block_list = [e['block'] for e in elements if e['block'] != "N/A"]
        unique_blocks = sorted(set(block_list))
        crossing_count = sum(1 for e in elements if e['crossing'] == "Yes")
        
        info = f"{line_name}\n"
        info += f"• Stations: {station_count}\n"
        info += f"• Blocks: {', '.join(unique_blocks) if unique_blocks else 'None'}\n"
        info += f"• Railway Crossings: {crossing_count}"
        self.update_info(info)
    
    def draw_all_lines(self):
        self.canvas.delete("all")
        self.elements = []
        
        line_names = list(self.track_data.keys())
        if not line_names:
            return
        
        show_blocks = self.blocks_var.get()
        show_stations = self.stations_var.get()
        
        start_x = 150
        spacing_x = 90
        spacing_y = 200
        
        for line_idx, line_name in enumerate(line_names):
            df = self.track_data[line_name]
            color = self.line_colors.get(line_name, "#000000")
            
            base_y = 150 + line_idx * spacing_y
            
            elements = []
            for idx, row in df.iterrows():
                station = row.get("Station", "N/A")
                block = row.get("Block", "N/A")
                crossing = row.get("Crossing", "No")
                branching = row.get("Branching", "N/A")
                
                elements.append({
                    'station': station,
                    'block': block,
                    'crossing': crossing,
                    'branching': branching,
                    'line': line_name,
                    'row': row
                })
            
            if not elements:
                continue
            
            # Draw line label
            self.canvas.create_text(30, base_y, text=line_name, 
                                   font=("Arial", 11, "bold"),
                                   fill=color, anchor="e")
            
            # Calculate curved positions for this line
            positions = self.calculate_curved_path(len(elements), start_x, base_y, 
                                                   spacing_x, curve_intensity=0.2)
            
            # Draw curved track
            self.draw_smooth_curve(positions, color, 4)
            
            # Draw block boundaries (simplified for overview)
            if show_blocks:
                current_block = None
                for i, elem in enumerate(elements):
                    block_id = elem['block']
                    if block_id != "N/A" and block_id != current_block:
                        if current_block is not None and i > 0:
                            x, y = positions[i]
                            self.canvas.create_line(
                                x, y - 40, x, y + 40,
                                fill="#999", width=2, dash=(6, 3)
                            )
                        current_block = block_id
            
            # Draw stations
            if show_stations:
                for i, elem in enumerate(elements):
                    if elem['station'] == "N/A":
                        continue
                    
                    x, y = positions[i]
                    
                    size = 8
                    if elem['crossing'] == "Yes":
                        points = [x, y-size, x+size, y, x, y+size, x-size, y]
                        marker_id = self.canvas.create_polygon(points, fill="red", 
                                                              outline="darkred", width=1)
                    else:
                        marker_id = self.canvas.create_oval(x-size, y-size, x+size, y+size,
                                                           fill=color, outline="black", width=2)
                    
                    name_id = self.canvas.create_text(x, y + 20, text=elem['station'],
                                                     font=("Arial", 7), anchor="n")
                    
                    self.elements.append({
                        'id': marker_id,
                        'type': 'station',
                        'data': elem
                    })
                    self.elements.append({
                        'id': name_id,
                        'type': 'station',
                        'data': elem
                    })
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.update_info(f"Showing {len(line_names)} railway lines (overview mode)")
    
    def on_canvas_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        items = self.canvas.find_overlapping(x-15, y-15, x+15, y+15)
        
        # Prioritize stations over everything
        for item in items:
            for element in self.elements:
                if element['id'] == item:
                    if element['type'] in ['station', 'station_name', 'station_bg']:
                        self.show_station_details(element['data'])
                        return
        
        # Check for section label click (to expand/collapse)
        for item in items:
            for element in self.elements:
                if element['id'] == item:
                    if element['type'] == 'section_label':
                        section = element['data']['section']
                        line_name = self.current_line
                        
                        # Initialize set for this line if doesn't exist
                        if line_name not in self.expanded_sections:
                            self.expanded_sections[line_name] = set()
                        
                        # Toggle expansion for this line
                        if section in self.expanded_sections[line_name]:
                            self.expanded_sections[line_name].remove(section)
                        else:
                            self.expanded_sections[line_name].add(section)
                        
                        # Redraw
                        self.draw_single_line(line_name)
                        return
        
        # Check for block label click (also toggle collapse)
        for item in items:
            for element in self.elements:
                if element['id'] == item:
                    if element['type'] == 'block_label':
                        # Can click block label to collapse section
                        section = element['data']['section']
                        line_name = self.current_line
                        
                        if line_name in self.expanded_sections and section in self.expanded_sections[line_name]:
                            self.expanded_sections[line_name].remove(section)
                            self.draw_single_line(line_name)
                            return
                        else:
                            # Show block details
                            self.show_block_details(element['data'])
                            return
        
        # Check for block boundary click
        for item in items:
            for element in self.elements:
                if element['id'] == item:
                    if element['type'] in ['block_boundary', 'block_boundary_arrow']:
                        self.show_block_details(element['data'])
                        return
    
    def on_canvas_hover(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Remove previous highlight
        if self.hover_id:
            try:
                tags = self.canvas.gettags(self.hover_id)
                if "station" in tags:
                    self.canvas.itemconfig(self.hover_id, width=3)
                elif "block_boundary" in tags:
                    self.canvas.itemconfig(self.hover_id, width=5, fill="#666")
                elif "section_label" in tags:
                    self.canvas.itemconfig(self.hover_id, fill="#0066CC")
            except:
                pass
            self.hover_id = None
        
        self.canvas.delete("tooltip")
        
        items = self.canvas.find_overlapping(x-10, y-10, x+10, y+10)
        
        # Prioritize stations in hover
        for item in items:
            for element in self.elements:
                if element['id'] == item and element['type'] == 'station':
                    self.canvas.itemconfig(item, width=5)
                    self.hover_id = item
                    self.root.config(cursor="hand2")
                    station_name = element['data']['station']
                    block_name = element['data'].get('block', 'N/A')
                    self.show_hover_tooltip(x, y, f"{station_name} ({block_name})")
                    return
        
        # Check for section label
        for item in items:
            for element in self.elements:
                if element['id'] == item and element['type'] == 'section_label':
                    section = element['data']['section']
                    self.canvas.itemconfig(item, fill="#FF6600")
                    self.hover_id = item
                    self.root.config(cursor="hand2")
                    self.show_hover_tooltip(x, y, f"Section {section} (click to expand)")
                    return
        
        # Check for block boundary if no station
        for item in items:
            for element in self.elements:
                if element['id'] == item:
                    if element['type'] in ['block_boundary', 'block_boundary_arrow']:
                        block_name = element['data']['name']
                        self.canvas.itemconfig(item, width=7, fill="#FF6B6B")
                        self.hover_id = item
                        self.root.config(cursor="hand2")
                        self.show_hover_tooltip(x, y, block_name)
                        return
                    elif element['type'] == 'block_label':
                        block_name = element['data']['name']
                        self.root.config(cursor="hand2")
                        self.show_hover_tooltip(x, y, block_name)
                        return
        
        self.root.config(cursor="")
    
    def show_hover_tooltip(self, x, y, text):
        """Show a hover tooltip near the cursor."""
        tooltip_width = len(text) * 8 + 20
        tooltip_bg = self.canvas.create_rectangle(
            x + 15, y - 30, x + 15 + tooltip_width, y - 5,
            fill="#FFFACD", outline="#333", width=2, tags="tooltip"
        )
        tooltip_text = self.canvas.create_text(
            x + 15 + tooltip_width // 2, y - 17,
            text=text, font=("Arial", 10, "bold"), tags="tooltip"
        )
    
    def show_station_details(self, station_data):
        info = f"STATION: {station_data['station']}\n"
        info += f"Block: {station_data.get('block', 'N/A')}\n"
        info += f"Railway Crossing: {station_data['crossing']}\n"
        info += f"Branching: {station_data['branching']}"
        self.update_info(info)
    
    def show_block_details(self, block_data):
        block_name = block_data['name']
        info = f"BLOCK: {block_name}\n"
        info += f"Individual block identifier (Section + Block Number)\n"
        
        # Get all stations in this block
        if 'start_idx' in block_data and 'end_idx' in block_data:
            start = block_data['start_idx']
            end = block_data['end_idx']
            
            if self.current_line and self.current_line in self.track_data:
                df = self.track_data[self.current_line]
                block_stations = []
                for idx in range(start, end + 1):
                    if idx < len(df):
                        row = df.iloc[idx]
                        station = row.get("Station", "N/A")
                        if station != "N/A":
                            block_stations.append(station)
                
                if block_stations:
                    info += f"\nStations: {', '.join(block_stations)}"
                else:
                    info += f"\nNo stations in this block"
        
        self.update_info(info)
    
    def update_info(self, text):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", text)
        self.info_text.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = RailwayDiagram(root)
    root.mainloop()

if __name__ == "__main__":
    main()