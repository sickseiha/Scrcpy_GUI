import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import sys
import subprocess
import shlex
import os
import re
import threading
from tkinter import filedialog
import shutil

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

bin_dir = resource_path("bin")
os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

root = ttkb.Window(themename="darkly")
root.geometry("630x630")
root.resizable(False, False)
root.overrideredirect(True)

titlebar = tk.Frame(root, bg="#212529", height=20)
titlebar.pack(fill="x")

title_label = tk.Label(titlebar, text="SCRCPY", bg="#212529", fg="#28a745", font=("Segoe UI", 10))
title_label.pack(side="left", padx=12, pady=0)

def close_app():
    reset_resolution()
    root.destroy()

close_btn = tk.Button(titlebar, text="×", bg="#212529", fg="#adb5bd", font=("Segoe UI", 12, "bold"), bd=0, command=close_app, width=3, height=1)
close_btn.pack(side="right", padx=6, pady=0)
close_btn.configure(activebackground="#c82333", activeforeground="white")

def start_drag(event):
    root._offsetx = event.x_root - root.winfo_x()
    root._offsety = event.y_root - root.winfo_y()

def drag(event):
    x = event.x_root - root._offsetx
    y = event.y_root - root._offsety
    root.geometry(f"+{x}+{y}")

for widget in [titlebar, title_label, close_btn]:
    widget.bind("<Button-1>", start_drag)
    widget.bind("<B1-Motion>", drag)

video_var = tk.BooleanVar(value=True)
audio_var = tk.BooleanVar(value=True)
control_var = tk.BooleanVar(value=True)
hid_var = tk.BooleanVar(value=False)
gamepad_var = tk.BooleanVar(value=True)
borderless_var = tk.BooleanVar(value=False)
fullscreen_var = tk.BooleanVar(value=False)
screenoff_var = tk.BooleanVar(value=False)
auto_resize_var = tk.BooleanVar(value=False)
res_w_var = tk.StringVar()
res_h_var = tk.StringVar()
dpi_var = tk.StringVar()
recorder_var = tk.BooleanVar(value=False)
save_path_var = tk.StringVar()
app_launch_var = tk.StringVar()
apk_path_var = tk.StringVar()

mode = None
wifi_serial = None
tcpip_set = False
last_ip = None
original_size = None
original_density = None
binaries_ok = True

CREATE_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0

def check_binaries():
    global binaries_ok
    adb_exists = shutil.which("adb") is not None
    scrcpy_exists = shutil.which("scrcpy") is not None
    if not adb_exists and not scrcpy_exists:
        status_label.configure(text="ADB & Scrcpy not found", bootstyle=DANGER)
        binaries_ok = False
    elif not adb_exists:
        status_label.configure(text="ADB not found", bootstyle=DANGER)
        binaries_ok = False
    elif not scrcpy_exists:
        status_label.configure(text="Scrcpy not found", bootstyle=DANGER)
        binaries_ok = False
    if not binaries_ok:
        start_btn.configure(state="disabled")
    return binaries_ok

def run(cmd):
    try:
        return subprocess.check_output(
            cmd,
            creationflags=CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
            stderr=subprocess.STDOUT
        ).decode(errors="ignore")
    except:
        return ""

def run_s(cmd):
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    )

def get_target_id():
    if mode == "usb":
        return ["-d"]
    elif mode == "wifi" and wifi_serial:
        return ["-s", wifi_serial]
    return []

def get_adb_val(cmd_type):
    target = get_target_id()
    if not target: return ""
    out = run(["adb"] + target + ["shell", "wm", cmd_type])
    ov = re.search(r"Override size: (\d+x\d+)", out) or re.search(r"Override density: (\d+)", out)
    if ov: return ov.group(1)
    ph = re.search(r"Physical size: (\d+x\d+)", out) or re.search(r"Physical density: (\d+)", out)
    if ph: return ph.group(1)
    return ""

def reset_resolution():
    target = get_target_id()
    if not target: return
    if auto_resize_var.get():
        if original_size:
            run_s(["adb"] + target + ["shell", "wm", "size", original_size])
            res_w_var.set(original_size.split('x')[0])
            res_h_var.set(original_size.split('x')[1])
        if original_density:
            run_s(["adb"] + target + ["shell", "wm", "density", original_density])
            dpi_var.set(original_density)

def apply_resolution():
    target = get_target_id()
    if not target: return
    if auto_resize_var.get():
        if res_w_var.get() and res_h_var.get():
            run_s(["adb"] + target + ["shell", "wm", "size", f"{res_w_var.get()}x{res_h_var.get()}"])
        if dpi_var.get():
            run_s(["adb"] + target + ["shell", "wm", "density", dpi_var.get()])

def get_ip():
    for iface in ["wlan0", "wlan1", "rmnet_data0"]:
        out = run(["adb", "shell", "ip", "addr", "show", iface])
        for line in out.splitlines():
            if "inet " in line:
                match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    ip = match.group(1)
                    if ip.startswith(("192.", "10.", "172.")):
                        return ip
    return None

header = ttkb.Label(root, text="SCRCPY", font=("Segoe UI", 24, "bold"), bootstyle=SUCCESS)
header.pack(pady=(0, 0))
status_label = ttkb.Label(root, text="Checking connection...", font=("Segoe UI", 10), bootstyle=SECONDARY)
status_label.pack(pady=(0, 12))

main_frame = ttkb.Frame(root)
main_frame.pack(fill=X, padx=20, pady=(10, 4))

video_col = ttkb.Frame(main_frame)
video_col.pack(side="left", fill=BOTH, expand=True, padx=(0, 10))
video_cb = ttkb.Checkbutton(video_col, text="  Enable Video", variable=video_var, bootstyle="info-square-toggle")
video_cb.pack(anchor="center", pady=(0, 4))

video_settings = ttkb.Labelframe(video_col, text=" Video ", bootstyle=PRIMARY)
video_settings.pack(fill=X, pady=4)
size_label = ttkb.Label(video_settings, text="Max Size")
size_label.grid(row=0, column=0, padx=6, pady=4, sticky="w")
size_combo = ttkb.Combobox(video_settings, values=["480", "640", "720", "960", "1024", "1280", "1440", "1600", "1920"], width=14, bootstyle=INFO)
size_combo.set("1024")
size_combo.grid(row=0, column=1, padx=6, pady=4, sticky="w")
vbit_label = ttkb.Label(video_settings, text="Bitrate")
vbit_label.grid(row=1, column=0, padx=6, pady=4, sticky="w")
vbit_combo = ttkb.Combobox(video_settings, values=["2M", "4M", "6M", "8M", "10M", "12M", "16M", "20M"], width=14, bootstyle=INFO)
vbit_combo.set("8M")
vbit_combo.grid(row=1, column=1, padx=6, pady=4, sticky="w")
fps_label = ttkb.Label(video_settings, text="Framerate")
fps_label.grid(row=2, column=0, padx=6, pady=4, sticky="w")
fps_combo = ttkb.Combobox(video_settings, values=["30", "45", "60", "75", "90", "120"], width=14, bootstyle=INFO)
fps_combo.set("60")
fps_combo.grid(row=2, column=1, padx=6, pady=(4, 10), sticky="w")

display_cb = ttkb.Checkbutton(video_col, text="  Auto Resize", variable=auto_resize_var, bootstyle="info-square-toggle")
display_cb.pack(anchor="center", pady=(10, 4))

res_settings = ttkb.Labelframe(video_col, text=" Display ", bootstyle=DANGER)
res_settings.pack(fill=X, pady=4)
res_label = ttkb.Label(res_settings, text="Resolution")
res_label.grid(row=0, column=0, padx=6, pady=4, sticky="w")
res_box = ttkb.Frame(res_settings)
res_box.grid(row=0, column=1, padx=(2, 10), pady=4)
res_w_ent = ttkb.Entry(res_box, textvariable=res_w_var, width=5, bootstyle=DANGER)
res_w_ent.pack(side=LEFT)
res_x_label = ttkb.Label(res_box, text="x")
res_x_label.pack(side=LEFT, padx=6)
res_h_ent = ttkb.Entry(res_box, textvariable=res_h_var, width=5, bootstyle=DANGER)
res_h_ent.pack(side=LEFT)
dpi_label = ttkb.Label(res_settings, text="Density")
dpi_label.grid(row=1, column=0, padx=6, pady=4, sticky="w")
dpi_ent = ttkb.Entry(res_settings, textvariable=dpi_var, width=5, bootstyle=DANGER)
dpi_ent.grid(row=1, column=1, padx=2, pady=11, sticky="w")

audio_col = ttkb.Frame(main_frame)
audio_col.pack(side="left", fill=BOTH, expand=True, padx=10)
audio_cb = ttkb.Checkbutton(audio_col, text="  Enable Audio", variable=audio_var, bootstyle="info-square-toggle")
audio_cb.pack(anchor="center", pady=(0, 4))
audio_settings = ttkb.Labelframe(audio_col, text=" Audio ", bootstyle=SUCCESS)
audio_settings.pack(fill=X, pady=4)
buffer_label = ttkb.Label(audio_settings, text="Buffer")
buffer_label.grid(row=0, column=0, padx=8, pady=4, sticky="w")
buffer_combo = ttkb.Combobox(audio_settings, values=["20 ms", "50 ms", "80 ms", "120 ms", "200 ms"], width=10, bootstyle=SUCCESS)
buffer_combo.set("50 ms")
buffer_combo.grid(row=0, column=1, padx=8, pady=4, sticky="w")
abit_label = ttkb.Label(audio_settings, text="Bitrate")
abit_label.grid(row=1, column=0, padx=8, pady=4, sticky="w")
abit_combo = ttkb.Combobox(audio_settings, values=["64K", "96K", "128K", "192K", "256K", "320K"], width=10, bootstyle=SUCCESS)
abit_combo.set("128K")
abit_combo.grid(row=1, column=1, padx=8, pady=4, sticky="w")
codec_label = ttkb.Label(audio_settings, text="Codec")
codec_label.grid(row=2, column=0, padx=8, pady=4, sticky="w")
codec_combo = ttkb.Combobox(audio_settings, values=["opus", "aac", "raw", "flac"], width=10, bootstyle=SUCCESS)
codec_combo.set("opus")
codec_combo.grid(row=2, column=1, padx=8, pady=(4, 10), sticky="w")

recorder_cb = ttkb.Checkbutton(audio_col, text="  Enable Recorder", variable=recorder_var, bootstyle="info-square-toggle")
recorder_cb.pack(anchor="center", pady=(10, 4))
recorder_settings = ttkb.Labelframe(audio_col, text=" Recorder ", bootstyle=PRIMARY)
recorder_settings.pack(fill=X, pady=4)
format_label = ttkb.Label(recorder_settings, text="Format")
format_label.grid(row=0, column=0, padx=8, pady=4, sticky="w")
format_combo = ttkb.Combobox(recorder_settings, values=["mp4", "mkv"], width=10, bootstyle=PRIMARY)
format_combo.set("mp4")
format_combo.grid(row=0, column=1, padx=(4, 10), pady=4, sticky="w")
save_label_ui = ttkb.Label(recorder_settings, text="Save to")
save_label_ui.grid(row=1, column=0, padx=8, pady=4, sticky="w")

def select_path():
    path = filedialog.asksaveasfilename(defaultextension=f".{format_combo.get()}", filetypes=[("Video files", f"*.{format_combo.get()}")])
    if path: save_path_var.set(path)

save_btn_ui = ttkb.Button(recorder_settings, text="Browse", width=10, bootstyle="info-outline", command=select_path)
save_btn_ui.grid(row=1, column=1, padx=(4, 10), pady=10, sticky="w")

control_col = ttkb.Frame(main_frame)
control_col.pack(side="left", fill=BOTH, expand=True, padx=(10, 0))
ttkb.Checkbutton(control_col, text="  Enable Control", variable=control_var, bootstyle="info-square-toggle").pack(anchor="center", pady=(0, 4))
ctrl_settings = ttkb.Labelframe(control_col, text=" Control ", bootstyle=WARNING)
ctrl_settings.pack(fill=X, pady=4)
hid_cb = ttkb.Checkbutton(ctrl_settings, text="  Mouse & Keyboard HID", variable=hid_var, bootstyle="info-square-toggle")
hid_cb.pack(anchor="w", padx=10, pady=(3, 3.5))
gamepad_cb = ttkb.Checkbutton(ctrl_settings, text="  Enable Gamepad", variable=gamepad_var, bootstyle="info-square-toggle")
gamepad_cb.pack(anchor="w", padx=10, pady=3.5)
borderless_cb = ttkb.Checkbutton(ctrl_settings, text="  Borderless Window", variable=borderless_var, bootstyle="info-square-toggle")
borderless_cb.pack(anchor="w", padx=10, pady=3.5)
fullscreen_cb = ttkb.Checkbutton(ctrl_settings, text="  Start Fullscreen", variable=fullscreen_var, bootstyle="info-square-toggle")
fullscreen_cb.pack(anchor="w", padx=10, pady=3.5)
screenoff_cb = ttkb.Checkbutton(ctrl_settings, text="  Turn Screen Off", variable=screenoff_var, bootstyle="info-square-toggle")
screenoff_cb.pack(anchor="w", padx=10, pady=(3, 9))

ttkb.Label(control_col, text="Extra Features").pack(anchor="center", pady=(7, 2))
more_settings = ttkb.Labelframe(control_col, text=" Application ", bootstyle=LIGHT)
more_settings.pack(fill=X, pady=4)
ttkb.Label(more_settings, text="Launch").grid(row=0, column=0, padx=8, pady=4, sticky="w")
launch_combo = ttkb.Combobox(more_settings, textvariable=app_launch_var, width=16, bootstyle=LIGHT)
launch_combo.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="w")
ttkb.Label(more_settings, text="Install").grid(row=1, column=0, padx=8, pady=4, sticky="w")

def select_apk():
    path = filedialog.askopenfilename(filetypes=[("APK files", "*.apk")])
    if path:
        apk_path_var.set(path)
        target = get_target_id()
        if target or last_ip:
            status_label.configure(text="Installing APK...", bootstyle=WARNING)
            def do_install():
                run_s(["adb"] + (target if target else ["-s", f"{last_ip}:5555"]) + ["install", path])
                root.after(0, lambda: status_label.configure(text="Install Finished", bootstyle=SUCCESS))
                root.after(3000, lambda: check_connection())
            threading.Thread(target=do_install, daemon=True).start()

push_btn = ttkb.Button(more_settings, text="Browse", width=10, bootstyle="light-outline", command=select_apk)
push_btn.grid(row=1, column=1, padx=(0, 8), pady=10, sticky="w")

cmd_frame = ttkb.Frame(root)
cmd_frame.pack(fill=X, padx=20, pady=(4, 10))
ttkb.Label(cmd_frame, text="Active Commands").pack(side="top", pady=(0,12))
log = tk.Text(cmd_frame, height=5, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
log.pack(fill="x", expand=True)

style = ttkb.Style()
style.configure('success.Outline.TButton', font=("Segoe UI", 11, "bold"))

btn_frame = ttkb.Frame(root)
btn_frame.pack(pady=(8, 8))

def build_command():
    full_cmd = []
    target = get_target_id()
    target_str = " ".join(target) if target else ""
    if auto_resize_var.get():
        if res_w_var.get() and res_h_var.get():
            full_cmd.append(f"adb {target_str} shell wm size {res_w_var.get()}x{res_h_var.get()}")
        if dpi_var.get():
            full_cmd.append(f"adb {target_str} shell wm density {dpi_var.get()}")
    cmd = ["scrcpy"]
    if mode == "usb": cmd.append("-d")
    elif mode == "wifi" and wifi_serial: cmd += ["-s", wifi_serial]
    cmd.append("--shortcut-mod=lalt,ralt")
    if not video_var.get(): cmd.append("--no-video")
    else: cmd += ["--max-size", size_combo.get(), "--video-bit-rate", vbit_combo.get(), "--max-fps", fps_combo.get()]
    if not audio_var.get(): cmd.append("--no-audio")
    else:
        buf = buffer_combo.get().replace(" ms", "")
        cmd += ["--audio-buffer", buf, "--audio-bit-rate", abit_combo.get(), "--audio-codec", codec_combo.get()]
    if not control_var.get(): cmd.append("--no-control")
    else:
        if hid_var.get(): cmd += ["--keyboard=uhid", "--mouse=uhid"]
        if gamepad_var.get(): cmd.append("--gamepad=uhid")
    if borderless_var.get(): cmd.append("--window-borderless")
    if fullscreen_var.get(): cmd.append("--fullscreen")
    if screenoff_var.get(): cmd.append("--turn-screen-off")
    if recorder_var.get() and save_path_var.get():
        cmd += ["--record", save_path_var.get(), "--record-format", format_combo.get()]
    if app_launch_var.get():
        cmd += ["--start-app", app_launch_var.get()]
    full_cmd.append(shlex.join(cmd))
    if auto_resize_var.get():
        if original_size: full_cmd.append(f"adb {target_str} shell wm size {original_size}")
        if original_density: full_cmd.append(f"adb {target_str} shell wm density {original_density}")
    return " && ".join(full_cmd)

def start_scrcpy():
    target = get_target_id()
    if not target and not last_ip: return
    apply_resolution()
    full_text = log.get("1.0", tk.END).strip()
    scrcpy_part = next((p for p in full_text.split(" && ") if p.strip().startswith("scrcpy")), None)
    if scrcpy_part:
        try:
            cmd_args = shlex.split(scrcpy_part)
            proc = subprocess.Popen(cmd_args, creationflags=CREATE_NO_WINDOW)
            def monitor():
                proc.wait()
                root.after(0, reset_resolution)
            threading.Thread(target=monitor, daemon=True).start()
        except Exception as e:
            pass

start_btn = ttkb.Button(btn_frame, text="START", bootstyle="success outline", style="success.Outline.TButton", width=10, command=start_scrcpy)
start_btn.pack(side="left")

def toggle_video(*args):
    enabled = video_var.get()
    state = "normal" if enabled else "disabled"
    size_combo.config(state=state)
    vbit_combo.config(state=state)
    fps_combo.config(state=state)

def toggle_audio(*args):
    enabled = audio_var.get()
    state = "normal" if enabled else "disabled"
    buffer_combo.config(state=state)
    abit_combo.config(state=state)
    codec_combo.config(state=state)

def toggle_control(*args):
    enabled = control_var.get()
    state = "normal" if enabled else "disabled"
    hid_cb.config(state=state)
    gamepad_cb.config(state=state)

def toggle_display(*args):
    enabled = auto_resize_var.get()
    state = "normal" if enabled else "disabled"
    res_w_ent.config(state=state)
    res_h_ent.config(state=state)
    dpi_ent.config(state=state)

def toggle_recorder(*args):
    enabled = recorder_var.get()
    state = "normal" if enabled else "disabled"
    format_combo.config(state=state)
    save_btn_ui.config(state=state)

def update_preview(*args):
    cmd = build_command()
    log.delete("1.0", tk.END)
    log.insert(tk.END, cmd)

def check_connection():
    global mode, wifi_serial, tcpip_set, last_ip, original_size, original_density
    if not binaries_ok: return
    try:
        out = run(["adb", "devices"])
        lines = out.strip().splitlines()[1:]
        usb = any("device" in line and ":" not in line.split()[0] for line in lines)
        wifi_list = [line.split()[0] for line in lines if "device" in line and ":" in line.split()[0]]
        wifi = bool(wifi_list)
        if usb:
            mode = "usb"
            wifi_serial = None
            status_label.configure(text="USB Connected", bootstyle=SUCCESS)
            if not tcpip_set:
                run_s(["adb", "tcpip", "5555"])
                tcpip_set = True
            ip = get_ip()
            if ip:
                last_ip = ip
                run_s(["adb", "connect", f"{ip}:5555"])
        elif wifi:
            mode = "wifi"
            wifi_serial = wifi_list[0]
            status_label.configure(text=f"Wi-Fi → {wifi_serial}", bootstyle=INFO)
        else:
            mode = None
            wifi_serial = None
            status_label.configure(text="No device detected", bootstyle=DANGER)
            if last_ip:
                run_s(["adb", "connect", f"{last_ip}:5555"])
        if (usb or wifi):
            start_btn.configure(state="normal")
            if not original_size:
                s = get_adb_val("size")
                d = get_adb_val("density")
                if s and 'x' in s:
                    original_size = s
                    res_w_var.set(s.split('x')[0])
                    res_h_var.set(s.split('x')[1])
                if d:
                    original_density = d
                    dpi_var.set(d)
            if not launch_combo['values']:
                pkgs = run(["adb"] + get_target_id() + ["shell", "pm", "list", "packages", "-3"]).splitlines()
                launch_combo['values'] = sorted([p.replace("package:", "") for p in pkgs])
        else:
            start_btn.configure(state="disabled")
    except:
        status_label.configure(text="ADB error", bootstyle=DANGER)
        start_btn.configure(state="disabled")
    update_preview()
    root.after(2000, check_connection)

for var in [video_var, audio_var, control_var, hid_var, gamepad_var, borderless_var, fullscreen_var, screenoff_var, auto_resize_var, recorder_var, save_path_var, app_launch_var, apk_path_var, res_w_var, res_h_var, dpi_var]:
    var.trace_add("write", update_preview)
for combo in [size_combo, vbit_combo, fps_combo, buffer_combo, abit_combo, codec_combo, format_combo, launch_combo]:
    combo.bind("<<ComboboxSelected>>", update_preview)
video_var.trace_add("write", toggle_video)
audio_var.trace_add("write", toggle_audio)
control_var.trace_add("write", toggle_control)
auto_resize_var.trace_add("write", toggle_display)
recorder_var.trace_add("write", toggle_recorder)
update_preview()
if check_binaries():
    check_connection()
toggle_video()
toggle_audio()
toggle_control()
toggle_display()
toggle_recorder()
root.mainloop()
