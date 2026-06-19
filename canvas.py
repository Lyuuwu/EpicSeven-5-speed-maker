import math
from pathlib import Path

import customtkinter as ctk
from tkinter import Canvas
from PIL import Image, ImageTk

ROOT = Path(__file__).resolve().parent
LANGUAGE = ('zh-TW', 'en')

class CropWindow(ctk.CTkToplevel):
    MAX_W, MAX_H = 900, 560     # init window size
    MAX_SCALE = 8.0             # max zoom in scale
    HANDLE = 5                  # control square dot size
    CURSORS = {"nw": "top_left_corner", "ne": "top_right_corner",
               "se": "bottom_right_corner", "sw": "bottom_left_corner",
               "n": "sb_v_double_arrow", "s": "sb_v_double_arrow",
               "e": "sb_h_double_arrow", "w": "sb_h_double_arrow"}
    DIM_STIPPLE = 'gray50'      # mask
    
    def __init__(self, master, screenshot):
        super().__init__(master)
        self.app = master
        imgs_dir = ROOT / 'imgs'
        
        # --- window top level ---
        self.transient(master)
        self.lift()
        self.focus_force()
        self.after(100, self.lift)
        
        self.original = screenshot      # source img
        self.tk_img = None              # the cur img shows on the screen
        self.sel = None                 # selected region
        self.mode = None                # 'new' / 'pan' / 'move' / 'resize'
        self.resize_handle = None       # the name of control point when resizing
        self.drag_anchor = None         # initial cursor pos when draggin (original image corrdinate)
        self.sel_at_press = None        # start sel when moving
        self.pan_anchor = None          # initial cursor pos when panning (canvas corrdinate)
        self.offset_at_pan = None       # initial offset when panning
        self.hovering = False           # deter if the cursor is on the selected region
        
        self.title(self.app.tr('crop_title'))
        
        # min scale -> full img to MAX_W/H -> init scale
        ow, oh = self.original.size
        self.fit_scale = min(self.MAX_W / ow, self.MAX_H / oh, 1.0)
        self.scale = self.fit_scale
        self.offset_x = self.offset_y = 0.0
        
        # viewable region
        self.canvas_w = round(ow * self.fit_scale)
        self.canvas_h = round(oh * self.fit_scale)
        
        bar = ctk.CTkFrame(self)
        bar.pack(padx=10, pady=10, fill='x')
        ctk.CTkLabel(bar, text=self.app.tr('crop_target')).pack(side='left', padx=(8, 4))
        
        targets = [f.name[:-4].split('_', 1)[1] for f in imgs_dir.iterdir()
                   if f.is_file() and f.with_suffix('.png')
                   and len(f.name.split('_', 1)) == 2 and f.name.split('_', 1)[0] in LANGUAGE]
        targets = list(set(targets))
        self.target_menu = ctk.CTkOptionMenu(bar, values=targets)
        self.target_menu.pack(side='left', padx=4)
        ctk.CTkButton(bar, text=self.app.tr('crop_save'),
                      command=self.on_save).pack(side='right', padx=8)
        ctk.CTkButton(bar, text=self.app.tr('crop_clear'),
                      command=self.clear_selection).pack(side='right', padx=4)
        
        ctk.CTkLabel(self, text=self.app.tr('crop_hint')).pack(padx=10, pady=(0, 6))
        
        self.canvas = Canvas(self, width=self.canvas_w, height=self.canvas_h,
                             highlightthickness=0, cursor='cross', background='black')
        self.canvas.pack(padx=10, pady=(0, 10))
        
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Motion>', self.on_hover)
        self.canvas.bind('<Button-3>', self.on_clear)
        self.canvas.bind('<MouseWheel>', self.on_wheel)
        self.canvas.bind('<Button-2>', self.on_pan_start)
        self.canvas.bind('<B2-Motion>', self.on_pan_move)
        self.canvas.bind('<ButtonRelease-2>', self.on_pan_end)
        
        self.render()
    
    # --- corrdinate covert (original image, canvas) ---
    def c2o(self, cx, cy):
        ''' cursor to offset '''
        return (cx - self.offset_x) / self.scale, (cy - self.offset_y) / self.scale
    
    def o2c(self, ox, oy):
        ''' offset to cursor '''
        return ox * self.scale + self.offset_x, oy * self.scale + self.offset_y
    
    def clampx(self, ox):
        return max(0, min(ox, self.original.size[0]))
    
    def clampy(self, oy):
        return max(0, min(oy, self.original.size[1]))
    
    def clampxy(self, ox, oy):
        return self.clampx(ox), self.clampy(oy)
    
    def clamp_offset(self):
        ''' make image be full in the canvas '''
        dw, dh = (self.original.size[0] * self.scale,
                  self.original.size[1] * self.scale)
        self.offset_x = (self.canvas_w - dw) / 2 if dw <= self.canvas_w \
            else min(0, max(self.canvas_w - dw, self.offset_x))
        self.offset_y = (self.canvas_h - dh) / 2 if dh <= self.canvas_h \
            else min(0, max(self.canvas_h - dh, self.offset_y))
    
    def render(self):
        ow, oh = self.original.size
        ox0, oy0 = self.c2o(0, 0)
        ox1, oy1 = self.c2o(self.canvas_w, self.canvas_h)
        l = max(0,  int(math.floor(ox0)))
        t = max(0,  int(math.floor(oy0)))
        r = min(ow, int(math.ceil(ox1)))
        b = min(oh, int(math.ceil(oy1)))
        if r <= l or b <= t:
            return
        crop = self.original.crop((l, t, r, b))
        dw = max(1, round((r - l) * self.scale))
        dh = max(1, round((b - t) * self.scale))
        
        # zoom in: NEAREST | zoom out: LANCZOS
        resample = Image.NEAREST if self.scale > 1 else Image.LANCZOS
        self.tk_img = ImageTk.PhotoImage(crop.resize((dw, dh), resample))
        self.canvas.delete('img')
        px, py = self.o2c(l, t)
        self.canvas.create_image(round(px), round(py), anchor='nw',
                                 image=self.tk_img, tags='img')
        self.canvas.tag_lower('img')
        self.redraw_overlay()
    
    # --- selected region ---
    def sel_canvas(self):
        if self.sel is None:
            return None
        l, t, r, b = self.sel
        cl, ct = self.o2c(min(l, r), min(t, b))
        cr, cb = self.o2c(max(l, r), max(t, b))
        return cl, ct, cr, cb
    
    def handle_points(self, l, t, r, b):
        mx, my = (l + r) / 2, (t + b) / 2
        return {'nw': (l, t), 'n': (mx, t), 'ne': (r, t), 'e': (r, my),
                'se': (r, b), 's': (mx, b), 'sw': (l, b), 'w': (l, my)}
    
    def handle_at(self, cx, cy):
        box = self.sel_canvas()
        if box is None:
            return None
        tol = self.HANDLE + 3
        for name, (hx, hy) in self.handle_points(*box).items():
            if abs(cx - hx) <= tol and abs(cy - hy) <= tol:
                return name
        return None
    
    def over_selection(self, cx, cy):
        box = self.sel_canvas()
        if box is None:
            return False
        l, t, r, b = box
        m = self.HANDLE + 3
        return l - m <= cx <= r + m and t - m <= cy <= b + m
    
    # --- decoration ---
    def redraw_overlay(self):
        self.canvas.delete('dim', 'sel', 'handle', 'siz')
        box = self.sel_canvas()
        if box is None:
            return
        l, t, r, b = box
        W, H = self.canvas_w, self.canvas_h
        
        for d in [(0, 0, W, t), (0, b, W, H), (0, t, l, b), (r, t, W, b)]:
            self.canvas.create_rectangle(*d, fill='black', outline='',
                                         stipple=self.DIM_STIPPLE, tags='dim')
        self.canvas.create_rectangle(l, t, r, b, outline='red', width=2, tags='sel')
        
        # control point
        if self.hovering or self.mode in ('move', 'resize'):
            h = self.HANDLE
            for x, y in self.handle_points(l, t, r, b).values():
                self.canvas.create_rectangle(x - h, y - h, x + h, y + h,
                                             fill='white', outline='red', tags='handle')
            
        sl, st, sr, sb = self.sel
        w_orig, h_orig = round(abs(sr - sl)), round(abs(sb - st))
        tx = (l + r) / 2
        ty = (b - 14) if (b -t) > 40 else (b + 14)
        tid = self.canvas.create_text(tx, ty, text=f'{w_orig} x {h_orig}',
                                      fill='white', tags='siz')
        bb = self.canvas.bbox(tid)
        self.canvas.create_rectangle(bb[0] - 4, bb[1] - 2, bb[2] + 4, bb[3] + 2,
                                     fill='black', outline='', tags='siz')
        self.canvas.tag_raise(tid)
    
    def clear_selection(self):
        self.sel = None
        self.mode = None
        self.hovering = False
        self.redraw_overlay()

    def on_press(self, event):
        cx, cy = event.x, event.y
        handle = self.handle_at(cx, cy)
        if handle:
            self.mode = 'resize'
            self.resize_handle = handle
        elif self.over_selection(cx, cy):
            self.mode = 'move'
            self.sel_at_press = self.sel
            self.drag_anchor = self.c2o(cx, cy)
        elif self.sel is None:
            self.mode = 'new'
            ox, oy = self.c2o(cx, cy)
            ox, oy = self.clampxy(ox, oy)
            self.sel = (ox, oy, ox, oy)
            self.drag_anchor = (ox, oy)
        else:
            self.mode = 'pan'
            self.pan_anchor = (cx, cy)
            self.offset_at_pan = (self.offset_x, self.offset_y)
    
    def on_drag(self, event):
        if self.mode is None:
            return
        
        if self.mode == 'pan':
            ax, ay = self.pan_anchor
            ox0, oy0 = self.offset_at_pan
            self.offset_x = ox0 + (event.x - ax)
            self.offset_y = oy0 + (event.y - ay)
            self.clamp_offset()
            self.render()
            return
        
        ox, oy = self.c2o(event.x, event.y)
        ox, oy = self.clampxy(ox, oy)
        if self.mode == 'resize':
            l, t, r, b = self.sel # get size
            hn = self.resize_handle
            if 'n' in hn: t = oy
            if 's' in hn: b = oy
            if 'w' in hn: l = ox
            if 'e' in hn: r = ox
            self.sel = (l, t, r, b)
        elif self.mode == 'move':
            ax, ay = self.drag_anchor
            dx, dy = ox-ax, oy-ay
            l, t, r, b = self.sel_at_press
            ow, oh = self.original.size
            dx = max(-min(l, r), min(dx, ow-max(l, r)))
            dy = max(-min(t, b), min(dy, oh-max(t, b)))
            self.sel = (l+dx, t+dy, r+dx, b+dy)
        else: # new
            ax, ay = self.drag_anchor
            self.sel = (ax, ay, ox, oy)
        self.redraw_overlay()
    
    def on_release(self, event):
        if self.mode is not None and self.sel is not None:
            l, t, r, b = self.sel
            self.sel = (min(l, r), min(t, b), max(l, r), max(t, b))
        self.mode = None
        self.hovering = self.over_selection(event.x, event.y)
        self.redraw_overlay()
    
    def on_hover(self, event):
        self.hovering = self.over_selection(event.x, event.y)
        self.update_cursor(event.x, event.y)
        self.redraw_overlay()
    
    def update_cursor(self, cx, cy):
        handle = self.handle_at(cx, cy)
        if handle:
            self.canvas.config(cursor=self.CURSORS[handle]) # resize
        elif self.over_selection(cx, cy):
            self.canvas.config(cursor='fleur')              # move
        elif self.sel is None:
            self.canvas.config(cursor='cross')              # have not selected
        else:
            self.canvas.config(cursor='hand2')              # selected region or space: move
    
    def on_clear(self, event):
        self.clear_selection()
    
    def on_wheel(self, event):
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        new_scale = min(self.MAX_SCALE, max(self.fit_scale, self.scale * factor))
        if abs(new_scale - self.scale) < 1e-9:  # to min/max scale
            return

        # zoom in/out center is the cursor
        ox, oy = self.c2o(event.x, event.y)
        self.scale = new_scale
        self.offset_x = event.x - ox * self.scale
        self.offset_y = event.y - oy * self.scale
        self.clamp_offset()
        self.render()
        self.update_cursor(event.x, event.y)
    
    def on_pan_start(self, event):
        self.pan_anchor = (event.x, event.y)
        self.offset_at_pan = (self.offset_x, self.offset_y)
        self.canvas.config(cursor="fleur")

    def on_pan_move(self, event):
        if self.pan_anchor is None:
            return
        ax, ay = self.pan_anchor
        ox0, oy0 = self.offset_at_pan
        self.offset_x = ox0 + (event.x - ax)
        self.offset_y = oy0 + (event.y - ay)
        self.clamp_offset()
        self.render()

    def on_pan_end(self, event):
        self.pan_anchor = None
        self.update_cursor(event.x, event.y)

    def on_save(self):
        if self.sel is None:
            self.app.log(self.app.tr('msg_no_region'))
            return
        
        l, t, r, b = self.sel
        box = (int(round(min(l, r))), int(round(min(t, b))),
               int(round(max(l, r))), int(round(max(t, b))))
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            self.app.log(self.app.tr('msg_no_region'))
            return
        filename = self.target_menu.get()
        language = self.app.language
        self.original.crop(box).save(ROOT / 'imgs' / f'{language}_{filename}.png')
        self.app.log(self.app.tr('msg_saved').format(file=filename))
        self.destroy()