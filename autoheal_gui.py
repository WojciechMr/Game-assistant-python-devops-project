

# # ======================================== AUTHEAL===========================================
from PIL import ImageFilter
import pytesseract
from PIL import Image
import pyautogui
import time
import threading
import tkinter as tk
import gc   
import json
import keyboard
from prometheus_client import start_http_server, Counter, Gauge
import requests
paused = False
VPS_METRICS_URL = "http://217.160.189.157:9100/update"  # Me VPS 

pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

hp_box = (1871, 148, 20, 12)



autoheal_active = False
# ============ METRICS ===============
hp_gauge = Gauge("bot_hp", "Current Hp")
mana_gauge = Gauge("bot_mana", "Current mana")
targets_counter = Counter("bot_targets_total", "How many times has the monster been found")
heals_counter = Counter("bot_heals_total", "How many times the treatment was used")
mana_uses_counter = Counter("bot_mana_uses_total", "How many times mana was used")

start_http_server(8000, addr='0.0.0.0')

def get_hp_number():
    img = pyautogui.screenshot(region=hp_box)
    img = img.convert('L')
    img = img.point(lambda x: 0 if x < 128 else 255, '1')
    text = pytesseract.image_to_string(img, config='--psm 7 -c tessedit_char_whitelist=0123456789')
    del img
    gc.collect()
    digits = ''.join(filter(str.isdigit, text))
    if digits:
        return int(digits)
    else:
        return None

def cast_heal_spell():
    print("Exura Gran - treatment!")
    pyautogui.press('f1')  

def autoheal_loop():
    global autoheal_active
    last_hp = None
    print("Autoheal enabled")
    while autoheal_active:
        hp = get_hp_number()
        if hp is not None:
            if last_hp != hp:
                print(f"HP change: {last_hp} -> {hp}")
                last_hp = hp
                if hp < int(entry_hp.get()):
                    cast_heal_spell()
                    heals_counter.inc()
                    hp_gauge.set(hp)
                    send_metrics(hp=hp, heals=heals_counter._value.get())
        else:
            print("Failed to read HP.")
        time.sleep(0.1)
    print("Autoheal disabled.")

def toggle_autoheal():
    global autoheal_active
    if autoheal_active:
        autoheal_active = False
        button_autoheal.config(text="Enable Autoheal from WM", bg="lightgreen")
    else:
        autoheal_active = True
        button_autoheal.config(text="Disabled Autoheal from WM", bg="tomato")
        threading.Thread(target=autoheal_loop, daemon=True).start()

# ======================================== AUTOMANA ===========================================

mana_box = (1869, 158, 32, 15)

auto_mana_active = False

def get_mana_number():
    img = pyautogui.screenshot(region=mana_box)
    img = img.convert('L')
    img = img.point(lambda x: 0 if x < 128 else 255, '1')
    text = pytesseract.image_to_string(img, config='--psm 7 -c tessedit_char_whitelist=0123456789')
    del img
    gc.collect()
    digits = ''.join(filter(str.isdigit, text))
    if digits:
        return int(digits)
    else:
        return None

def use_mana_item():
    print("Item used for mana (F12)!")
    pyautogui.press('f12')

def auto_mana_loop():
    global auto_mana_active
    last_mana = None
    print("AutoMana enabled.")
    while auto_mana_active:
        mana = get_mana_number()
        
        if mana is None:
            time.sleep(0.2)
            mana = get_mana_number()

        if mana is not None:
            if last_mana != mana:
                print(f"MANA change: {last_mana} -> {mana}")
                last_mana = mana
                if mana < int(entry_mana.get()):
                    use_mana_item()
                    mana_uses_counter.inc()
                    mana_gauge.set(mana)
                    send_metrics(mana=mana, mana_uses=mana_uses_counter._value.get())
        else:
            print("Failed to read mana.")

        time.sleep(0.1)
    print("AutoMana disabled.")

def toggle_auto_mana():
    global auto_mana_active
    if auto_mana_active:
        auto_mana_active = False
        button_automana.config(text="Enable AutoMana from WM", bg="lightblue")
    else:
        auto_mana_active = True
        button_automana.config(text="Disable AutoMana from WM", bg="deepskyblue")
        threading.Thread(target=auto_mana_loop, daemon=True).start()



# ==================================== AUTOTARGET ================================================


autotarget_active = False
game_region = (1744, 30, 172, 986)

TARGETS = ["rotworm", "cyclops", "orc", "orc warrior", "poison spider", "orc spearman", "skeleton"]

fighting = False
pause_cavebot = False  

def autotarget_loop():
    global autotarget_active, fighting, pause_cavebot
    print("AutoTarget enabled.")
    while autotarget_active:
        screenshot = pyautogui.screenshot(region=game_region)
        screenshot_gray = screenshot.convert('L')
        screenshot_bin = screenshot_gray.point(lambda x: 0 if x < 140 else 255, '1')
        screenshot_bin = screenshot_bin.filter(ImageFilter.SHARPEN)

        boxes = pytesseract.image_to_data(
            screenshot_bin,
            config='--psm 6',
            output_type=pytesseract.Output.DICT
        )

        found = False
        for i, text in enumerate(boxes['text']):
            text_clean = text.strip().lower().replace(" ", "")
            if any(target in text_clean for target in TARGETS) and text_clean != '':
                x_local = boxes['left'][i] + boxes['width'][i] // 2
                y_local = boxes['top'][i] + boxes['height'][i] // 2

                global_x = game_region[0] + x_local
                global_y = game_region[1] + y_local

                print(f"Found '{text_clean}' na pozycji ({global_x}, {global_y})")
                pyautogui.click(global_x, global_y, button='left')
                time.sleep(0.1)
                pyautogui.press('f2')
                targets_counter.inc()  

                found = True
                break
        
        if found:
            fighting = True
            pause_cavebot = True
            send_metrics(targets=targets_counter._value.get())   
        else:
            fighting = False
            pause_cavebot = False
            print("No targets in the game area.")

        del screenshot, screenshot_gray, screenshot_bin
        gc.collect()

        time.sleep(2)

    fighting = False
    pause_cavebot = False
    print("AutoTarget disabled.")


def toggle_autotarget():
    global autotarget_active
    if autotarget_active:
        autotarget_active = False
        button_autotarget.config(text="Enable AutoTarget from WM", bg="khaki")
    else:
        autotarget_active = True
        button_autotarget.config(text="Disable AutoTarget from WM.", bg="yellow")
        threading.Thread(target=autotarget_loop, daemon=True).start()



# ======================================== CAVEBOT ============================================

# ================== KONFIGURACJA ===================
waypoints = []
recorder_waypoints = []
cavebot_active = False
waypoints_file = "waypoints.json"

# używana w AutoTarget
pause_cavebot = False  

# ================== FUNKCJE ===================

def add_waypoint_hotkey():
    x, y = pyautogui.position()
    recorder_waypoints.append((x, y))
    print(f" Waypoint added: {x}, {y}")

def save_waypoints():
    with open(waypoints_file, "w") as f:
        json.dump(recorder_waypoints, f)
    print(f" Waypoints saved: {waypoints_file}")

def load_waypoints():
    global waypoints
    try:
        with open(waypoints_file, "r") as f:
            waypoints = json.load(f)
        print(f" Loaded {len(waypoints)} waypointów.")
    except FileNotFoundError:
        print(" No waypoints, record new ones.")
        waypoints = []

def cavebot_loop():
    global cavebot_active, waypoints, pause_cavebot
    while cavebot_active:
        if not waypoints:
            time.sleep(1)
            continue

        for x, y in waypoints:
            if not cavebot_active:
                break

            
            while pause_cavebot and cavebot_active:
                time.sleep(0.5)

            pyautogui.click(x, y)
            print(f" I click on the point: {x}, {y}")
            time.sleep(2.0)  

def toggle_cavebot():
    """Start/Stop CaveBot"""
    global cavebot_active
    if cavebot_active:
        cavebot_active = False
        button_cavebot.config(text="Start CaveBot")
        print(" CaveBot stopped.")
    else:
        load_waypoints()
        cavebot_active = True
        button_cavebot.config(text="Stop CaveBot")
        threading.Thread(target=cavebot_loop, daemon=True).start()
        print(" CaveBot started.")

def clear_waypoints():
    global recorder_waypoints, waypoints
    recorder_waypoints = []
    waypoints = []
    try:
        with open(waypoints_file, "w") as f:
            json.dump([], f)
        print("Waypoints cleared.")
    except:
        pass


def remove_last_waypoint():
    global recorder_waypoints
    if recorder_waypoints:
        removed = recorder_waypoints.pop()
        print(f" Last waypoint removed: {removed}")
    else:
        print("No waypoints to remove.")

def toggle_pause():
    global paused
    paused = not paused
    if paused:
        print("⏸ All pause.")
        set_buttons_state('disabled')  
    else:
        print(" All resumed.")
        set_buttons_state('normal')  


# -------------------------------------------- GUI ------------------------------------------------------

root = tk.Tk()
root.title("Auto WojciechM")
root.geometry("400x700")
root.resizable(False, False)

button_autoheal = tk.Button(root, text="Enable Autoheal", command=toggle_autoheal, width=30, height=2, bg="lightgreen")
button_autoheal.pack(pady=5)
label_hp = tk.Label(root, text="HP Threshold:")
label_hp.pack()
entry_hp = tk.Entry(root)
entry_hp.insert(0, "220")  
entry_hp.pack()

button_automana = tk.Button(root, text="Enable AutoMana", command=toggle_auto_mana, width=30, height=2, bg="lightblue")
button_automana.pack(pady=5)
label_mana = tk.Label(root, text="Mana Threshold:")
label_mana.pack()
entry_mana = tk.Entry(root)
entry_mana.insert(0, "500")  # domyślna wartość
entry_mana.pack()

button_autotarget = tk.Button(root, text="Enable AutoTarget", command=toggle_autotarget, width=30, height=2, bg="khaki")
button_autotarget.pack(pady=5)


button_save = tk.Button(root, text="Save waypoints", command=save_waypoints)
button_save.pack(fill="x")

button_load = tk.Button(root, text="Load waypoints", command=load_waypoints)
button_load.pack(fill="x")

button_cavebot = tk.Button(root, text="Start CaveBot", command=toggle_cavebot)
button_cavebot.pack(fill="x")


button_remove = tk.Button(root, text="Remove last waypoint", command=remove_last_waypoint)
button_remove.pack(fill="x")

button_exit = tk.Button(root, text="Close", command=root.destroy, width=30, height=2, bg="gray")
button_exit.pack(pady=5)

# F9 dodaje waypoint pod kursorem
keyboard.add_hotkey("F9", add_waypoint_hotkey)
print("Press F9 to add a waypoint ( -  ends the program).")

def close_gui():
    print("GUI closed with a key '-'")
    root.destroy()

def hotkey_listener():
    keyboard.wait("-")  
    close_gui()


def send_metrics(hp=None, mana=None, targets=None, heals=None, mana_uses=None):
    data = {}
    if hp is not None: data["hp"] = hp
    if mana is not None: data["mana"] = mana
    if targets is not None: data["targets"] = targets
    if heals is not None: data["heals"] = heals
    if mana_uses is not None: data["mana_uses"] = mana_uses
    try:
        requests.post(VPS_METRICS_URL, json=data)
    except Exception as e:
        print(f"Failed to send metrics: {e}")
threading.Thread(target=hotkey_listener, daemon=True).start()


root.mainloop()
