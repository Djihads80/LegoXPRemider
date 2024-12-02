import subprocess
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, Scale
from tkinter.filedialog import askopenfilename
import threading
import time
import sounddevice as sd
import soundfile as sf
from shutil import copyfile
from PIL import Image, ImageTk  # For handling images

# Function to install a package if not already installed
def install_package(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure required packages are installed
install_package("sounddevice")
install_package("soundfile")
install_package("pillow")

# Path to the Assets folder
ASSETS_DIR = os.path.join(os.getcwd(), "Assets")

# Ensure the Assets folder exists
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

class LegoXPReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LegoXPReminder")
        self.root.geometry("500x400")
        self.root.minsize(500, 400)

        self.selected_device = tk.StringVar()
        self.selected_sound = tk.StringVar()
        self.timer_interval = tk.DoubleVar(value=10)
        self.volume_level = tk.IntVar(value=100)

        self.play_thread = None
        self.is_running = False

        # Set application icon
        self.set_app_icon()

        # Create UI
        self.create_ui()

        # Attach banana image to bottom-right
        self.root.bind("<Configure>", self.update_banana_position)

    def set_app_icon(self):
        try:
            icon_path = os.path.join(os.getcwd(), "logo.png")
            self.root.iconphoto(True, ImageTk.PhotoImage(file=icon_path))
        except Exception as e:
            print(f"Error setting app icon: {e}")

    def create_ui(self):
        # Reminder time input
        reminder_frame = tk.Frame(self.root)
        reminder_frame.pack(pady=5, anchor="w")
        ttk.Label(reminder_frame, text="Reminder Time:").pack(side="left", padx=5)
        ttk.Entry(reminder_frame, textvariable=self.timer_interval, width=10).pack(side="left", padx=5)

        # Volume layout
        volume_frame = tk.Frame(self.root)
        volume_frame.pack(pady=5, anchor="w", fill="x")
        ttk.Label(volume_frame, text="Volume:").grid(row=0, column=0, padx=5, sticky="w")
        self.volume_slider = Scale(volume_frame, from_=0, to=150, orient="horizontal", variable=self.volume_level)
        self.volume_slider.grid(row=1, column=0, padx=5, sticky="w")
        self.volume_entry = ttk.Entry(volume_frame, textvariable=self.volume_level, width=5)
        self.volume_entry.grid(row=1, column=1, padx=5, sticky="e")
        self.volume_level.trace_add("write", self.update_volume_entry)

        # Sound selection dropdown
        sound_frame = tk.Frame(self.root)
        sound_frame.pack(pady=5, anchor="w")
        ttk.Label(sound_frame, text="Sound:").pack(side="left", padx=5)
        self.sound_dropdown = ttk.OptionMenu(sound_frame, self.selected_sound, "")
        self.sound_dropdown.pack(side="left", padx=5)
        ttk.Button(sound_frame, text="Add Custom", command=self.add_custom_sound).pack(side="left", padx=5)
        self.update_sounds_dropdown()

        # Audio output device dropdown
        device_frame = tk.Frame(self.root)
        device_frame.pack(pady=5, anchor="w")
        ttk.Label(device_frame, text="Audio Output Device:").pack(side="left", padx=5)
        self.device_dropdown = ttk.OptionMenu(device_frame, self.selected_device, *self.get_audio_devices())
        self.device_dropdown.pack(side="left", padx=5)

        # Start/Stop button
        self.start_button = ttk.Button(self.root, text="Start", command=self.start_timer)
        self.start_button.pack(pady=10)

        # Banana character at bottom-right
        self.add_banana_character()

    def add_banana_character(self):
        try:
            banana_image_path =  os.path.join(os.getcwd(), "banana.png")
            banana_img = Image.open(banana_image_path).resize((70, 70), Image.LANCZOS)  # Slightly larger size
            self.banana_photo = ImageTk.PhotoImage(banana_img)
            self.banana_label = tk.Label(self.root, image=self.banana_photo, bd=0)
            self.banana_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)  # Offset from corner
        except Exception as e:
            print(f"Error loading banana image: {e}")

    def update_banana_position(self, event=None):
        # Dynamically reposition the banana when the window resizes
        self.banana_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    def get_audio_devices(self):
        try:
            devices = sd.query_devices()
            output_devices = [device["name"] for device in devices if device["max_output_channels"] > 0]
            return list(dict.fromkeys(output_devices))  # Remove duplicates
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get audio devices: {e}")
            return []

    def get_sounds(self):
        try:
            return [f for f in os.listdir(ASSETS_DIR) if f.endswith((".mp3", ".wav"))]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sounds: {e}")
            return []

    def update_sounds_dropdown(self):
        sounds = self.get_sounds()
        if sounds:
            self.selected_sound.set(sounds[0])

        # Clear the old dropdown menu
        menu = self.sound_dropdown["menu"]
        menu.delete(0, "end")

        # Populate dropdown with new options
        for sound in sounds:
            menu.add_command(label=sound, command=lambda value=sound: self.selected_sound.set(value))

    def add_custom_sound(self):
        file_path = askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if file_path:
            try:
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(ASSETS_DIR, file_name)
                copyfile(file_path, dest_path)
                self.update_sounds_dropdown()
                messagebox.showinfo("Success", f"Added {file_name} to Assets.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add sound: {e}")

    def update_volume_entry(self, *args):
        # Get the volume level and ensure it is valid
        try:
            volume_value = str(self.volume_level.get())
            self.volume_entry.delete(0, tk.END)  # Clear the entry field first
            self.volume_entry.insert(0, volume_value)  # Insert the updated value
        except Exception as e:
            # If an error occurs (like invalid value), set to a default value
            self.volume_entry.delete(0, tk.END)
            self.volume_entry.insert(0, "100")  # Default volume level if something goes wrong
            print(f"Error updating volume entry: {e}")

    def play_sound(self):
        sound_file = os.path.join(ASSETS_DIR, self.selected_sound.get())
        try:
            device_index = self.get_selected_device_index()
            if device_index is not None:
                data, samplerate = sf.read(sound_file)
                volume_factor = self.volume_level.get() / 100
                data = data * volume_factor  # Adjust volume
                sd.play(data, samplerate=samplerate, device=device_index)
                sd.wait()
            else:
                messagebox.showerror("Error", "No valid audio output device selected.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play sound: {e}")

    def get_selected_device_index(self):
        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if device["name"] == self.selected_device.get():
                return index
        return None

    def timer_loop(self):
        while self.is_running:
            time.sleep(self.timer_interval.get() * 60)
            if self.is_running:
                self.play_sound()

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.start_button.config(text="Stop", command=self.stop_timer)
            self.play_thread = threading.Thread(target=self.timer_loop, daemon=True)
            self.play_thread.start()
        else:
            self.stop_timer()

    def stop_timer(self):
        self.is_running = False
        sd.stop()
        self.start_button.config(text="Start", command=self.start_timer)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = LegoXPReminderApp(root)
        root.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Press Enter to exit.")
        input()
