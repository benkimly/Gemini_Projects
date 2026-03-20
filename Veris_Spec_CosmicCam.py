#Gemini - Veris-Spec V4 Cosmic classmethod
import cv
2, os, winsound, time, numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime

# Load AI Brain
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

class VerisSuperNova:
    def __init__(self, window):
        self.window = window
        self.window.title("VERIS-SPEC V4: STAR-TRAIL & RANGE")
        self.cap = cv2.VideoCapture(0)
        
        # Core States
        self.manual_box = None; self.drawing = False; self.start_pt = (0,0)
        self.night_vision = False; self.sentry_mode = False; self.is_firing = False
        self.track_color = None; self.prev_frame = None
        
        # --- NEW: STAR-TRAIL & RANGE SPECS ---
        self.star_trail_frame = None # Holds the accumulated light
        self.trail_active = False
        self.focal_length_px = 800  # Calibration for Rangefinder
        self.known_width = 0.5      # Ref size in meters

        # UI Setup
        self.canvas = tk.Canvas(window, width=640, height=480, bg="black")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.start_drag); self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Button-3>", self.pick_color) # Right click to lock color

        ctrl = tk.Frame(window); ctrl.pack(pady=5)
        tk.Button(ctrl, text="NIGHT VISION", command=self.toggle_nv).grid(row=0, column=0)
        self.sentry_btn = tk.Button(ctrl, text="SENTRY: OFF", command=self.toggle_sentry)
        self.sentry_btn.grid(row=0, column=1)
        self.trail_btn = tk.Button(ctrl, text="STAR-TRAIL: OFF", command=self.toggle_trail, bg="darkblue", fg="white")
        self.trail_btn.grid(row=0, column=2)
        
        self.fire_btn = tk.Button(window, text="HOLD TO RAPID FIRE / SNIPE", bg="red", fg="white", font=("Arial",10,"bold"))
        self.fire_btn.pack(fill="x", padx=10, pady=5)
        self.fire_btn.bind("<Button-1>", lambda e: self.set_fire(True)); self.fire_btn.bind("<ButtonRelease-1>", lambda e: self.set_fire(False))

        self.update_loop()

    def toggle_nv(self): self.night_vision = not self.night_vision
    def toggle_sentry(self): self.sentry_mode = not self.sentry_mode
    def toggle_trail(self):
        self.trail_active = not self.trail_active
        if not self.trail_active: self.star_trail_frame = None # Reset
        self.trail_btn.config(text=f"TRAIL: {'ON' if self.trail_active else 'OFF'}")

    def set_fire(self, state):
        self.is_firing = state
        if state: self.rapid_fire()

    def pick_color(self, e):
        ret, f = self.cap.read()
        if ret: self.track_color = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)[e.y, e.x]

    def start_drag(self, e): self.start_pt = (e.x, e.y)
    def drag(self, e): self.manual_box = (self.start_pt, (e.x, e.y))

    def update_loop(self):
        ret, frame = self.cap.read()
        if not ret: return
        
        # 1. STAR TRAIL ACCUMULATION (Light Stacking)
        if self.trail_active:
            if self.star_trail_frame is None: self.star_trail_frame = frame.astype(np.float32)
            # Add new frame to stack with slight decay for smoothness
            cv2.accumulateWeighted(frame, self.star_trail_frame, 0.1)
            display = cv2.convertScaleAbs(self.star_trail_frame)
        else:
            display = frame.copy()

        # 2. NIGHT VISION
        if self.night_vision:
            g = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
            display = np.zeros_like(display); display[:,:,1] = cv2.equalizeHist(g)

        # 3. RANGEFINDER & TARGETING
        if self.manual_box:
            (x1, y1), (x2, y2) = self.manual_box
            pw = abs(x2 - x1)
            dist = (self.known_width * self.focal_length_px) / max(pw, 1)
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display, f"RNG: {dist:.2f}m", (x1, y2+20), 1, 1, (0,255,0), 2)
            # Crosshair
            cx, cy = (x1+x2)//2, (y1+y2)//2
            cv2.line(display, (cx-10, cy), (cx+10, cy), (0,255,0), 1)
            cv2.line(display, (cx, cy-10), (cx, cy+10), (0,255,0), 1)

        # 4. SENTRY (Auto-Fire on Motion)
        if self.sentry_mode and self.prev_frame is not None:
            if np.mean(cv2.absdiff(cv2.cvtColor(self.prev_frame, 6), cv2.cvtColor(frame, 6))) > 25:
                self.save_logic(frame, "SENTRY")

        self.prev_frame = frame.copy()
        img_tk = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(display, cv2.COLOR_BGR2RGB)))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk); self.canvas.img = img_tk
        self.window.after(15, self.update_loop)

    def rapid_fire(self):
        if self.is_firing:
            ret, f = self.cap.read(); 
            if ret: self.save_logic(f, "RAPID")
            self.window.after(200, self.rapid_fire)

    def save_logic(self, f, lbl):
        winsound.Beep(1200, 50)
        os.makedirs("captures", exist_ok=True)
        fname = f"captures/{lbl}_{datetime.now().strftime('%H%M%S_%f')}.bmp"
        # Stamp Distance if targeting
        cv2.imwrite(fname, f)

root = tk.Tk(); app = VerisSuperNova(root); root.mainloop()



