import os
import json
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog, PhotoImage
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pystray
from pystray import MenuItem as item, Icon
from PIL import Image, ImageDraw, ImageTk
import winreg

CONFIG_PATH = "config.json"
LOGO_PATH = "data/logo.png"


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    else:
        config = {
            "watch_folder": "",
            "rules": {".mp3": "Music", ".jpg": "Images", ".txt": "Documents"},
            "start_with_system": False,
            "show_window_on_start": True,  # Default value for this key
            "version": "1.0.0",
        }
        save_config(config)  # Save the initial configuration with the key
    return config


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


def handle_startup():
    if config["start_with_system"]:
        add_to_startup()
    if config["show_window_on_start"]:
        app.deiconify()
    else:
        app.withdraw()


def add_to_startup():
    key = winreg.HKEY_CURRENT_USER
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "XFolder"
    value = f'"{os.path.abspath(__file__)}"'

    with winreg.OpenKey(key, reg_path, 0, winreg.KEY_WRITE) as registry_key:
        winreg.SetValueEx(registry_key, value_name, 0, winreg.REG_SZ, value)


class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            self.organize_file(event.src_path)

    def organize_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        folder = config["rules"].get(ext)
        if folder:
            dest_folder = os.path.join(config["watch_folder"], folder)
            os.makedirs(dest_folder, exist_ok=True)
            shutil.move(
                file_path, os.path.join(dest_folder, os.path.basename(file_path))
            )
            app.log_event(f"Moved: {file_path} -> {dest_folder}")


class OrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"File Organizer - v{config['version']}")
        self.geometry("600x600")
        self.resizable(False, False)
        self.config(background="#1a1a1a")  # Dark background color
        self.iconbitmap("data/logo.png")
        if os.path.exists(LOGO_PATH):
            self.tk.call("wm", "iconphoto", self._w, PhotoImage(file=LOGO_PATH))

        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Set font to Consolas and use orange accent
        self.style = ctk.CTkFont(family="Consolas", size=12)
        self.accent_color = "#d18c24"  # Orange accent

        self.label = ctk.CTkLabel(
            self,
            text="Monitored Folder:",
            font=self.style,
            text_color=self.accent_color,
            bg_color="#1a1a1a",
        )
        self.label.pack(pady=5)

        self.path_var = ctk.StringVar(value=config["watch_folder"])
        self.path_entry = ctk.CTkEntry(
            self, textvariable=self.path_var, width=550, font=self.style
        )
        self.path_entry.pack(pady=5)

        self.browse_button = ctk.CTkButton(
            self,
            text="Select Folder",
            command=self.select_folder,
            font=self.style,
            fg_color=self.accent_color,
            hover_color="#a16b1a",
            bg_color="#1a1a1a",
        )
        self.browse_button.pack(pady=5)

        self.rules_button = ctk.CTkButton(
            self,
            text="Edit Rules",
            command=self.edit_rules,
            font=self.style,
            fg_color=self.accent_color,
            hover_color="#a16b1a",
            bg_color="#1a1a1a",
        )
        self.rules_button.pack(pady=5)

        self.start_with_system_switch = ctk.CTkSwitch(
            self,
            text="Start with system",
            command=self.toggle_startup,
            font=self.style,
            fg_color="#ad2323",
            progress_color="#53ad23",
            bg_color="#1a1a1a",
        )
        self.start_with_system_switch.pack(pady=5)
        (
            self.start_with_system_switch.select()
            if config["start_with_system"]
            else self.start_with_system_switch.deselect()
        )

        self.show_window_switch = ctk.CTkSwitch(
            self,
            text="Show window on startup",
            command=self.toggle_show_window,
            font=self.style,
            fg_color="#ad2323",
            progress_color="#53ad23",
            bg_color="#1a1a1a",
        )
        self.show_window_switch.pack(pady=5)
        (
            self.show_window_switch.select()
            if config.get("show_window_on_start", True)
            else self.show_window_switch.deselect()
        )

        # Increased size for the log console
        self.log_text = ctk.CTkTextbox(self, height=300, width=550, font=self.style)
        self.log_text.pack(pady=5)

        self.create_tray_icon()
        self.start_monitoring()

    def toggle_startup(self):
        config["start_with_system"] = self.start_with_system_switch.get()
        save_config(config)
        if config["start_with_system"]:
            add_to_startup()
        else:
            self.remove_from_startup()

    def toggle_show_window(self):
        config["show_window_on_start"] = self.show_window_switch.get()
        save_config(config)

    def remove_from_startup(self):
        key = winreg.HKEY_CURRENT_USER
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        value_name = "XFolder"
        try:
            with winreg.OpenKey(key, reg_path, 0, winreg.KEY_WRITE) as registry_key:
                winreg.DeleteValue(registry_key, value_name)
        except FileNotFoundError:
            pass

    def create_tray_icon(self):
        if os.path.exists(LOGO_PATH):
            image = Image.open(LOGO_PATH)
        else:
            image = Image.new("RGB", (64, 64), (255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle((16, 16, 48, 48), fill=(0, 0, 255))

        self.tray_icon = pystray.Icon(
            "XFolder",
            image,
            menu=pystray.Menu(
                item("Show", self.show_window), item("Exit", self.exit_app)
            ),
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()

    def exit_app(self):
        self.tray_icon.stop()
        self.observer.stop()
        self.observer.join()
        self.quit()

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            config["watch_folder"] = folder
            save_config(config)
            self.create_folders()
            self.log_event(f"Monitored folder set: {folder}")
            self.restart_monitoring()

    def create_folders(self):
        for folder in config["rules"].values():
            os.makedirs(os.path.join(config["watch_folder"], folder), exist_ok=True)

    def edit_rules(self):
        self.rules_window = ctk.CTkToplevel(self)
        self.rules_window.title("Edit Rules")
        self.rules_window.geometry("400x300")

        self.rules_list = ctk.CTkTextbox(self.rules_window, height=200)
        self.rules_list.pack(pady=5)

        self.rules_list.insert("end", json.dumps(config["rules"], indent=4))

        self.save_rules_button = ctk.CTkButton(
            self.rules_window, text="Save", command=self.save_rules, font=self.style
        )
        self.save_rules_button.pack(pady=5)

    def save_rules(self):
        try:
            new_rules = json.loads(self.rules_list.get("1.0", "end").strip())
            config["rules"] = new_rules
            save_config(config)
            self.log_event("Rules updated!")
            self.create_folders()
            self.rules_window.destroy()
        except json.JSONDecodeError:
            self.log_event("Error: Invalid format!")

    def log_event(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def start_monitoring(self):
        self.event_handler = FileHandler()
        self.observer = Observer()

        if config["watch_folder"] and os.path.isdir(config["watch_folder"]):
            self.observer.schedule(
                self.event_handler, config["watch_folder"], recursive=True
            )
            self.observer.start()
            self.log_event("Monitoring started...")
        else:
            self.log_event("Error: Invalid or non-existent monitored folder.")

    def restart_monitoring(self):
        if hasattr(self, "observer") and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        self.start_monitoring()


if __name__ == "__main__":
    config = load_config()
    app = OrganizerApp()
    handle_startup()  # Check behavior on startup
    app.mainloop()
