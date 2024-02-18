import subprocess
import json
import os
import sys
import re
import psutil
import tkinter as tk
from tkinter import ttk
from threading import Thread

SETTINGS_FILE = "mining_settings.json"

BACKGROUND_COLOR = "#121212"
TEXT_COLOR = "#FFFFFF"
BUTTON_COLOR = "#03DAC6"
INPUT_COLOR = "#000000"

STYLES = {
    "ClassicMonochrome": {"background": "#FFFFFF", "text": "#333333", "button": "#CCCCCC", "input": "#DDDDDD"},
    "OceanBreeze": {"background": "#86C5DA", "text": "#FFFFFF", "button": "#3E7CB1", "input": "#AAC9CE"},
    "SunsetHorizon": {"background": "#FFA07A", "text": "#FFFFFF", "button": "#FF5733", "input": "#FFCCBC"},
    "ForestCanopy": {"background": "#3C685E", "text": "#FFFFFF", "button": "#5AFF3D", "input": "#7FBCA6"},
    "RoyalPlum": {"background": "#94618E", "text": "#FFFFFF", "button": "#9932CC", "input": "#C5A3FF"},
    "GoldenHarvest": {"background": "#FFD700", "text": "#333333", "button": "#FFA500", "input": "#FFEC8B"},
    "MysticMoonlight": {"background": "#2C3E50", "text": "#FFFFFF", "button": "#7F8C8D", "input": "#34495E"},
    "VintageRose": {"background": "#F88379", "text": "#FFFFFF", "button": "#FFC0CB", "input": "#FFDAB9"},
    "PastelDream": {"background": "#F5EAD7", "text": "#333333", "button": "#F6DDCC", "input": "#EAE0D5"},
    "ElectricLime": {"background": "#BFFF00", "text": "#333333", "button": "#32CD32", "input": "#7FFF00"},
    "TropicalFiesta": {"background": "#FF6347", "text": "#FFFFFF", "button": "#FFD700", "input": "#FF8C00"},
    "GalacticNebula": {"background": "#483D8B", "text": "#FFFFFF", "button": "#9370DB", "input": "#B0E0E6"},
    "DarkMode": {"background": "#121212", "text": "#FFFFFF", "button": "#03DAC6", "input": "#000000"},
}

class MiningUI(tk.Tk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_style = tk.StringVar(value="DarkMode")
        self.labels = []
        self.entries = []
        self.start_button = None
        self.output_text = None
        self.cpu_info_label = None
        self.total_threads_label = None
        self.ccminer_process = None
        self.load_settings()
        self.apply_style()
        self.create_widgets()
        self.customization_window = None

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as file:
                self.settings = json.load(file)
        except FileNotFoundError:
            self.settings = {}

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as file:
            json.dump(self.settings, file)

    def apply_style(self):
        style_settings = STYLES.get(self.selected_style.get(), STYLES["ClassicMonochrome"])
        self.configure(background=style_settings["background"])
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TLabel', background=style_settings["background"], foreground=style_settings["text"], font=('Helvetica', 12))
        self.style.configure('TButton', background=style_settings["button"], foreground="#000000", font=('Helvetica', 12))
        self.style.configure('Custom.TEntry', background=style_settings["input"], foreground="#000000", font=('Helvetica', 12))

    def create_widgets(self):
        self.title("Crypto Mining Dashboard")
        label_texts = ['Algorithm:', 'Pool:', 'Wallet:', 'Name:', 'Password:', 'Threads:']
        for i, text in enumerate(label_texts):
            label = ttk.Label(self, text=text, anchor="e")
            label.grid(row=i, column=0, padx=10, pady=5, sticky='w')
            self.labels.append(label)

        for i, entry_name in enumerate(["algorithm", "pool", "wallet", "name", "password", "threads"]):
            entry = ttk.Entry(self, style='Custom.TEntry')
            entry.insert(0, self.settings.get(entry_name, ""))
            entry.grid(row=i, column=1, pady=5, padx=5, sticky='ew')
            self.entries.append(entry)

        self.start_button = ttk.Button(self, text="Start Mining", command=self.start_stop_mining)
        self.start_button.grid(row=6, column=1, pady=10, padx=5, sticky='ew')

        total_threads = psutil.cpu_count(logical=True)
        self.total_threads_label = ttk.Label(self, text=f"CPU Threads Available: {total_threads}")
        self.total_threads_label.grid(row=len(label_texts), column=0, columnspan=2, pady=(10, 205), padx=10, sticky='w')

        self.output_text = tk.Text(self, wrap=tk.WORD, width=90, height=35, background="#333333", foreground=TEXT_COLOR, font=('Courier New', 10))
        self.output_text.grid(row=0, column=2, rowspan=8, pady=5, padx=10, sticky='nsew')

        self.cpu_info_label = ttk.Label(self, text="")
        self.cpu_info_label.grid(row=8, column=2, pady=(5, 10), padx=10, sticky='ew')

        self.avg_hash_rate_label = ttk.Label(self, text="Average Hash Rate (last 10 jobs):")
        self.avg_hash_rate_label.grid(row=9, column=2, pady=3, padx=10, sticky='w')

        self.avg_hash_rate_value = ttk.Label(self, text="", style='Yellow.TLabel')
        self.avg_hash_rate_value.grid(row=9, column=2, pady=3, padx=250, sticky='w')

        self.style.configure('Yellow.TLabel', foreground='#FFFF00')
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        customize_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Customize", menu=customize_menu)

        for style_name in sorted(STYLES.keys()):
            customize_menu.add_radiobutton(label=style_name, variable=self.selected_style, value=style_name, command=self.apply_style)

    def start_stop_mining(self):
        if hasattr(self, 'ccminer_process') and self.ccminer_process:
            self.stop_mining()
        else:
            self.start_mining_thread()

    def start_mining_thread(self):
        if not self.ccminer_process:
            mining_thread = Thread(target=self.start_mining)
            mining_thread.start()

    def start_mining(self):
        ccminer_path = self.find_ccminer()
        if ccminer_path:
            self.settings = {entry_name: entry.get() for entry_name, entry in zip(["algorithm", "pool", "wallet", "name", "password", "threads"], self.entries)}
            self.save_settings()
            ccminer_command = f'"{ccminer_path}" -a {self.settings["algorithm"]} -o {self.settings["pool"]} -u {self.settings["wallet"]}.{self.settings["name"]} -p {self.settings["password"]} -t {self.settings["threads"]}'
            self.ccminer_process = subprocess.Popen(ccminer_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout_thread = Thread(target=self.read_stdout)
            stdout_thread.daemon = True
            stdout_thread.start()
        else:
            print("ccminer.exe not found in the script directory.")

    def stop_mining(self):
        if self.ccminer_process:
            self.ccminer_process.terminate()
            self.ccminer_process = None

    def read_stdout(self):
        boo_detected = False
        initial_message_detected = False
        accepted_jobs = []
        job_count = 0
        while True:
            line = self.ccminer_process.stdout.readline()
            if not line:
                break
            output_text = line.decode('utf-8').strip()

            output_text_clean = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', output_text)
            output_text_clean = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] ', '', output_text_clean)

            if output_text_clean.startswith("Error"):
                self.output_text.insert(tk.END, output_text_clean + '\n', "error")
            else:
                if not initial_message_detected:
                    if "Originally based on Christian Buchner and Christian H. project" in output_text_clean:
                        initial_message_detected = True
                        initial_message = (
                            output_text_clean + "\n"
                            "Adapted to Verus by Monkins\n"
                            "1010\n"
                            "UI created by 1800 👨‍💻💰💎\n"
                            "Goto https://wiki.verus.io/#!index.md for mining setup guides.\n\n"
                        )
                        self.output_text.insert(tk.END, initial_message)
                        self.output_text.tag_configure("white_text", foreground="#FFFFFF", font=('Courier New', 10, 'bold'))
                        self.output_text.tag_configure("green_text", foreground="#00FF00", font=('Consolas', 10, 'bold italic'))
                        self.output_text.tag_add("white_text", "1.0", "end-1c")
                        ui_start_index = self.output_text.search("UI created by 1800 👨‍💻💰💎", "1.0", stopindex=tk.END)
                        ui_end_index = f"{ui_start_index}+{len('UI created by 1800 👨‍💻💰💎')}c"
                        self.output_text.tag_add("green_text", ui_start_index, ui_end_index)
                        continue

                words = output_text_clean.split()
                for word in words:
                    if "accepted" in word.lower():
                        job_count += 1
                        if boo_detected:
                            self.output_text.insert(tk.END, word + " ", "rejected")
                            self.output_text.tag_configure("rejected", foreground="#FF0000")
                        else:
                            self.output_text.insert(tk.END, word + " ", "accepted")
                            self.output_text.tag_configure("accepted", foreground="#00FF00")
                        try:
                            hash_rate, unit = self.parse_hash_rate(words)
                            if hash_rate is not None:
                                if unit == "kH/s":
                                    hash_rate /= 1000
                                accepted_jobs.append(hash_rate)
                        except ValueError:
                            pass
                    elif "rejected" in word.lower():
                        boo_detected = True
                        self.output_text.insert(tk.END, word + " ", "rejected")
                        self.output_text.tag_configure("rejected", foreground="#FF0000")
                    elif word.lower() == "yes!" or (word.startswith("yes!") and len(word) > 4):
                        self.output_text.insert(tk.END, word[:3], "yes")
                        self.output_text.insert(tk.END, word[3:], "normal")
                        self.output_text.tag_configure("yes", foreground="#00FF00")
                    elif word.lower() == "boo!" or (word.startswith("boo!") and len(word) > 4):
                        self.output_text.insert(tk.END, word[:3], "boo")
                        self.output_text.insert(tk.END, word[3:], "normal")
                        self.output_text.tag_configure("boo", foreground="#FF0000")
                    elif word.lower() == "retry" and len(words) > i + 3 and words[i + 1].lower() == "in" and words[i + 2].isdigit() and "seconds" in words[i + 3].lower():
                        self.output_text.insert(tk.END, word + " " + words[i + 1] + " " + words[i + 2] + " " + words[i + 3] + " ", "retry")
                        self.output_text.tag_configure("retry", foreground="#FF00FF")
                    elif "stratum difficulty set to" in output_text_clean.lower():
                        self.output_text.insert(tk.END, output_text_clean + '\n', "difficulty")
                        self.output_text.tag_configure("difficulty", foreground="#FFA500")
                        break
                    else:
                        self.output_text.insert(tk.END, word + " ", "normal")
                        self.output_text.tag_configure("normal", foreground="#FFFFFF")

                self.output_text.insert(tk.END, '\n')
                self.output_text.see(tk.END)

            if job_count % 10 == 0 and job_count != 0:
                if accepted_jobs:
                    avg_hash_rate = sum(accepted_jobs) / len(accepted_jobs)
                    self.avg_hash_rate_value.config(text=f"{avg_hash_rate:.2f} MH/s")
                    accepted_jobs.clear()

    def parse_hash_rate(self, words):
        for i, word in enumerate(words):
            if word.endswith("kH/s") or word.endswith("MH/s"):
                try:
                    hash_rate = float(words[i - 1])
                    unit = words[i][-5:]
                    return hash_rate, unit
                except (ValueError, IndexError):
                    pass
        raise ValueError("Hash rate not found")

    def show_customization(self):
        if not self.customization_window:
            self.customization_window = tk.Toplevel(self)
            self.customization_window.title("Customize")
            self.customization_window.configure(background=BACKGROUND_COLOR)
            for style_name in STYLES:
                btn = ttk.Button(self.customization_window, text=style_name, command=lambda name=style_name: self.select_style(name))
                btn.pack(pady=5)
            self.customization_window.protocol("WM_DELETE_WINDOW", self.on_customization_close)

    def on_customization_close(self):
        self.customization_window.destroy()
        self.customization_window = None

    def select_style(self, style_name):
        if style_name in STYLES:
            self.selected_style.set(style_name)
            self.apply_style()
        else:
            print(f"Style '{style_name}' not found in STYLES.")

    def find_ccminer(self):
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        print("Executable directory:", exe_dir)
        for filename in os.listdir(exe_dir):
            if filename.lower() == "ccminer.exe":
                return os.path.join(exe_dir, filename)
        return None

if __name__ == '__main__':
    app = MiningUI()
    app.mainloop()
