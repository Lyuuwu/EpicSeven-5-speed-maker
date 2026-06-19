import ctypes
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
import cv2
import numpy as np
from adbutils import adb
from PIL import Image
from tkinter import messagebox

from canvas import CropWindow

@dataclass
class TranslationClass:
    title: str
    language_label: str
    theme_label: str
    light: str
    dark: str
    addr_label: str
    addr_placeholder: str
    points_label: str
    points_placeholder: str
    start: str
    stop: str
    msg_need_points: str
    msg_points_digit: str
    msg_start: str
    msg_stop: str
    msg_conf: str
    msg_found: str
    msg_loading: str
    msg_running: str
    msg_not_enough_points: str
    msg_nxt_btn_not_found: str
    update_image: str
    crop_title: str
    crop_target: str
    crop_hint: str
    crop_save: str
    crop_clear: str
    msg_no_region: str
    msg_saved: str
    
    def get(self, key, default=None):
        return getattr(self, key, default)
    

TRANSLATIONS = {
    'zh-TW': TranslationClass(
        title='E7 5 speed maker',
        language_label='語言: ',
        theme_label='主題: ',
        light='淺色',
        dark='深色',
        addr_label='addr:',
        addr_placeholder='必填',
        points_label='目前點數: ',
        points_placeholder='必填',
        start='開始',
        stop='停止',
        msg_need_points='請先輸入目前點數',
        msg_points_digit='點數必須是數字',
        msg_start='開始執行，目前點數 {points}',
        msg_loading='[讀取畫面] 跳過',
        msg_stop='已停止',
        msg_conf='最高信心: {conf:.1f}%',
        msg_found='找到目標!! 停止執行',
        msg_running='正在執行中',
        update_image='更新圖片',
        crop_title='截圖裁切',
        crop_target='要取代的圖片', crop_hint='拖曳框選；有框後拖空白平移、拖框內移動、滾輪縮放',
        crop_save='儲存', crop_clear='清空', msg_no_region='請先選取範圍', msg_saved= '已更新! {file}',
        msg_nxt_btn_not_found='[錯誤] 變更輔助能力值 按鈕無法找到',
        msg_not_enough_points='點數不足'
    ),
    
    'en': TranslationClass(
        title='E7 5 speed maker',
        language_label='language: ',
        theme_label='theme: ',
        light='Light',
        dark='Dark',
        addr_label='addr:',
        addr_placeholder='Required',
        points_label='Current points',
        points_placeholder='Required',
        start='Start',
        stop='Stop',
        msg_need_points='Please enter current points first',
        msg_points_digit='Points must be a number',
        msg_start='Started. Current points {points}',
        msg_loading='[detect loading] skip.',
        msg_stop='Stopped',
        msg_conf='confidence {conf:.1f}%',
        msg_found='Target found, stopped',
        msg_running='Already running',
        update_image='Update images',
        crop_title='Crop screenshot',
        crop_target='Replace which image:',
        crop_hint='Drag to select; once selected, drag empty to pan, drag box to move, wheel to zoom',
        crop_save='Save',
        crop_clear='Clear',
        msg_no_region='Please select a region first',
        msg_saved='Updated {file}',
        msg_nxt_btn_not_found='[error] Change Substats button cannot found',
        msg_not_enough_points='not enough points'
    )
}

LANGUAGES = {'繁體中文': 'zh-TW', 'English': 'en'}
LANGUAGES_ = {'zh-TW': '繁體中文', 'en': 'English'}

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / 'config.json'
IMGS_DIR    = ROOT / 'imgs'

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def save_json(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(content, indent=4))

def load_img(path):
    return cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)

def get_tar_shape(img, max_loc):
    ''' return top_l and bot_r for TM_CCOEFF_NORMED matching method '''
    h, w = img.shape[:2]
    
    top_l = max_loc
    bot_r = (top_l[0] + w, top_l[1] + h)
    return top_l, bot_r

def get_center(top_l, bot_r):
    return ((top_l[0] + bot_r[0]) / 2, (top_l[1] + bot_r[1]) / 2)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.after(300, self._set_app_icon)
        
        try:
            self.cfg = load_json(CONFIG_PATH)
        
        except FileNotFoundError:
            messagebox.showerror(
                'FILE NOT FOUND',
                'config.json does not exist.\nplease make sure the config file is at the same directory with .exe file.',
                parent=self
            )
            self.destroy()
            return
        
        # -- basic setting ---
        self.language = self.cfg.get('language', 'zh-TW')
        self.theme    = self.cfg.get('theme', 'Dark')
        ctk.set_appearance_mode(self.theme)
        
        # --- background ---
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        self.geometry('420x520')
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)
        
        # --- row 0 ---
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, columnspan=2,
                            padx=10, pady=10, sticky='ew')
        
        self.lang_label = ctk.CTkLabel(self.top_frame, text='')
        self.lang_label.grid(row=0, column=0, padx=(10, 4), pady=10)
        self.lang_menu = ctk.CTkOptionMenu(
            self.top_frame,
            values = list(LANGUAGES.keys()),
            command=self.on_language_change,
        )
        self.lang_menu.grid(row=0, column=1, padx=(0, 16), pady=10)
        
        self.theme_label = ctk.CTkLabel(self.top_frame, text='')
        self.theme_label.grid(row=0, column=2, padx=(0, 4), pady=10)
        self.theme_switch = ctk.CTkSwitch(self.top_frame, text='',
                                          command=self.on_theme_toggle)
        self.theme_switch.grid(row=0, column=3, padx=(0, 10), pady=10)
        
        if self.theme == 'Dark':
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
            
        # --- row 1: addr/points ---
        self.r1_frame = ctk.CTkFrame(self)
        self.r1_frame.grid(row=1, column=0, columnspan=4,
                           padx=10, pady=10, sticky='ew')
        
        self.addr_label = ctk.CTkLabel(self.r1_frame, text='')
        self.addr_label.grid(row=1, column=0, padx=5, pady=10, sticky='e')
        self.addr_entry = ctk.CTkEntry(self.r1_frame)
        self.addr_entry.grid(row=1, column=1, padx=5, pady=10, sticky='ew')
        if self.cfg.get('addr'):
            self.addr_entry.insert(0, self.cfg.get('addr').strip())

        self.points_label = ctk.CTkLabel(self.r1_frame, text='')
        self.points_label.grid(row=1, column=2, padx=5, pady=10, stick='e')
        self.points_entry = ctk.CTkEntry(self.r1_frame)
        self.points_entry.grid(row=1, column=3, padx=5, pady=10, sticky='ew')
        
        # --- row 2: start/stop ---
        self.start_btn = ctk.CTkButton(self, text='', command=self.on_start)
        self.start_btn.grid(row=2, column=0, padx=10, pady=10, sticky='ew')
        self.stop_btn = ctk.CTkButton(self, text='', command=self.on_stop)
        self.stop_btn.grid(row=2, column=1, padx=10, pady=10, sticky='ew')
        
        # --- row 3: update image ---
        self.update_img_btn = ctk.CTkButton(self, text='', command=self.open_crop_windw)
        self.update_img_btn.grid(row=3, column=0, columnspan=2,
                                 padx=10, pady=(0, 10), sticky='ew')
        
        # --- row 4: log box ---
        self.log_box = ctk.CTkTextbox(self)
        self.log_box.grid(row=4, column=0, columnspan=2,
                  padx=10, pady=10, sticky='nsew')
        self.log_box.configure(state='disabled')
        
        self.lang_menu.set(LANGUAGES_[self.language])
        self.update_texts()

    def _set_app_icon(self):
        self.iconbitmap(str(ROOT / 'icon.ico'))

    def save_cfg(self):
        save_json(CONFIG_PATH, self.cfg)
    
    def tr(self, key):
        ''' translate '''
        return TRANSLATIONS[self.language].get(key)
    
    def update_texts(self):
        self.title(self.tr('title'))
        self.lang_label.configure(text=self.tr('language_label'))
        self.theme_label.configure(text=self.tr('theme_label'))
        self.addr_label.configure(text=self.tr('addr_label'))
        self.addr_entry.configure(placeholder_text=self.tr('points_placeholder'))
        self.points_label.configure(text=self.tr('points_label'))
        self.points_entry.configure(placeholder_text=self.tr('points_placeholder'))
        self.start_btn.configure(text=self.tr('start'))
        self.stop_btn.configure(text=self.tr('stop'))
        self.update_img_btn.configure(text=self.tr('update_image'))
    
    def on_language_change(self, choice):
        self.language = LANGUAGES[choice]
        self.update_texts()
        
        self.cfg['language'] = self.language
        self.save_cfg()

    def on_theme_toggle(self):
        self.theme = 'Dark' if self.theme_switch.get() == 1 else 'Light'
        ctk.set_appearance_mode(self.theme)
        self.theme_switch.configure(text=self.tr(self.theme.lower()))
        
        self.cfg['theme'] = self.theme
        self.save_cfg()
        
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_box.configure(state='normal')
        self.log_box.insert('end', f'[{timestamp}] {message}\n')
        self.log_box.see('end')
        self.log_box.configure(state='disabled')
    
    def on_start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.log(self.tr('msg_running'))
            return
        
        points = self.points_entry.get().strip()
        if not points:
            self.log(self.tr('msg_need_points'))
            return
        
        if not points.isdigit():
            self.log(self.tr('msg_points_digit'))
            return
        
        self.log(self.tr('msg_start').format(points=points))
        self.set_running_ui(True)
        self.stop_event.clear()     # remove stopping flag
        
        # build thread
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()
    
    def on_stop(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set()
            self.log(self.tr('msg_stop'))
    
    def worker_loop(self):        
        try:
            device = self.try_connect(self.addr_entry.get().strip())
            digit_img   = load_img(IMGS_DIR / 'digit5.png')
            loading_img = load_img(IMGS_DIR / 'loading.png')
            next_btn    = load_img(IMGS_DIR / f'{self.language}_next.png')
            method = cv2.TM_CCOEFF_NORMED
            
        except Exception as e:
            self.log(e)
            self.on_stop()

        while not self.stop_event.is_set():
            screenshot = np.asarray(device.screenshot())
            
            # --- match loading ---
            loading_match = cv2.matchTemplate(screenshot, loading_img, method)
            _, max_val, _, _ = cv2.minMaxLoc(loading_match)
            
            if max_val > 0.9:
                self.log('msg_loading')
                time.sleep(5)
                continue
            
            # --- match 5 speed ---
            tar_matching = cv2.matchTemplate(screenshot, digit_img, method)
            _, max_val, min_loc, max_loc = cv2.minMaxLoc(tar_matching)
            
            self.log(self.tr('msg_conf').format(conf=max_val*100))
            
            if max_val < 0.9:
                points = int(self.points_entry.get())
                if points < 20:
                    self.log(self.tr('msg_not_enough_points'))
                    self.on_stop()
                    break
                
                # not found
                nxt_matching = cv2.matchTemplate(screenshot, next_btn, method)
                _, max_val, _, max_loc = cv2.minMaxLoc(nxt_matching)
                
                if max_val < 0.9:
                    self.log(self.tr('msg_nxt_btn_not_found'))
                    self.on_stop()
                    break
                
                top_l, bot_r = get_tar_shape(next_btn, max_loc)
                cx, cy = get_center(top_l, bot_r)
                device.click(cx, cy)
                
                self.points_entry.configure(state='normal')
                self.points_entry.delete(0, 'end')
                self.points_entry.insert(0, f'{points - 20}')
                self.points_entry.configure(state='disabled')
                
                time.sleep(2)
            
            else:
                self.log(self.tr('msg_found'))
                break
        
        self.after(0, self.set_running_ui, False)
    
    def try_connect(self, addr):
        adb.connect(addr, timeout=10)
            
        devices = adb.list(extended=True)
        flg = False
        for info in devices:
            if info.serial == addr and info.state == 'device':
                flg = True
                break
                
        if not flg:
            raise RuntimeError(f'ADB cannot connect to the device: {addr}')
        
        self.cfg['addr'] = addr
        self.save_cfg()
        
        device = adb.device(serial=addr)
        return device
        
    def set_running_ui(self, running):
        state = 'disabled' if running else 'normal'
        self.start_btn.configure(state=state)
        self.addr_entry.configure(state=state)
        self.points_entry.configure(state=state)
    
    def get_screenshot(self):
        try:
            device = self.try_connect(self.addr_entry.get().strip())
        except Exception as e:
            self.log(e)
            return None
        
        return Image.fromarray(np.array(device.screenshot()))
    
    def open_crop_windw(self):
        screenshot = self.get_screenshot()
        if screenshot is None:
            self.log('cannot get screenshot!')
        CropWindow(self, screenshot)

if __name__ == '__main__':
    # 整個程式停用輸入法（本 App 所有欄位都是 ASCII/數字，不需要中文輸入）。
    # 必須在建立任何視窗之前呼叫，才會對 Tk 主視窗生效。
    try:
        ctypes.windll.imm32.ImmDisableIME(-1)   # -1 = 對整個行程的所有執行緒生效
    except Exception as e:
        print('ImmDisableIME failed:', e)

    app = App()
    app.mainloop()