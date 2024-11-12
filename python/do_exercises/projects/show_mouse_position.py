import datetime

import pyautogui as auto

PER_INTERVAL = 2

while True:
    auto.sleep(PER_INTERVAL)
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -> {auto.position()}")
