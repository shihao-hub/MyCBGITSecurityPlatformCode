# """
#     实现周期性移动鼠标以避免睡眠，键盘按下 Ctrl + C 终止进程
#     但是有点丑陋...
# """
#
# import datetime
# import sys
# import time
#
# import pyautogui as auto
# import PIL
# import keyboard
# from PIL import Image, ImageGrab
#
# # const
# TIME_INTERVAL = 60
# TIMEOUT = 60 * 60
# left_position, right_position = auto.Point(951, 775), auto.Point(1800, 400)
#
# # mut
# count = 0
#
# # 2024-08-14：想到个新方法
# #   首先，存一张主屏幕的一部分的图片，即我需要匹配的那张图片
# #   然后，每次点击屏幕前，截屏 + 全图定位，如果不存在我的那张图片，就点击左上角
# #   最后，就可以实现这种功能：保证点击 WeLink 的输入框让 WeLink 始终在主页，
# #                           否则就只是点击一下右上角，对正常使用有影响，但是并没有那么大
#
# max_time = time.time() + TIMEOUT
# while time.time() < max_time:
#     # step: 截图
#     screen_image = ImageGrab.grab(bbox=(0, 0, 1920, 1080))
#     screen_image.save("screen_image.jpg")
#     print("start -> ")
#     target_image = Image.open("target_image.jpg")
#     # step: 图片匹配
#     # (Q)!: 为什么匹配不到呢？因为截图工具不是同一个？
#     print(auto.locateOnScreen(target_image, 5))
#
#     # step: 根据匹配结果执行不同的逻辑
#
#     sys.exit(0)
#
#     # 这里要注意不要点到关闭窗口等
#     auto.click(*left_position)
#     auto.moveTo(*right_position)
#
#     count += 1
#     now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     print(f"{now} -> 第 {count - 1} 次点击屏幕或移动鼠标 (interval: {TIME_INTERVAL} s)")
#
#     auto.sleep(TIME_INTERVAL)
#     # 上一行就是在睡眠，所以很难及时执行到下面这段代码，除非开个线程，在线程中终止整个进程？
#     if keyboard.is_pressed("ctrl") and keyboard.is_pressed("c"):
#         print("按下了 ctrl + c，进程终止")
#         break
# print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -> 超时终止 (timeout: {TIMEOUT} s)")
