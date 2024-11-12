"""
    2024 简易考研倒计时
"""

import datetime

date1_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date2_str = "2024-12-23 23:59:59"
date1 = datetime.datetime.strptime(date1_str, "%Y-%m-%d %H:%M:%S")
date2 = datetime.datetime.strptime(date2_str, "%Y-%m-%d %H:%M:%S")
print(date2 - date1)
