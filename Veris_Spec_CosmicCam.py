# =================================================================
# GEMINI VERIS-SPEC V4.2: COSMIC-CAM TERMINAL (FINALIZED)
# Features: Zoom, Focus Peaking, Thermal, Sentry, Telemetry Logging
# =================================================================
import cv2
import os
import winsound
import time
import csv
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
import pygame
import time

class VerisSuperNova:
    def __init__(self, window):
        self.window = window
        self.window.title("VERIS-SPEC V4.2: COSMIC-CAM TERMINAL")
        self.cap = cv2.VideoCapture(0)
        # --- ENHANCED STATES ---
        self.zoom_level = 1.0
        self.zoom_center = [320, 240]
        self.peaking_active = False
        self.manual_box = None
        self.drawing = False
        self.start_pt = (0, 0)
        self.night_vision = False
        self.thermal_mode = False
        self.trail_active = False
        self.sentry_mode = False
        self.is_firing = False
        self.star_trail_frame = None
        self.prev_frame = None
        
        # --- BUTTON PUSH SOUND EFFECT ---
        pygame.mixer.init() # Initialize the mixer
        audio_file = "c:/Gemini/ButtonPush.Wav"
        self.sound = pygame.mixer.Sound(audio_file)


        # --- CALIBRATION & LOGGING ---
        self.focal_length_px = 800
        self.known_width = 0.5      # Reference object size (meters)
        self.log_file = "captures/cosmic_log.csv"
        os.makedirs("captures", exist_ok=True)
        self.init_log()

        # --- UI SETUP ---
        self.canvas = tk.Canvas(window, width=640, height=480, bg="black")
        self.canvas.pack()

        # Bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<MouseWheel>", self.handle_zoom)
        window.bind("<z>", lambda e: self.reset_zoom())
        window.bind("<c>", lambda e: self.auto_calibrate())

        ctrl = tk.Frame(window)
        ctrl.pack(pady=5)
        tk.Button(ctrl, text="NIGHT VISION",
                  command=self.toggle_nv).grid(row=0, column=0)
        tk.Button(ctrl, text="THERMAL", command=self.toggle_thermal,
                  bg="orange").grid(row=0, column=1)
        self.peak_btn = tk.Button(
            ctrl, text="FOCUS PEAK: OFF", command=self.toggle_peaking, bg="green", fg="white")
        self.peak_btn.grid(row=0, column=2)
        self.trail_btn = tk.Button(
            ctrl, text="STAR-TRAIL", command=self.toggle_trail, bg="darkblue", fg="white")
        self.trail_btn.grid(row=0, column=3)
        self.sentry_btn = tk.Button(
            ctrl, text="SENTRY: OFF", command=self.toggle_sentry)
        self.sentry_btn.grid(row=0, column=4)

        self.fire_btn = tk.Button(window, text="HOLD TO RAPID FIRE / LOG DATA",
                                  bg="red", fg="white", font=("Arial", 10, "bold"))
        self.fire_btn.pack(fill="x", padx=10, pady=5)
        self.fire_btn.bind("<Button-1>", lambda e: self.set_fire(True))
        self.fire_btn.bind("<ButtonRelease-1>", lambda e: self.set_fire(False))

        self.update_loop()

    # --- LOGGING & CALIBRATION ---
    def init_log(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                csv.writer(f).writerow(
                    ["Timestamp", "Label", "Dist_m", "Focus_Score"])

    def auto_calibrate(self):
        if self.manual_box:
            (x1, _), (x2, _) = self.manual_box
            pw = max(abs(x2 - x1), 1)
            self.focal_length_px = (pw * 2.0) / \
                self.known_width  # Target at 2m
            # winsound.Beep(2000, 100)
            self.sound.play(0)

    # --- FEATURE TOGGLES ---
    def toggle_nv(self):
        self.night_vision = not self.night_vision
        self.thermal_mode = False

    def toggle_thermal(self):
        self.thermal_mode = not self.thermal_mode
        self.night_vision = False

    def toggle_peaking(self):
        self.peaking_active = not self.peaking_active
        self.peak_btn.config(
            text=f"FOCUS PEAK: {'ON' if self.peaking_active else 'OFF'}")

    def toggle_sentry(self):
        self.sentry_mode = not self.sentry_mode
        self.sentry_btn.config(
            text=f"SENTRY: {'ON' if self.sentry_mode else 'OFF'}")

    def toggle_trail(self):
        self.trail_active = not self.trail_active
        if not self.trail_active:
            self.star_trail_frame = None
            self.trail_btn.config(
                text=f"TRAIL: {'ON' if self.trail_active else 'OFF'}")

    # --- ZOOM LOGIC ---
    def handle_zoom(self, event):
        if event.delta > 0:
            self.zoom_level = min(self.zoom_level + 0.2, 5.0)
        else:
            self.zoom_level = max(self.zoom_level - 0.2, 1.0)
        self.zoom_center = [event.x, event.y]

    def reset_zoom(self): 
    	self.zoom_level = 1.0;
    	self.zoom_center = [320, 240]

    def apply_zoom(self, img):
        if self.zoom_level == 1.0:
            return img
        h, w = img.shape[:2]
        nw, nh = int(w/self.zoom_level), int(h/self.zoom_level)
        x = max(0, min(self.zoom_center[0] - nw//2, w - nw))
        y = max(0, min(self.zoom_center[1] - nh//2, h - nh))
        return cv2.resize(img[y:y+nh, x:x+nw], (w, h))

    # --- IMAGE PROCESSING ---
    def apply_focus_peaking(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        edges = cv2.Laplacian(gray, cv2.CV_8U, ksize=3)
        _, mask = cv2.threshold(edges, 45, 255, cv2.THRESH_BINARY)
        peaking_layer = img.copy()
        peaking_layer[mask > 0] = [0, 255, 0]
        cv2.putText(
            peaking_layer, f"FOCUS-SCORE: {int(score)}", (10, 460), 1, 1, (0, 255, 0), 2)
        return cv2.addWeighted(img, 0.8, peaking_layer, 0.2, 0), score

    def update_loop(self):
        ret, raw = self.cap.read()
        if not ret:
            return

        # 1. Pipeline
        display = self.apply_zoom(raw)
        f_score = 0

        if self.trail_active:
            if self.star_trail_frame is None:
                self.star_trail_frame = display.astype(np.float32)
            cv2.accumulateWeighted(display, self.star_trail_frame, 0.1)
            display = cv2.convertScaleAbs(self.star_trail_frame)

        if self.thermal_mode:
            display = cv2.applyColorMap(cv2.cvtColor(
                display, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_JET)
        elif self.night_vision:
            g = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
            display = np.zeros_like(display)
            display[:, :, 1] = cv2.equalizeHist(g)

        if self.peaking_active:
            display, f_score = self.apply_focus_peaking(display)

        # 2. UI Overlays
        cv2.putText(
            display, f"V4.2 | ZOOM: {self.zoom_level:.1f}x", (10, 30), 1, 1, (0, 255, 0), 1)
        if self.manual_box:
            (x1, y1), (x2, y2) = self.manual_box
            pw = max(abs(x2 - x1), 1)
            dist = (self.known_width * self.focal_length_px) / \
                (pw / self.zoom_level)
            cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.putText(display, f"RANGE: {dist:.2f}m",
                        (x1, y1-10), 1, 1, (255, 0, 255), 2)

        # 3. Sentry Motion
        if self.sentry_mode and self.prev_frame is not None:
            if np.mean(cv2.absdiff(cv2.cvtColor(self.prev_frame, 6), cv2.cvtColor(raw, 6))) > 25:
                self.save_logic(raw, "SENTRY", 0, f_score)

        self.prev_frame = raw.copy()
        img_tk = ImageTk.PhotoImage(image=Image.fromarray(
            cv2.cvtColor(display, cv2.COLOR_BGR2RGB)))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        self.canvas.img = img_tk
        self.window.after(15, self.update_loop)

    def set_fire(self, state):
        self.is_firing = state
        if state:
            self.rapid_fire()

    def rapid_fire(self):
        if self.is_firing:
            ret, f = self.cap.read()
            if ret:
                self.save_logic(f, "RAPID", 0, 0)
                self.window.after(300, self.rapid_fire)

    def save_logic(self, f, lbl, dist, score):
        # winsound.Beep(1200, 50)
        self.sound.play(0)
        ts = datetime.now().strftime('%H%M%S_%f')
        cv2.imwrite(f"captures/{lbl}_{ts}.bmp", f)
        with open(self.log_file, 'a', newline='') as cf:
            csv.writer(cf).writerow([ts, lbl, f"{dist:.2f}", int(score)])

    def start_drag(self, e): self.start_pt = (e.x, e.y)
    def drag(self, e): self.manual_box = (self.start_pt, (e.x, e.y))


root = tk.Tk()
app = VerisSuperNova(root)
root.mainloop()



