import pprint
import tkinter

from tkinter import ttk
from tkinter import Widget

pprint.pprint(tkinter.Toplevel.__mro__)

root = tkinter.Tk()


li = ['C', 'python', 'php', 'html', 'SQL', 'java']
movie = ['CSS', 'jQuery', 'Bootstrap']

button = ttk.Button(root)
button2 = tkinter.Button(root)
listb = tkinter.Listbox(root)
listb2 = tkinter.Listbox(root)

for item in li:
    listb.insert(0, item)

for item in movie:
    listb2.insert(0, item)

button.pack()
button2.pack()
listb.pack()  # 将小部件放置到主窗口中
listb2.pack()
root.mainloop()  # 进入消息循环
