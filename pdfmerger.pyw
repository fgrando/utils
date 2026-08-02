#!/bin/python3
# pip install tkinterdnd2
# pip install pypdf2


import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import PyPDF2


class PDFCombinerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple PDF Combiner")

        self.pdf_list = []

        # Instructions
        tk.Label(root, text="Drag & Drop PDFs below, arrange them, then combine").pack(pady=5)

        # Listbox to show added PDFs
        self.listbox = tk.Listbox(root, selectmode=tk.SINGLE, width=60, height=15)
        self.listbox.pack(padx=10, pady=5)

        # Button controls
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Add PDFs", command=self.add_pdfs).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Remove", command=self.remove_pdf).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Clear All", command=self.clear_all).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Up", command=lambda: self.move_pdf(-1)).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Down", command=lambda: self.move_pdf(1)).grid(row=0, column=4, padx=5)
        tk.Button(btn_frame, text="Combine", command=self.combine_pdfs).grid(row=0, column=5, padx=5)

        # Enable drag & drop
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind("<<Drop>>", self.drop_files)

    def add_pdfs(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        for f in files:
            if f not in self.pdf_list:
                self.pdf_list.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))

    def remove_pdf(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.listbox.delete(idx)
            self.pdf_list.pop(idx)

    def clear_all(self):
        self.listbox.delete(0, tk.END)
        self.pdf_list.clear()

    def move_pdf(self, direction):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.pdf_list):
            self.pdf_list[idx], self.pdf_list[new_idx] = self.pdf_list[new_idx], self.pdf_list[idx]

            # Refresh listbox
            self.listbox.delete(0, tk.END)
            for f in self.pdf_list:
                self.listbox.insert(tk.END, os.path.basename(f))
            self.listbox.select_set(new_idx)

    def combine_pdfs(self):
        if not self.pdf_list:
            messagebox.showwarning("No PDFs", "Please add some PDF files first.")
            return

        out_file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if not out_file:
            return

        try:
            merger = PyPDF2.PdfMerger()
            for pdf in self.pdf_list:
                merger.append(pdf)

            merger.write(out_file)
            merger.close()

            messagebox.showinfo("Success", f"Combined PDF saved as:\n{out_file}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def drop_files(self, event):
        files = self.root.tk.splitlist(event.data)
        for f in files:
            if f.lower().endswith(".pdf") and f not in self.pdf_list:
                self.pdf_list.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = PDFCombinerApp(root)
    root.mainloop()
