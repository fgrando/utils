#!/bin/python3

import io
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image

DEFAULT_MAX_SIZE = (1024, 768)
DEFAULT_MAX_FILESIZE_KB = 100
SUFFIX = '_lowres'
FILESIZE_SEARCH_ITERATIONS = 16
FILESIZE_MIN_SCALE = 0.01


class MainWidget(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        title = os.path.basename(sys.argv[0])
        self.title(title)
        self.geometry('450x300')

        self.mode = tk.StringVar(value='max')

        controls = tk.Frame(self)
        controls.pack(fill='x', padx=10, pady=10)

        tk.Radiobutton(
            controls, text='Max size (px)', variable=self.mode, value='max',
            command=self.update_mode,
        ).grid(row=0, column=0, sticky='w')
        self.width_entry = tk.Entry(controls, width=6)
        self.width_entry.insert(0, str(DEFAULT_MAX_SIZE[0]))
        self.width_entry.grid(row=0, column=1, padx=2)
        tk.Label(controls, text='x').grid(row=0, column=2)
        self.height_entry = tk.Entry(controls, width=6)
        self.height_entry.insert(0, str(DEFAULT_MAX_SIZE[1]))
        self.height_entry.grid(row=0, column=3, padx=2)

        tk.Radiobutton(
            controls, text='Reduction factor', variable=self.mode, value='factor',
            command=self.update_mode,
        ).grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.factor_combo = ttk.Combobox(controls, width=6, values=['2x', '3x', '4x', '5x', '10x'])
        self.factor_combo.set('2x')
        self.factor_combo.grid(row=1, column=1, padx=2, pady=(8, 0))

        tk.Radiobutton(
            controls, text='Max file size (KB)', variable=self.mode, value='filesize',
            command=self.update_mode,
        ).grid(row=2, column=0, sticky='w', pady=(8, 0))
        self.filesize_entry = tk.Entry(controls, width=6)
        self.filesize_entry.insert(0, str(DEFAULT_MAX_FILESIZE_KB))
        self.filesize_entry.grid(row=2, column=1, padx=2, pady=(8, 0))

        self.update_mode()

        self.status = tk.Label(
            self,
            text=f'Drop image files here\n(saved as *{SUFFIX})',
            font=('Arial', 12),
            wraplength=420,
            justify='center',
        )
        self.status.pack(fill='both', expand=True, padx=10, pady=10)

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop_event)

    def update_mode(self):
        mode = self.mode.get()
        self.width_entry.config(state='normal' if mode == 'max' else 'disabled')
        self.height_entry.config(state='normal' if mode == 'max' else 'disabled')
        self.factor_combo.config(state='normal' if mode == 'factor' else 'disabled')
        self.filesize_entry.config(state='normal' if mode == 'filesize' else 'disabled')

    def drop_event(self, event):
        for f in self.tk.splitlist(event.data):
            self.process(f)

    def get_target_size(self, img):
        if self.mode.get() == 'factor':
            raw = self.factor_combo.get().strip().lower().rstrip('x')
            factor = float(raw)
            if factor <= 0:
                raise ValueError('reduction factor must be greater than 0')
            return (max(1, round(img.width / factor)), max(1, round(img.height / factor)))
        else:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            if width <= 0 or height <= 0:
                raise ValueError('max size must be greater than 0')
            return (width, height)

    def encode_params(self, ext, img):
        ext = ext.lower()
        if ext in ('.jpg', '.jpeg'):
            return 'JPEG', {'quality': 85}
        if ext == '.webp':
            return 'WEBP', {'quality': 85}
        if ext == '.png':
            return 'PNG', {}
        if ext == '.bmp':
            return 'BMP', {}
        if ext == '.gif':
            return 'GIF', {}
        return (img.format or 'PNG'), {}

    def fit_to_filesize(self, img, fmt, save_kwargs, target_bytes):
        def encode(scale):
            w = max(1, round(img.width * scale))
            h = max(1, round(img.height * scale))
            resized = img.resize((w, h), Image.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, format=fmt, **save_kwargs)
            return resized, buf.tell()

        best_img, best_size = encode(1.0)
        if best_size <= target_bytes:
            return best_img

        lo, hi = FILESIZE_MIN_SCALE, 1.0
        for _ in range(FILESIZE_SEARCH_ITERATIONS):
            mid = (lo + hi) / 2
            candidate_img, candidate_size = encode(mid)
            if candidate_size <= target_bytes:
                lo = mid
                best_img = candidate_img
            else:
                hi = mid
        return best_img

    def process(self, file):
        try:
            img = Image.open(file)
        except Exception as e:
            messagebox.showerror('', f'Not an image: {file}\n{e}')
            return

        base, ext = os.path.splitext(file)
        newname = f'{base}{SUFFIX}{ext}'

        if os.path.exists(newname):
            if not messagebox.askyesno('', f'Overwrite {newname}?'):
                return

        fmt, save_kwargs = self.encode_params(ext, img)
        if fmt == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        try:
            if self.mode.get() == 'filesize':
                target_kb = int(self.filesize_entry.get())
                if target_kb <= 0:
                    raise ValueError('max file size must be greater than 0')
                result = self.fit_to_filesize(img, fmt, save_kwargs, target_kb * 1024)
            else:
                target = self.get_target_size(img)
                result = img.copy()
                result.thumbnail(target, Image.LANCZOS)
        except ValueError as e:
            messagebox.showerror('', f'Invalid input: {e}')
            return

        try:
            result.save(newname, format=fmt, **save_kwargs)
        except Exception as e:
            messagebox.showerror('', f'Failed to save {newname}\n{e}')
            return

        size_kb = os.path.getsize(newname) / 1024
        self.status.config(
            text=f'Saved {os.path.basename(newname)}\n{result.width}x{result.height}  ({size_kb:.0f} KB)'
        )


if __name__ == '__main__':
    app = MainWidget()
    app.mainloop()
