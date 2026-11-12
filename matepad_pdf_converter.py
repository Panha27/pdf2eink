"""
MatePad Paper PDF Converter  (Windows, Python 3.9+)

Install:   pip install pymupdf
Run:       python matepad_pdf_converter.py
Make .exe: pip install pyinstaller
           pyinstaller --onefile --windowed --name MatePadPDF matepad_pdf_converter.py

What it does for each page:
  1. Detects the real content area and crops the white margins.
  2. Scales the content to fill the MatePad Paper screen (1404 x 1872, 3:4).
  3. Mode A "Keep text":  vector copy (text stays selectable, small file).
     Mode B "E-ink image": grayscale render at device resolution (best for
     scans / light-gray text / heavy graphics), with optional darkening.
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import fitz  # PyMuPDF

# MatePad Paper 10.3" screen in pixels (portrait)
DEV_W, DEV_H = 1404, 1872


# ---------------------------------------------------------------- core logic
def pixel_bbox(page, dpi=50, thr=225):
    """Bounding box (in page points) of non-white content, via a small render."""
    z = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(z, z), colorspace=fitz.csGRAY, alpha=False)
    w, h, s = pix.width, pix.height, pix.samples
    top = None
    bottom = None
    for y in range(h):
        if min(s[y * w:(y + 1) * w]) < thr:
            if top is None:
                top = y
            bottom = y
    if top is None:
        return page.rect  # blank page
    left = right = None
    for x in range(w):
        if min(s[x::w]) < thr:
            if left is None:
                left = x
            right = x
    k = 1.0 / z
    r = fitz.Rect(left * k, top * k, (right + 1) * k, (bottom + 1) * k)
    r += (page.rect.x0, page.rect.y0, page.rect.x0, page.rect.y0)
    return r


def convert_pdf(src_path, dst_path, mode, margin, rotate_landscape, gamma,
                crop, jpg_quality, progress_cb=None):
    src = fitz.open(src_path)
    out = fitz.open()
    n = len(src)
    avail = fitz.Rect(margin, margin, DEV_W - margin, DEV_H - margin)

    for i in range(n):
        page = src[i]
        clip = page.rect
        if crop:
            c = pixel_bbox(page)
            pad = 6
            c = fitz.Rect(c.x0 - pad, c.y0 - pad, c.x1 + pad, c.y1 + pad) & page.rect
            if c.width > 20 and c.height > 20:
                clip = c

        rot = 0
        if rotate_landscape and clip.width > clip.height * 1.15:
            rot = 90
        cw, ch = (clip.height, clip.width) if rot else (clip.width, clip.height)
        scale = min(avail.width / cw, avail.height / ch)

        newp = out.new_page(width=DEV_W, height=DEV_H)

        if mode == "vector":
            newp.show_pdf_page(avail, src, i, clip=clip, rotate=rot)
        else:
            m = fitz.Matrix(scale, scale)  # 1 px per device pixel
            pix = page.get_pixmap(matrix=m, clip=clip,
                                  colorspace=fitz.csGRAY, alpha=False)
            if gamma and abs(gamma - 1.0) > 0.01:
                pix.gamma_with(gamma)
            try:
                data = pix.tobytes("jpeg", jpg_quality=jpg_quality)
            except TypeError:
                data = pix.tobytes("png")
            newp.insert_image(avail, stream=data, rotate=rot)

        if progress_cb:
            progress_cb(i + 1, n)

    try:
        toc = src.get_toc()
        if toc:
            out.set_toc(toc)
    except Exception:
        pass

    out.save(dst_path, garbage=4, deflate=True)
    out.close()
    src.close()


# ---------------------------------------------------------------------- GUI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MatePad Paper PDF Converter")
        self.geometry("720x560")
        self.files = []
        self.out_dir = tk.StringVar(value="")
        self.mode = tk.StringVar(value="vector")
        self.crop = tk.BooleanVar(value=True)
        self.rot = tk.BooleanVar(value=False)
        self.margin = tk.IntVar(value=20)
        self.gamma = tk.DoubleVar(value=1.2)
        self.quality = tk.IntVar(value=80)
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 4}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Add PDF files…", command=self.add_files).pack(side="left")
        ttk.Button(top, text="Add folder…", command=self.add_folder).pack(side="left", padx=6)
        ttk.Button(top, text="Clear", command=self.clear).pack(side="left")

        self.listbox = tk.Listbox(self, height=8, selectmode="extended")
        self.listbox.pack(fill="both", expand=True, **pad)

        of = ttk.Frame(self)
        of.pack(fill="x", **pad)
        ttk.Label(of, text="Output folder:").pack(side="left")
        ttk.Entry(of, textvariable=self.out_dir).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(of, text="Browse…", command=self.pick_out).pack(side="left")

        mf = ttk.LabelFrame(self, text="Mode")
        mf.pack(fill="x", **pad)
        ttk.Radiobutton(mf, text="Keep text (vector) – selectable text, small file",
                        variable=self.mode, value="vector").pack(anchor="w", padx=8)
        ttk.Radiobutton(mf, text="E-ink image – grayscale at device resolution "
                                 "(best for scans / light text)",
                        variable=self.mode, value="image").pack(anchor="w", padx=8)

        of2 = ttk.LabelFrame(self, text="Options")
        of2.pack(fill="x", **pad)
        ttk.Checkbutton(of2, text="Auto-crop white margins",
                        variable=self.crop).grid(row=0, column=0, sticky="w", padx=8)
        ttk.Checkbutton(of2, text="Rotate landscape pages to fill screen",
                        variable=self.rot).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(of2, text="Page margin (px)").grid(row=1, column=0, sticky="w", padx=8)
        ttk.Spinbox(of2, from_=0, to=100, textvariable=self.margin, width=6
                    ).grid(row=1, column=1, sticky="w")
        ttk.Label(of2, text="Darken text (image mode, 1.0–2.0)").grid(row=2, column=0, sticky="w", padx=8)
        ttk.Spinbox(of2, from_=1.0, to=2.0, increment=0.1, textvariable=self.gamma, width=6
                    ).grid(row=2, column=1, sticky="w")
        ttk.Label(of2, text="JPEG quality (image mode)").grid(row=3, column=0, sticky="w", padx=8)
        ttk.Spinbox(of2, from_=40, to=95, textvariable=self.quality, width=6
                    ).grid(row=3, column=1, sticky="w")

        self.bar = ttk.Progressbar(self, mode="determinate")
        self.bar.pack(fill="x", **pad)
        self.status = ttk.Label(self, text="Add PDFs, choose options, then Convert.")
        self.status.pack(fill="x", **pad)
        self.btn = ttk.Button(self, text="Convert", command=self.start)
        self.btn.pack(pady=8)

    # --- file handling
    def add_files(self):
        for f in filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")]):
            self._add(f)

    def add_folder(self):
        d = filedialog.askdirectory()
        if d:
            for name in sorted(os.listdir(d)):
                if name.lower().endswith(".pdf"):
                    self._add(os.path.join(d, name))

    def _add(self, f):
        if f not in self.files:
            self.files.append(f)
            self.listbox.insert("end", f)

    def clear(self):
        self.files.clear()
        self.listbox.delete(0, "end")

    def pick_out(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir.set(d)

    # --- conversion
    def start(self):
        if not self.files:
            messagebox.showwarning("No files", "Please add at least one PDF.")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        total = len(self.files)
        errors = []
        for idx, f in enumerate(self.files, 1):
            base = os.path.splitext(os.path.basename(f))[0]
            folder = self.out_dir.get() or os.path.dirname(f)
            dst = os.path.join(folder, base + "_matepad.pdf")

            def cb(p, n, idx=idx, base=base):
                self.after(0, self._progress, f"[{idx}/{total}] {base}: page {p}/{n}",
                           (p / n) * 100)

            try:
                convert_pdf(f, dst, self.mode.get(), int(self.margin.get()),
                            self.rot.get(), float(self.gamma.get()),
                            self.crop.get(), int(self.quality.get()), cb)
            except Exception as e:  # keep going with the other files
                errors.append(f"{base}: {e}")
        self.after(0, self._done, errors)

    def _progress(self, text, pct):
        self.status.config(text=text)
        self.bar["value"] = pct

    def _done(self, errors):
        self.btn.config(state="normal")
        self.bar["value"] = 100
        if errors:
            self.status.config(text="Finished with errors.")
            messagebox.showerror("Some files failed", "\n".join(errors))
        else:
            self.status.config(text="Done! Copy the *_matepad.pdf files to your MatePad Paper.")
            messagebox.showinfo("Done", "All files converted.")


if __name__ == "__main__":
    App().mainloop()
