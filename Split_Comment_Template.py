import tkinter as tk
from tkinter import filedialog, ttk, colorchooser, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont, ExifTags
import sys
import os
import glob
import json
import shutil  # Import the shutil module
import getpass
import winreg
import threading
import time

# ------------ Default Paths and Settings ------------
DEFAULT_CONFIG_PATH = "config.json"
DEFAULT_BOTTOM_IMAGE_PATH = "C:/Scripts/background-1.jpg"
DEFAULT_FONT_PATH = "C:/Scripts/Huruf-Font-1.ttf"



# ------------ Border config state ---------------
border_config = {
    "top": {"enabled": True, "width": 10, "color": "black"},
    "bottom": {"enabled": True, "width": 10, "color": "black"},
    "left": {"enabled": True, "width": 10, "color": "black"},
    "right": {"enabled": True, "width": 10, "color": "black"},
}

# =========================== Layout default heights ===========================
top_img_height = 1860
bottom_img_height = 1500

# =========================== Watermark defaults ===========================
# Text watermark settings (existing)
watermark_text = "FB : Yaxhup"
text_color = (255, 255, 0)
opacity = 128
stroke_enabled = True
position_offset = (75, 1665)

# New image watermark settings
watermark_image_path = ""  # Path to watermark image file
image_opacity = 200  # Image transparency (0-255)
image_size = 300  # Size of watermark image in pixels
image_position_offset = (50, 50)  # X, Y position of image watermark

# Watermark type control
watermark_type = "text"  # Options: "text", "image", "both"

# Additional text settings (if not already present)
text_settings = {
    "font_path": "arial.ttf",  # Default font
    "text_color": "#000000",  # Text color
    "box_color": "#FFFFFF",  # Text box background color
    "box_style": "rounded",  # Box style: "rounded", "rectangle", "dashed"
    "text_stroke": True,  # Text outline
    "offset_x": 100,  # Text box X position
    "offset_y": 100,  # Text box Y position
    "box_width": 800,  # Text box width
    "box_height": 200  # Text box height
}

# =========================== Text settings defaults ===========================
text_settings = {
    "font_path": DEFAULT_FONT_PATH,
    "text_color": "black",
    "box_color": "white",
    "box_style": "rounded",
    "text_stroke": False,
    "offset_x": 150,
    "offset_y": 1800,
    "box_width": 2700,
    "box_height": 975,
}

def make_scrollable_notebook(root):
    container = tk.Frame(root)
    container.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(container)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    notebook_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=notebook_frame, anchor="nw")

    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    notebook_frame.bind("<Configure>", on_configure)

    return notebook_frame


class ImageTextComposer:
    def __init__(self, root, config_path=DEFAULT_CONFIG_PATH):
        self.root = root
        self.root.title("Image + Text Composer (3000x3000 JPG)")

        self.canvas_size = 3000
        self.canvas = tk.Canvas(root, width=300, height=300)
        self.canvas.pack()

        self.top_image_path = None
        self.bottom_image_path = DEFAULT_BOTTOM_IMAGE_PATH  # Use default

        self.config_path = config_path
        self.load_config() # Load config *before* building UI

        notebook_frame = make_scrollable_notebook(root)
        control_tabs = ttk.Notebook(notebook_frame)
        control_tabs.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # Layout customization tab
        layout_frame = ttk.Frame(control_tabs)
        control_tabs.add(layout_frame, text="🖼 Layout Customization")
        tk.Button(layout_frame, text="Ganti Gambar Atas", command=self.load_top_image).pack(pady=2)
        tk.Button(layout_frame, text="Ganti Gambar Bawah", command=self.load_bottom_image).pack(pady=2)
        
        self.build_layout_controls(layout_frame)

        # Border controls tab
        border_frame = ttk.Frame(control_tabs)
        control_tabs.add(border_frame, text="🟦 Border Controls")
        self.build_border_controls(border_frame)

        # Watermark settings tab
        watermark_frame = ttk.Frame(control_tabs)
        control_tabs.add(watermark_frame, text="💧 Watermark Settings")
        self.build_watermark_controls(watermark_frame)

        # Text settings tab
        text_frame = ttk.Frame(control_tabs)
        control_tabs.add(text_frame, text="✍️ Text Settings")
        self.text_box = tk.Text(text_frame, wrap=tk.WORD, width=100, height=6, font=("Arial", 12))
        self.text_box.pack(pady=5)
        self.build_text_controls(text_frame)

        # Buttons below tabs
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="🔁 Refresh Image Preview", command=self.draw_template).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="💾 Simpan Gambar (JPG)", command=self.save_composite).pack(side=tk.LEFT, padx=5)
        
        # Add export button and Find and Replace config.json
        tk.Button(btn_frame, text="Export Script (Auto Rename Config)", command=self.export_with_config_replacement).pack(side=tk.LEFT, padx=5) 
        
        # Context Menu Registry tab
        context_menu_frame = ttk.Frame(control_tabs)
        control_tabs.add(context_menu_frame, text="🖱️ Add Script to Context Menu")
        self.build_context_menu_controls(context_menu_frame)
 
        self.last_image = None
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Save on close
        

    def load_top_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.top_image_path = path
            extracted_text = self.extract_text_from_exif(path)
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert("1.0", extracted_text)
            self.draw_template()

    def load_bottom_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.bottom_image_path = path
            self.draw_template()

    def extract_text_from_exif(self, image_path):
        try:
            img = Image.open(image_path)
            exif = img.getexif()
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag in ["UserComment", "ImageDescription"]:
                    text = str(value)
                    if "****" in text and "----" in text:
                        start = text.find("****") + 4
                        end = text.find("----")
                        extracted = text[start:end].strip()
                        extracted = extracted.replace("  ", " ")
                        extracted = extracted.replace("😊", "😎")
                        return extracted
            return ""
        except Exception as e:
            print("EXIF error:", e)
            return ""

    def draw_template(self):
        base = Image.new("RGB", (self.canvas_size, self.canvas_size), "white")
        base, draw = self.apply_layout(base)
        self.draw_global_border(draw, self.canvas_size)

        box = (150, 1800, 2850, 2775)
        self.draw_textbox_shape(draw, box)

        text = self.text_box.get("1.0", "end-1c").strip()

        font_path = text_settings["font_path"]
        self.render_text(draw, box, text, font_path)
        base = self.add_watermark(base)

        thumb = base.resize((300, 300))
        self.tk_image = ImageTk.PhotoImage(thumb)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.last_image = base

    def save_composite(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg")])
        if file_path:
            self.last_image.save(file_path, "JPEG", quality=95)

    def export_with_config_replacement(self):
            # Step 1: Ask user what type of export they want (SWAPPED OPTIONS)
            export_choice = messagebox.askyesnocancel(
                "Export Options",
                "Choose export type:\n\n" +
                "YES = Export as Python Script (.py)\n" +
                "NO = Export as Compiled EXE (.exe)\n" +
                "CANCEL = Cancel export"
            )
            
            if export_choice is None:  # User clicked Cancel
                return
            
            export_as_exe = not export_choice  # True if user clicked NO (wants EXE)
            
            # Step 2: Ask where to save the file
            if export_as_exe:
                new_file_path = filedialog.asksaveasfilename(
                    defaultextension=".exe",
                    filetypes=[("Executable Files", "*.exe")],
                    title="Export as EXE"
                )
            else:
                new_file_path = filedialog.asksaveasfilename(
                    defaultextension=".py",
                    filetypes=[("Python Files", "*.py")],
                    title="Export Script As"
                )
            
            if not new_file_path:
                return  # Cancelled
            
            try:
                # Step 3: Get base name and paths
                base_name = os.path.splitext(os.path.basename(new_file_path))[0]
                new_config_name = f"{base_name}.json"
                output_dir = os.path.dirname(new_file_path)
                new_config_path = os.path.join(output_dir, new_config_name)
                
                # Step 4: Create temporary script for compilation (if needed)
                current_script_path = os.path.abspath(sys.argv[0])
                
                if export_as_exe:
                    # Create temporary script with updated config name
                    temp_script_path = os.path.join(output_dir, f"{base_name}_temp.py")
                    shutil.copy(current_script_path, temp_script_path)
                    
                    # Update config name in temporary script with full path
                    with open(temp_script_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if "config.json" in content:
                        content = content.replace("config.json", new_config_path)
                        with open(temp_script_path, "w", encoding="utf-8") as f:
                            f.write(content)
                else:
                    # Regular script export
                    shutil.copy(current_script_path, new_file_path)
                    
                    # Update config name in script with full path
                    with open(new_file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    config_replaced = False
                    if "config.json" in content:
                        content = content.replace("config.json", new_config_path)
                        with open(new_file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        config_replaced = True
                
                # Step 5: Export current configuration to new JSON file
                config = {
                    # Existing settings
                    "border_config": border_config,
                    "top_img_height": top_img_height,
                    "bottom_img_height": bottom_img_height,
                    "watermark_text": watermark_text,
                    "text_color": text_color,
                    "opacity": opacity,
                    "stroke_enabled": stroke_enabled,
                    "position_offset": position_offset,
                    "text_settings": text_settings,
                    "bottom_image_path": self.bottom_image_path,
                    "font_path": text_settings["font_path"],
                    
                    # New watermark settings
                    "watermark_image_path": watermark_image_path,
                    "image_opacity": image_opacity,
                    "image_size": image_size,
                    "image_position_offset": image_position_offset,
                    "watermark_type": watermark_type,
                    
                    # Added config file location information
                    "config_file_path": new_config_path,
                    "config_file_name": new_config_name
                }
                
                with open(new_config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
                
                # Step 6: Compile to EXE if requested
                if export_as_exe:
                    # Check if PyInstaller is available
                    try:
                        import PyInstaller
                    except ImportError:
                        messagebox.showerror(
                            "PyInstaller Not Found",
                            "PyInstaller is required to compile to EXE.\n\n" +
                            "Install it using: pip install pyinstaller\n\n" +
                            "The Python script and config have been saved instead."
                        )
                        # Clean up temp file
                        if os.path.exists(temp_script_path):
                            os.remove(temp_script_path)
                        return
                    
                    # Show compilation progress
                    progress_window = tk.Toplevel(self.root)
                    progress_window.title("Compiling...")
                    progress_window.geometry("400x100")
                    progress_window.transient(self.root)
                    progress_window.grab_set()
                    
                    progress_label = tk.Label(progress_window, text="Compiling to EXE, please wait...")
                    progress_label.pack(pady=20)
                    
                    progress_window.update()
                    
                    try:
                        # Run PyInstaller with comprehensive bundling
                        import subprocess
                        cmd = [
                            "pyinstaller",
                            "--onefile",
                            "--windowed",
                            "--distpath", output_dir,
                            "--workpath", os.path.join(output_dir, "build"),
                            "--specpath", output_dir,
                            "--name", base_name,
                            "--collect-all", "PIL",  # Pillow/PIL image library
                            "--collect-all", "tkinter",  # Tkinter GUI
                            "--hidden-import", "PIL._tkinter_finder",
                            "--hidden-import", "PIL.ImageTk",
                            "--hidden-import", "PIL.Image",
                            "--hidden-import", "PIL.ImageDraw",
                            "--hidden-import", "PIL.ImageFont",
                            "--hidden-import", "PIL.ImageFilter",
                            "--hidden-import", "tkinter.filedialog",
                            "--hidden-import", "tkinter.messagebox",
                            "--hidden-import", "tkinter.colorchooser",
                            "--add-data", f"{new_config_path};.",  # Include config file
                            temp_script_path
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir)
                        
                        progress_window.destroy()
                        
                        if result.returncode == 0:
                            # Clean up temporary files
                            if os.path.exists(temp_script_path):
                                os.remove(temp_script_path)
                            
                            # Clean up PyInstaller build files
                            build_dir = os.path.join(output_dir, "build")
                            spec_file = os.path.join(output_dir, f"{base_name}.spec")
                            
                            if os.path.exists(build_dir):
                                shutil.rmtree(build_dir)
                            if os.path.exists(spec_file):
                                os.remove(spec_file)
                            
                            success_message = f"EXE compiled successfully!\n\n" + \
                                            f"Executable: {new_file_path}\n" + \
                                            f"Configuration: {new_config_path}\n\n" + \
                                            f"Ready to distribute!"
                            
                            messagebox.showinfo("Compilation Complete", success_message)
                        else:
                            messagebox.showerror(
                                "Compilation Failed",
                                f"PyInstaller failed with error:\n\n{result.stderr}"
                            )
                            
                    except Exception as e:
                        progress_window.destroy()
                        messagebox.showerror("Compilation Error", f"Error during compilation:\n{e}")
                    
                else:
                    # Regular script export success message
                    success_message = f"Script saved to:\n{new_file_path}\n\nConfiguration exported to:\n{new_config_path}"
                    
                    if config_replaced:
                        success_message += f"\n\nReplaced 'config.json' with full path '{new_config_path}' in the script."
                    else:
                        success_message += f"\n\nNote: 'config.json' not found in script, so no replacement was made."
                    
                    messagebox.showinfo("Export Complete", success_message)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export:\n{e}")

    # =========================== Config Load/Save ===========================
    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                global border_config, top_img_height, bottom_img_height, watermark_text, \
                       text_color, opacity, stroke_enabled, position_offset, text_settings, \
                       watermark_image_path, image_opacity, image_size, image_position_offset, \
                       watermark_type
                
                # Existing settings
                border_config = config.get("border_config", border_config)
                top_img_height = config.get("top_img_height", top_img_height)
                bottom_img_height = config.get("bottom_img_height", bottom_img_height)
                watermark_text = config.get("watermark_text", watermark_text)
                text_color = tuple(config.get("text_color", text_color))  # Ensure tuple
                opacity = config.get("opacity", opacity)
                stroke_enabled = config.get("stroke_enabled", stroke_enabled)
                position_offset = tuple(config.get("position_offset", position_offset))
                text_settings = config.get("text_settings", text_settings)
                
                # New watermark settings
                watermark_image_path = config.get("watermark_image_path", watermark_image_path)
                image_opacity = config.get("image_opacity", image_opacity)
                image_size = config.get("image_size", image_size)
                image_position_offset = tuple(config.get("image_position_offset", image_position_offset))
                watermark_type = config.get("watermark_type", watermark_type)
                
                # Path settings
                self.bottom_image_path = config.get("bottom_image_path", DEFAULT_BOTTOM_IMAGE_PATH)
                text_settings["font_path"] = config.get("font_path", DEFAULT_FONT_PATH)
                
                print("Configuration loaded successfully.")
        except FileNotFoundError:
            print("Config file not found. Using default settings.")
        except json.JSONDecodeError:
            print("Error decoding config file. Using default settings.")
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        try:
            config = {
                # Existing settings
                "border_config": border_config,
                "top_img_height": top_img_height,
                "bottom_img_height": bottom_img_height,
                "watermark_text": watermark_text,
                "text_color": text_color,
                "opacity": opacity,
                "stroke_enabled": stroke_enabled,
                "position_offset": position_offset,
                "text_settings": text_settings,
                "bottom_image_path": self.bottom_image_path,
                "font_path": text_settings["font_path"],
                
                # New watermark settings
                "watermark_image_path": watermark_image_path,
                "image_opacity": image_opacity,
                "image_size": image_size,
                "image_position_offset": image_position_offset,
                "watermark_type": watermark_type
            }
            
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
            print("Configuration saved successfully.")
        except Exception as e:
            print(f"Error saving config: {e}")
        
    def on_close(self):
        self.save_config()
        self.root.destroy()

    # =========================== Layout customization ===========================
    def apply_layout(self, base):
        draw = ImageDraw.Draw(base)

        if self.top_image_path:
            top_img = Image.open(self.top_image_path).resize((3000, top_img_height))
            base.paste(top_img, (0, 0))
            draw.rectangle([0, 0, 3000, top_img_height], outline="black", width=6)

        if self.bottom_image_path:
            bottom_img = Image.open(self.bottom_image_path).resize((3000, bottom_img_height))
            base.paste(bottom_img, (0, top_img_height))
            draw.rectangle([0, top_img_height, 3000, top_img_height + bottom_img_height], outline="black", width=6)

        return base, draw

    def build_layout_controls(self, frame):
        def update_top(val):
            global top_img_height
            top_img_height = int(val)
            self.draw_template()

        def update_bottom(val):
            global bottom_img_height
            bottom_img_height = int(val)
            self.draw_template()

        # Horizontal container to reduce height
        sliders_row = tk.Frame(frame)
        sliders_row.pack(pady=5)

        # Top image slider
        top_frame = tk.Frame(sliders_row)
        top_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(top_frame, text="Tinggi Atas").pack()
        top_slider = tk.Scale(top_frame, from_=500, to=2800, orient="vertical", length=120, command=update_top)
        top_slider.set(top_img_height)
        top_slider.pack()

        # Bottom image slider
        bottom_frame = tk.Frame(sliders_row)
        bottom_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(bottom_frame, text="Tinggi Bawah").pack()
        bottom_slider = tk.Scale(bottom_frame, from_=200, to=2000, orient="vertical", length=120, command=update_bottom)
        bottom_slider.set(bottom_img_height)
        bottom_slider.pack()

    # =========================== Border controls ===========================
    def draw_global_border(self, draw, canvas_size):
        # Skip drawing if all borders are disabled or have 0 width
        if not any(cfg["enabled"] and cfg["width"] > 0 for cfg in border_config.values()):
            return

        for side, cfg in border_config.items():
            if not cfg["enabled"] or cfg["width"] <= 0:
                continue
            width = cfg["width"]
            color = cfg["color"]

            for i in range(width):
                if side == "top":
                    draw.line([(i, i), (canvas_size - i - 1, i)], fill=color)
                elif side == "bottom":
                    draw.line([(i, canvas_size - i - 1), (canvas_size - i - 1, canvas_size - i - 1)], fill=color)
                elif side == "left":
                    draw.line([(i, i), (i, canvas_size - i - 1)], fill=color)
                elif side == "right":
                    draw.line([(canvas_size - i - 1, i), (canvas_size - i - 1, canvas_size - i - 1)], fill=color)

    def build_border_controls(self, frame):
        def make_control(side):
            cfg = border_config[side]
            group = tk.LabelFrame(frame, text=f"{side.capitalize()} Border", padx=5, pady=3)
            group.pack(side=tk.LEFT, padx=5, pady=5, anchor="n")

            var = tk.BooleanVar(value=cfg["enabled"])
            chk = tk.Checkbutton(group, text="Enable", variable=var,
                                 command=lambda: self.toggle_border(side, var.get()))
            chk.pack()

            slider = tk.Scale(group, from_=0, to=50, orient="horizontal", label="Width", length=120)
            slider.set(cfg["width"])
            slider.pack()
            slider.bind("<B1-Motion>", lambda e: self.update_border_width(side, slider.get()))
            slider.bind("<ButtonRelease-1>", lambda e: self.update_border_width(side, slider.get()))

            btn = tk.Button(group, text="Color", command=lambda: self.choose_border_color(side))
            btn.pack(pady=2)

        def toggle_border(side, value):
            border_config[side]["enabled"] = value
            self.draw_template()

        def update_border_width(side, value):
            border_config[side]["width"] = int(value)
            self.draw_template()

        def choose_border_color(side):
            color = colorchooser.askcolor(initialcolor=border_config[side]["color"])
            if color[1]:
                border_config[side]["color"] = color[1]
                self.draw_template()

        for side in ["top", "bottom", "left", "right"]:
            make_control(side)

    def toggle_border(self, side, value):
        border_config[side]["enabled"] = value
        self.draw_template()

    def update_border_width(self, side, value):
        border_config[side]["width"] = int(value)
        self.draw_template()

    def choose_border_color(self, side):
        color = colorchooser.askcolor(initialcolor=border_config[side]["color"])
        if color[1]:
            border_config[side]["color"] = color[1]
            self.draw_template()

     # =========================== Watermark settings with PNG support ===========================
    def build_watermark_controls(self, frame):
        def update_redraw(*_):
            self.draw_template()
        
        def pick_color():
            global text_color
            color = colorchooser.askcolor(initialcolor=text_color)
            if color[0]:
                text_color = tuple(int(c) for c in color[0])
                update_redraw()
        
        def pick_font():
            path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
            if path:
                text_settings["font_path"] = path
                update_redraw()
        
        def pick_image():
            global watermark_image_path
            path = filedialog.askopenfilename(
                title="Select Watermark Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("PNG Files", "*.png"), ("All Files", "*.*")]
            )
            if path:
                watermark_image_path = path
                # Update UI to show selected image
                image_label.config(text=f"Image: {os.path.basename(path)}")
                update_redraw()
        
        def clear_image():
            global watermark_image_path
            watermark_image_path = ""
            image_label.config(text="No image selected")
            update_redraw()
        
        def update_opacity(val):
            global opacity
            opacity = int(val)
            update_redraw()
        
        def update_image_opacity(val):
            global image_opacity
            image_opacity = int(val)
            update_redraw()
        
        def update_position_x(val):
            global position_offset
            position_offset = (int(val), position_offset[1])
            update_redraw()
        
        def update_position_y(val):
            global position_offset
            position_offset = (position_offset[0], int(val))
            update_redraw()
        
        def update_image_position_x(val):
            global image_position_offset
            image_position_offset = (int(val), image_position_offset[1])
            update_redraw()
        
        def update_image_position_y(val):
            global image_position_offset
            image_position_offset = (image_position_offset[0], int(val))
            update_redraw()
        
        def update_image_size(val):
            global image_size
            image_size = int(val)
            update_redraw()
        
        def toggle_stroke():
            global stroke_enabled
            stroke_enabled = stroke_var.get()
            update_redraw()
        
        def toggle_watermark_type():
            global watermark_type
            watermark_type = watermark_type_var.get()
            update_redraw()
        
        def text_changed(*_):
            global watermark_text
            watermark_text = text_entry.get()
            update_redraw()
        
        # Main container with tabs/sections
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Text Watermark Tab
        text_frame = ttk.Frame(notebook)
        notebook.add(text_frame, text="Text Watermark")
        
        # Image Watermark Tab
        image_frame = ttk.Frame(notebook)
        notebook.add(image_frame, text="Image Watermark")
        
        # Settings Tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        
        # === TEXT WATERMARK TAB ===
        text_left_col = tk.Frame(text_frame)
        text_right_col = tk.Frame(text_frame)
        text_left_col.pack(side=tk.LEFT, padx=10, pady=10, anchor="n")
        text_right_col.pack(side=tk.LEFT, padx=10, pady=10, anchor="n")
        
        # Text controls
        tk.Label(text_left_col, text="Watermark Text:", font=("Arial", 10, "bold")).pack(anchor="w")
        text_entry = tk.Entry(text_left_col, width=30, font=("Arial", 10))
        text_entry.insert(0, watermark_text)
        text_entry.pack(pady=2)
        text_entry.bind("<KeyRelease>", text_changed)
        
        tk.Button(text_left_col, text="📁 Choose Font", command=pick_font, width=15).pack(pady=3)
        tk.Button(text_left_col, text="🎨 Choose Color", command=pick_color, width=15).pack(pady=3)
        
        stroke_var = tk.BooleanVar(value=stroke_enabled)
        tk.Checkbutton(text_left_col, text="Outline Text", variable=stroke_var, command=toggle_stroke).pack(pady=3)
        
        # Text position and opacity sliders
        tk.Label(text_right_col, text="Text Opacity", font=("Arial", 10, "bold")).pack()
        op_slider = tk.Scale(text_right_col, from_=0, to=255, orient="horizontal", length=200, command=update_opacity)
        op_slider.set(opacity)
        op_slider.pack(pady=2)
        
        tk.Label(text_right_col, text="Text Position X", font=("Arial", 10, "bold")).pack()
        x_slider = tk.Scale(text_right_col, from_=0, to=3000, orient="horizontal", length=200, command=update_position_x)
        x_slider.set(position_offset[0])
        x_slider.pack(pady=2)
        
        tk.Label(text_right_col, text="Text Position Y", font=("Arial", 10, "bold")).pack()
        y_slider = tk.Scale(text_right_col, from_=0, to=3000, orient="horizontal", length=200, command=update_position_y)
        y_slider.set(position_offset[1])
        y_slider.pack(pady=2)
        
        # === IMAGE WATERMARK TAB ===
        image_left_col = tk.Frame(image_frame)
        image_right_col = tk.Frame(image_frame)
        image_left_col.pack(side=tk.LEFT, padx=10, pady=10, anchor="n")
        image_right_col.pack(side=tk.LEFT, padx=10, pady=10, anchor="n")
        
        # Image selection
        tk.Label(image_left_col, text="Image Watermark:", font=("Arial", 10, "bold")).pack(anchor="w")
        image_label = tk.Label(image_left_col, text="No image selected", fg="gray", wraplength=200)
        image_label.pack(pady=5)
        
        button_frame = tk.Frame(image_left_col)
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="📁 Browse Image", command=pick_image, width=15).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="❌ Clear", command=clear_image, width=8).pack(side=tk.LEFT, padx=2)
        
        # Image controls
        tk.Label(image_right_col, text="Image Opacity", font=("Arial", 10, "bold")).pack()
        img_op_slider = tk.Scale(image_right_col, from_=0, to=255, orient="horizontal", length=200, command=update_image_opacity)
        img_op_slider.set(image_opacity)
        img_op_slider.pack(pady=2)
        
        tk.Label(image_right_col, text="Image Size", font=("Arial", 10, "bold")).pack()
        size_slider = tk.Scale(image_right_col, from_=50, to=1000, orient="horizontal", length=200, command=update_image_size)
        size_slider.set(image_size)
        size_slider.pack(pady=2)
        
        tk.Label(image_right_col, text="Image Position X", font=("Arial", 10, "bold")).pack()
        img_x_slider = tk.Scale(image_right_col, from_=0, to=3000, orient="horizontal", length=200, command=update_image_position_x)
        img_x_slider.set(image_position_offset[0])
        img_x_slider.pack(pady=2)
        
        tk.Label(image_right_col, text="Image Position Y", font=("Arial", 10, "bold")).pack()
        img_y_slider = tk.Scale(image_right_col, from_=0, to=3000, orient="horizontal", length=200, command=update_image_position_y)
        img_y_slider.set(image_position_offset[1])
        img_y_slider.pack(pady=2)
        
        # === SETTINGS TAB ===
        settings_col = tk.Frame(settings_frame)
        settings_col.pack(padx=20, pady=20)
        
        tk.Label(settings_col, text="Watermark Type:", font=("Arial", 12, "bold")).pack(anchor="w", pady=5)
        
        watermark_type_var = tk.StringVar(value=watermark_type)
        tk.Radiobutton(settings_col, text="Text Only", variable=watermark_type_var, value="text", command=toggle_watermark_type).pack(anchor="w", pady=2)
        tk.Radiobutton(settings_col, text="Image Only", variable=watermark_type_var, value="image", command=toggle_watermark_type).pack(anchor="w", pady=2)
        tk.Radiobutton(settings_col, text="Both Text and Image", variable=watermark_type_var, value="both", command=toggle_watermark_type).pack(anchor="w", pady=2)
        
        # Update image label if image is already selected
        if watermark_image_path:
            image_label.config(text=f"Image: {os.path.basename(watermark_image_path)}")

    def add_watermark(self, base):
        """watermark function supporting both text and image watermarks"""
        try:
            base = base.convert("RGBA")
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            
            # Add text watermark
            if watermark_type in ["text", "both"] and watermark_text:
                overlay = self.add_text_watermark(overlay)
            
            # Add image watermark
            if watermark_type in ["image", "both"] and watermark_image_path:
                overlay = self.add_image_watermark(overlay)
            
            # Composite the overlay onto the base image
            result = Image.alpha_composite(base, overlay)
            return result.convert("RGB")
        except Exception as e:
            print(f"Watermark error: {e}")
            return base.convert("RGB")

    def add_text_watermark(self, overlay):
        """Add text watermark to overlay"""
        try:
            watermark_font = ImageFont.truetype(text_settings["font_path"], 110)
        except:
            watermark_font = ImageFont.load_default()
        
        wm_x, wm_y = position_offset
        draw_overlay = ImageDraw.Draw(overlay)
        
        # Add stroke if enabled
        if stroke_enabled:
            stroke_fill = (0, 0, 0, opacity)
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                draw_overlay.text((wm_x + dx, wm_y + dy), watermark_text, font=watermark_font, fill=stroke_fill)
        
        # Add main text
        fill_with_opacity = (*text_color[:3], opacity)
        draw_overlay.text((wm_x, wm_y), watermark_text, font=watermark_font, fill=fill_with_opacity)
        
        return overlay

    def add_image_watermark(self, overlay):
        """Add image watermark to overlay"""
        try:
            # Load the watermark image
            watermark_img = Image.open(watermark_image_path)
            
            # Convert to RGBA if not already
            if watermark_img.mode != "RGBA":
                watermark_img = watermark_img.convert("RGBA")
            
            # Resize the watermark image
            original_size = watermark_img.size
            aspect_ratio = original_size[1] / original_size[0]
            new_width = image_size
            new_height = int(new_width * aspect_ratio)
            watermark_img = watermark_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Apply opacity to the watermark image
            if image_opacity < 255:
                # Create a new image with the same size but with adjusted alpha
                watermark_with_opacity = Image.new("RGBA", watermark_img.size, (0, 0, 0, 0))
                
                # Get the alpha channel
                r, g, b, a = watermark_img.split()
                
                # Adjust alpha channel based on opacity setting
                a = a.point(lambda p: int(p * (image_opacity / 255.0)))
                
                # Recombine channels
                watermark_with_opacity = Image.merge("RGBA", (r, g, b, a))
                watermark_img = watermark_with_opacity
            
            # Position the watermark
            wm_x, wm_y = image_position_offset
            
            # Ensure the watermark fits within the image bounds
            if wm_x + watermark_img.width > overlay.width:
                wm_x = overlay.width - watermark_img.width
            if wm_y + watermark_img.height > overlay.height:
                wm_y = overlay.height - watermark_img.height
            if wm_x < 0:
                wm_x = 0
            if wm_y < 0:
                wm_y = 0
            
            # Paste the watermark onto the overlay
            overlay.paste(watermark_img, (wm_x, wm_y), watermark_img)
            
        except Exception as e:
            print(f"Image watermark error: {e}")
        
        return overlay

    # =========================== Text settings (keeping existing functionality) ===========================
    def build_text_controls(self, frame):
        def pick_font():
            path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
            if path:
                text_settings["font_path"] = path
                self.draw_template()
        
        def pick_text_color():
            color = colorchooser.askcolor(title="Pilih Warna Teks")
            if color[1]:
                text_settings["text_color"] = color[1]
                self.draw_template()
        
        def pick_box_color():
            color = colorchooser.askcolor(title="Pilih Warna Kotak Teks")
            if color[1]:
                text_settings["box_color"] = color[1]
                self.draw_template()
        
        def update_style(val):
            text_settings["box_style"] = val
            self.draw_template()
        
        def toggle_stroke():
            text_settings["text_stroke"] = stroke_var.get()
            self.draw_template()
        
        def update_x(val):
            text_settings["offset_x"] = int(val)
            self.draw_template()
        
        def update_y(val):
            text_settings["offset_y"] = int(val)
            self.draw_template()
        
        def update_w(val):
            text_settings["box_width"] = int(val)
            self.draw_template()
        
        def update_h(val):
            text_settings["box_height"] = int(val)
            self.draw_template()
        
        # Master row
        row = tk.Frame(frame)
        row.pack(pady=5)
        
        # === COL 1: Font & Color Buttons (Very Left) ===
        col1 = tk.Frame(row)
        col1.pack(side=tk.LEFT, padx=4)
        tk.Button(col1, text="📁 Ganti Font", command=pick_font).pack(pady=2)
        tk.Button(col1, text="🎨 Warna Teks", command=pick_text_color).pack(pady=2)
        tk.Button(col1, text="🖼 Warna Kotak", command=pick_box_color).pack(pady=2)
        
        # === COL 2: Stroke & Box Style ===
        col2 = tk.Frame(row)
        col2.pack(side=tk.LEFT, padx=4)
        stroke_var = tk.BooleanVar(value=text_settings["text_stroke"])
        tk.Checkbutton(col2, text="Outline Text", variable=stroke_var, command=toggle_stroke).pack(pady=2)
        
        tk.Label(col2, text="Bentuk Kotak").pack()
        box_var = tk.StringVar(value=text_settings["box_style"])
        for opt in ["rounded", "rectangle", "dashed"]:
            tk.Radiobutton(col2, text=opt.capitalize(), variable=box_var, value=opt,
                           command=lambda: update_style(box_var.get())).pack(anchor="w")
        
        # === COL 3: Posisi Sliders ===
        col3 = tk.Frame(row)
        col3.pack(side=tk.LEFT, padx=4)
        tk.Label(col3, text="Posisi X").pack()
        x_scale = tk.Scale(col3, from_=0, to=1500, orient="horizontal", length=130, command=update_x)
        x_scale.set(text_settings["offset_x"])
        x_scale.pack()
        
        tk.Label(col3, text="Posisi Y").pack()
        y_scale = tk.Scale(col3, from_=0, to=2700, orient="horizontal", length=130, command=update_y)
        y_scale.set(text_settings["offset_y"])
        y_scale.pack()
        
        # === COL 4: Size Sliders ===
        col4 = tk.Frame(row)
        col4.pack(side=tk.LEFT, padx=4)
        tk.Label(col4, text="Lebar Kotak").pack()
        w_scale = tk.Scale(col4, from_=300, to=3000, orient="horizontal", length=130, command=update_w)
        w_scale.set(text_settings["box_width"])
        w_scale.pack()
        
        tk.Label(col4, text="Tinggi Kotak").pack()
        h_scale = tk.Scale(col4, from_=100, to=1500, orient="horizontal", length=130, command=update_h)
        h_scale.set(text_settings["box_height"])
        h_scale.pack()

    def wrap_text(self, text, font, max_width):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if font.getlength(test_line) <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def render_text(self, draw, box, text, font_path=None):
        font_path = font_path or text_settings["font_path"]
        left_margin = 75
        right_margin = 75
        top_margin = 30
        bottom_margin = 45
        text_area_width = box[2] - box[0] - left_margin - right_margin
        text_area_height = box[3] - box[1] - top_margin - bottom_margin
        
        max_font_size = 135
        min_font_size = 18
        
        for font_size in range(max_font_size, min_font_size - 1, -2):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            lines = self.wrap_text(text, font, text_area_width)
            total_height = sum(font.getbbox(line)[3] - font.getbbox(line)[1] + 15 for line in lines)
            
            if total_height <= text_area_height:
                break
        
        y = box[1] + top_margin + (text_area_height - total_height) // 2
        
        for line in lines:
            line_width = font.getlength(line)
            x = box[0] + left_margin + (text_area_width - line_width) // 2
            
            if text_settings["text_stroke"]:
                for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                    draw.text((x + dx, y + dy), line, font=font, fill="black")
            
            draw.text((x, y), line, font=font, fill=text_settings["text_color"])
            y += font.getbbox(line)[3] - font.getbbox(line)[1] + 15

    def draw_textbox_shape(self, draw, _):
        x, y = text_settings["offset_x"], text_settings["offset_y"]
        w, h = text_settings["box_width"], text_settings["box_height"]
        box = (x, y, x + w, y + h)
        style = text_settings["box_style"]
        fill = text_settings["box_color"]
        
        if style == "rounded":
            draw.rounded_rectangle(box, radius=120, fill=fill, outline="black", width=9)
        elif style == "rectangle":
            draw.rectangle(box, fill=fill, outline="black", width=9)
        elif style == "dashed":
            for i in range(box[0], box[2], 40):
                draw.line([(i, box[1]), (i + 20, box[1])], fill="black", width=9)
                draw.line([(i, box[3]), (i + 20, box[3])], fill="black", width=9)
            for i in range(box[1], box[3], 40):
                draw.line([(box[0], i), (box[0], i + 20)], fill="black", width=9)
                draw.line([(box[2], i), (box[2], i + 20)], fill="black", width=9)
            draw.rectangle(box, fill=fill)

    # =========================== Text settings ===========================
    def build_text_controls(self, frame):
        def pick_font():
            path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
            if path:
                text_settings["font_path"] = path
                self.draw_template()

        def pick_text_color():
            color = colorchooser.askcolor(title="Pilih Warna Teks")
            if color[1]:
                text_settings["text_color"] = color[1]
                self.draw_template()

        def pick_box_color():
            color = colorchooser.askcolor(title="Pilih Warna Kotak Teks")
            if color[1]:
                text_settings["box_color"] = color[1]
                self.draw_template()

        def update_style(val):
            text_settings["box_style"] = val
            self.draw_template()

        def toggle_stroke():
            text_settings["text_stroke"] = stroke_var.get()
            self.draw_template()

        def update_x(val):
            text_settings["offset_x"] = int(val)
            self.draw_template()

        def update_y(val):
            text_settings["offset_y"] = int(val)
            self.draw_template()

        def update_w(val):
            text_settings["box_width"] = int(val)
            self.draw_template()

        def update_h(val):
            text_settings["box_height"] = int(val)
            self.draw_template()

        # Master row
        row = tk.Frame(frame)
        row.pack(pady=5)

        # === COL 1: Font & Color Buttons (Very Left) ===
        col1 = tk.Frame(row)
        col1.pack(side=tk.LEFT, padx=4)
        tk.Button(col1, text="📁 Ganti Font", command=pick_font).pack(pady=2)
        tk.Button(col1, text="🎨 Warna Teks", command=pick_text_color).pack(pady=2)
        tk.Button(col1, text="🖼 Warna Kotak", command=pick_box_color).pack(pady=2)

        # === COL 2: Stroke & Box Style ===
        col2 = tk.Frame(row)
        col2.pack(side=tk.LEFT, padx=4)
        stroke_var = tk.BooleanVar(value=text_settings["text_stroke"])
        tk.Checkbutton(col2, text="Outline Text", variable=stroke_var, command=toggle_stroke).pack(pady=2)

        tk.Label(col2, text="Bentuk Kotak").pack()
        box_var = tk.StringVar(value=text_settings["box_style"])
        for opt in ["rounded", "rectangle", "dashed"]:
            tk.Radiobutton(col2, text=opt.capitalize(), variable=box_var, value=opt,
                           command=lambda: update_style(box_var.get())).pack(anchor="w")

        # === COL 3: Posisi Sliders ===
        col3 = tk.Frame(row)
        col3.pack(side=tk.LEFT, padx=4)
        tk.Label(col3, text="Posisi X").pack()
        tk.Scale(col3, from_=0, to=1500, orient="horizontal", length=130, command=update_x).pack()
        tk.Label(col3, text="Posisi Y").pack()
        tk.Scale(col3, from_=0, to=2700, orient="horizontal", length=130, command=update_y).pack()

        # === COL 4: Size Sliders ===
        col4 = tk.Frame(row)
        col4.pack(side=tk.LEFT, padx=4)
        tk.Label(col4, text="Lebar Kotak").pack()
        tk.Scale(col4, from_=300, to=3000, orient="horizontal", length=130, command=update_w).pack()
        tk.Label(col4, text="Tinggi Kotak").pack()
        tk.Scale(col4, from_=100, to=1500, orient="horizontal", length=130, command=update_h).pack()

    def wrap_text(self, text, font, max_width):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if font.getlength(test_line) <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def render_text(self, draw, box, text, font_path=None):
        font_path = font_path or text_settings["font_path"]
        left_margin = 75
        right_margin = 75
        top_margin = 30
        bottom_margin = 45

        text_area_width = box[2] - box[0] - left_margin - right_margin
        text_area_height = box[3] - box[1] - top_margin - bottom_margin

        max_font_size = 135
        min_font_size = 18

        for font_size in range(max_font_size, min_font_size - 1, -2):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            lines = self.wrap_text(text, font, text_area_width)
            total_height = sum(font.getbbox(line)[3] - font.getbbox(line)[1] + 15 for line in lines)
            if total_height <= text_area_height:
                break

        y = box[1] + top_margin + (text_area_height - total_height) // 2
        for line in lines:
            line_width = font.getlength(line)
            x = box[0] + left_margin + (text_area_width - line_width) // 2
            if text_settings["text_stroke"]:
                for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                    draw.text((x + dx, y + dy), line, font=font, fill="black")
            draw.text((x, y), line, font=font, fill=text_settings["text_color"])
            y += font.getbbox(line)[3] - font.getbbox(line)[1] + 15

    def draw_textbox_shape(self, draw, _):
        x, y = text_settings["offset_x"], text_settings["offset_y"]
        w, h = text_settings["box_width"], text_settings["box_height"]
        box = (x, y, x + w, y + h)
        style = text_settings["box_style"]
        fill = text_settings["box_color"]

        if style == "rounded":
            draw.rounded_rectangle(box, radius=120, fill=fill, outline="black", width=9)
        elif style == "rectangle":
            draw.rectangle(box, fill=fill, outline="black", width=9)
        elif style == "dashed":
            for i in range(box[0], box[2], 40):
                draw.line([(i, box[1]), (i + 20, box[1])], fill="black", width=9)
                draw.line([(i, box[3]), (i + 20, box[3])], fill="black", width=9)
            for i in range(box[1], box[3], 40):
                draw.line([(box[0], i), (box[0], i + 20)], fill="black", width=9)
                draw.line([(box[2], i), (box[2], i + 20)], fill="black", width=9)
            draw.rectangle(box, fill=fill)
       
    # =========================== Context Menu Registry Tab ===========================
    def build_context_menu_controls(self, frame):
        def refresh_script_list():
            # This function now just displays the manually added files
            pass
        
        def choose_file():
            """Choose individual .py or .exe files"""
            filetypes = [
                ("Python and Executable files", "*.py;*.exe"),
                ("Python files", "*.py"),
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ]
            files = filedialog.askopenfilenames(
                title="Select Python or Executable files",
                filetypes=filetypes
            )
            if files:
                for file_path in files:
                    # Check if file is already in the list
                    items = script_list.get(0, tk.END)
                    if file_path not in items:
                        script_list.insert(tk.END, file_path)
        
        def browse_directory():
            """Browse directory and automatically find .py and .exe files"""
            directory = filedialog.askdirectory(title="Select Directory to Search for .py and .exe files")
            if directory:
                found_files = []
                # Search for .py and .exe files in the selected directory
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.endswith(('.py', '.exe')):
                            file_path = os.path.join(root, file)
                            found_files.append(file_path)
                
                if found_files:
                    # Add found files to the list (avoiding duplicates)
                    existing_items = script_list.get(0, tk.END)
                    added_count = 0
                    for file_path in found_files:
                        if file_path not in existing_items:
                            script_list.insert(tk.END, file_path)
                            added_count += 1
                    
                    if added_count > 0:
                        messagebox.showinfo("Files Found", f"Added {added_count} new files to the list.")
                    else:
                        messagebox.showinfo("Files Found", "All found files were already in the list.")
                else:
                    messagebox.showinfo("No Files Found", "No .py or .exe files found in the selected directory.")
        
        def remove_selected_file():
            """Remove selected file from the list"""
            selection = script_list.curselection()
            if selection:
                for idx in reversed(selection):  # Remove from end to avoid index shifting
                    script_list.delete(idx)
            else:
                messagebox.showwarning("No Selection", "Please select a file to remove.")
        
        def clear_file_list():
            """Clear all files from the list"""
            if script_list.size() > 0:
                if messagebox.askyesno("Clear List", "Remove all files from the list?"):
                    script_list.delete(0, tk.END)
        
        def add_registry_subcommand():
            idx = script_list.curselection()
            if not idx:
                messagebox.showwarning("Select Script", "Please select a script file from the list.")
                return
            script_path = script_list.get(idx[0])
            script_name = os.path.splitext(os.path.basename(script_path))[0]
            pc_username = getpass.getuser()
            
            # Determine the appropriate executable based on file extension
            file_ext = os.path.splitext(script_path)[1].lower()
            if file_ext == '.py':
                python_exe = f"C:\\Users\\{pc_username}\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"
                pythonw_exe = f"C:\\Users\\{pc_username}\\AppData\\Local\\Programs\\Python\\Python311\\pythonw.exe"
                executor = python_exe
                icon = pythonw_exe
            elif file_ext == '.exe':
                executor = f"\"{script_path}\""
                icon = script_path
            else:
                messagebox.showerror("Unsupported File", "Only .py and .exe files are supported.")
                return
            
            # Add to Directory context menu
            key_base = r"Directory\shell\GenerateAllPosters\shell"
            subkey = f"GenerateAllPosters-{script_name}"
            command_key = f"{subkey}\\command"
            try:
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{key_base}\\{subkey}") as k:
                    winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, script_name)
                    winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{key_base}\\{command_key}") as cmd_k:
                    if file_ext == '.py':
                        winreg.SetValueEx(cmd_k, "", 0, winreg.REG_SZ, f"\"{executor}\" \"{script_path}\" \"%1\"")
                    else:  # .exe
                        winreg.SetValueEx(cmd_k, "", 0, winreg.REG_SZ, f"{executor} \"%1\"")
                
                # Add to .jpg context menu
                jpg_base = r"SystemFileAssociations\.jpg\Shell\GeneratePoster\shell"
                jpg_subkey = f"GeneratePoster-{script_name}"
                jpg_command_key = f"{jpg_subkey}\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{jpg_base}\\{jpg_subkey}") as k:
                    winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, f"Generate Poster-{script_name}")
                    winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{jpg_base}\\{jpg_command_key}") as cmd_k:
                    if file_ext == '.py':
                        winreg.SetValueEx(cmd_k, "", 0, winreg.REG_SZ, f"\"{executor}\" \"{script_path}\" \"%1\"")
                    else:  # .exe
                        winreg.SetValueEx(cmd_k, "", 0, winreg.REG_SZ, f"{executor} \"%1\"")
                
                messagebox.showinfo("Registry Updated", f"Context menu added for {script_name}.")
                refresh_registry_list()
            except Exception as e:
                messagebox.showerror("Registry Error", str(e))
        
        def refresh_registry_list():
            registry_entries.delete(0, tk.END)
            # Directory context menu
            key_base = r"Directory\shell\GenerateAllPosters\shell"
            jpg_base = r"SystemFileAssociations\.jpg\Shell\GeneratePoster\shell"
            for base, prefix in [(key_base, "GenerateAllPosters-"), (jpg_base, "GeneratePoster-")]:
                try:
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, base) as k:
                        idx = 0
                        while True:
                            try:
                                sub = winreg.EnumKey(k, idx)
                                if sub.startswith(prefix):
                                    registry_entries.insert(tk.END, f"{base}\\{sub}")
                                idx += 1
                            except OSError:
                                break
                except Exception:
                    continue
        
        def delete_selected_registry():
            idx = registry_entries.curselection()
            if not idx:
                messagebox.showwarning("Select Entry", "Please select a registry entry to delete.")
                return
            key_path = registry_entries.get(idx[0])
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{key_path}\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
                messagebox.showinfo("Registry Deleted", f"Deleted registry entry:\n{key_path}")
                refresh_registry_list()
            except Exception as e:
                messagebox.showerror("Registry Error", str(e))
        
        def clear_all_registry():
            if not messagebox.askyesno("Confirmation", "Clear ALL registry keys related to this context menu?\nThis cannot be undone!"):
                return
            for base in [r"Directory\shell\GenerateAllPosters\shell", r"SystemFileAssociations\.jpg\Shell\GeneratePoster\shell"]:
                try:
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, base) as k:
                        idx = 0
                        subs = []
                        while True:
                            try:
                                sub = winreg.EnumKey(k, idx)
                                subs.append(sub)
                                idx += 1
                            except OSError:
                                break
                        for sub in subs:
                            try:
                                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{base}\\{sub}\\command")
                            except Exception:
                                pass
                            try:
                                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{base}\\{sub}")
                            except Exception:
                                pass
                except Exception:
                    pass
            messagebox.showinfo("Registry Cleared", "All related registry keys cleared.")
            refresh_registry_list()
        
        # UI layout - to support both individual file selection and directory browsing
        row_top = tk.Frame(frame)
        row_top.pack(fill=tk.X, pady=2)
        tk.Label(row_top, text="Selected Files:").pack(side=tk.LEFT)
        
        # File management buttons
        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=2)
        tk.Button(button_frame, text="Add Files (.py/.exe)", command=choose_file).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Browse Directory", command=browse_directory).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Remove Selected", command=remove_selected_file).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Clear All", command=clear_file_list).pack(side=tk.LEFT, padx=2)
        
        # File list with scrollbar
        list_frame = tk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        script_list = tk.Listbox(list_frame, width=80, height=6, selectmode=tk.EXTENDED)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=script_list.yview)
        script_list.configure(yscrollcommand=scrollbar.set)
        
        script_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Button(frame, text="Add Selected Script to Context Menu", command=add_registry_subcommand).pack(pady=2)
        tk.Label(frame, text="Registry Subcommands:").pack(pady=2)
        
        # Registry entries list with scrollbar
        registry_frame = tk.Frame(frame)
        registry_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        registry_entries = tk.Listbox(registry_frame, width=80, height=6)
        registry_scrollbar = tk.Scrollbar(registry_frame, orient=tk.VERTICAL, command=registry_entries.yview)
        registry_entries.configure(yscrollcommand=registry_scrollbar.set)
        
        registry_entries.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        registry_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Button(frame, text="Delete Selected Registry Entry", command=delete_selected_registry).pack(pady=2)
        tk.Button(frame, text="Clear ALL Registry Entries", command=clear_all_registry).pack(pady=2)
        refresh_registry_list()
        
         # CLI Support
def process_image_gui(image_path):
    root = tk.Tk()
    app = ImageTextComposer(root)
    app.top_image_path = image_path
    extracted_text = app.extract_text_from_exif(image_path)
    app.text_box.insert("1.0", extracted_text)
    app.draw_template()
    root.mainloop()

def process_image(image_path):
    root = tk.Tk()
    root.withdraw()
    app = ImageTextComposer(root)
    app.top_image_path = image_path
    extracted_text = app.extract_text_from_exif(image_path)
    app.text_box.insert("1.0", extracted_text)
    app.draw_template()
    filename = os.path.splitext(os.path.basename(image_path))[0]
    output_path = os.path.join(os.path.dirname(image_path), f"{filename}-1.jpg")
    app.last_image.save(output_path, "JPEG", quality=95)
    print(f"✔ Saved: {output_path}")
    root.destroy()

def process_folder_recursively(folder_path):
    jpg_files = glob.glob(os.path.join(folder_path, "**", "*.jpg"), recursive=True)
    for img_path in jpg_files:
        try:
            process_image(img_path)
        except Exception as e:
            print(f"❌ Error processing {img_path}: {e}") 

if __name__ == "__main__":
    if len(sys.argv) == 1:
        root = tk.Tk()
        root.title("Image + Text Composer (Resizable)")
        root.geometry("1100x800")  # Wider default window
        root.minsize(900, 700) 
        app = ImageTextComposer(root)
        root.mainloop()
    elif len(sys.argv) == 2:
        input_path = sys.argv[1]
        if os.path.isdir(input_path):
            process_folder_recursively(input_path)
        elif os.path.isfile(input_path):
            process_image(input_path)
        else:
            print("❌ Invalid path provided.")
    elif len(sys.argv) == 3 and sys.argv[1] == "--gui":
        process_image_gui(sys.argv[2])
