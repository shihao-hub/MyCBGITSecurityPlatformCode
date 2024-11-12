import pyperclip

with open(r"PyQt5Project_240628_1.csv", "r", encoding="utf-8") as fr:
    cnt = 0
    while True:
        cnt += 1
        data = fr.read(1024 * 50)
        if not data:
            break
        pyperclip.copy(data)
        input(f"第 {cnt} 次读取，按任意键继续读取")
