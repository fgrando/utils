#!/bin/python3

import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES


class MainWidget(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        title = os.path.basename(sys.argv[0])
        self.title(title)
        self.geometry('450x180')

        self.prefix = '<datetime format here>'

        self.display = tk.Label(self, font=('Arial', 25))
        self.display.pack(fill='both', expand=True)

        label_format = tk.Label(self, text='format:')
        label_format.pack(fill='x')

        self.format_entry = tk.Entry(self)
        self.format_entry.insert(0, '%Y.%m.%d-%H.%M.%S_')
        self.format_entry.pack(fill='x', padx=10, pady=10)

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop_event)

        self.tictac()

    def drop_event(self, event):
        for f in self.tk.splitlist(event.data):
            self.rename(f)

    def tictac(self):
        fmt = self.format_entry.get()
        try:
            self.prefix = datetime.datetime.now().strftime(fmt)
        except ValueError:
            pass
        self.display.config(text=self.prefix)
        self.after(1000, self.tictac)

    def rename(self, file):
        name = f'{self.prefix}{os.path.basename(file)}'
        newname = os.path.join(os.path.dirname(file), name)
        if messagebox.askyesno('', f'Rename to {newname}'):
            print(newname)
            os.rename(file, newname)


if __name__ == '__main__':
    app = MainWidget()
    app.mainloop()
