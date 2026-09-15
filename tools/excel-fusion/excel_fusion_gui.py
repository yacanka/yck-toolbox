"""Lightweight desktop shell. Start with python excel_fusion_gui.py."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path


def open_path(path: Path) -> None:
    """Open an existing local result with the OS default application."""
    if not path.exists():
        raise FileNotFoundError("Dosya taşınmış veya silinmiş olabilir.")
    if sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def main() -> None:
    started = time.perf_counter()
    # Import Tk only for the GUI; headless service tests do not require a display.
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from fusion_service import RunOptions, run_report, validate_paths

    root = tk.Tk()
    root.title("Excel Fusion")
    root.geometry("920x760")
    root.minsize(760, 680)
    root.configure(background="#FFFFFF")
    family = "Helvetica Neue" if sys.platform == "darwin" else "Arial"
    root.option_add("*Font", (family, 11))
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background="#FFFFFF", foreground="#191919", font=(family, 11))
    style.configure("TFrame", background="#FFFFFF")
    style.configure("TLabel", background="#FFFFFF")
    style.configure("Muted.TLabel", foreground="#606060")
    style.configure("Title.TLabel", font=(family, 30, "bold"))
    style.configure("Step.TLabel", foreground="#002FA7", font=(family, 20, "bold"))
    style.configure("Heading.TLabel", font=(family, 13, "bold"))
    style.configure("TButton", padding=(14, 9), background="#F7F7F8", borderwidth=1)
    style.configure("Primary.TButton", background="#002FA7", foreground="#FFFFFF")
    style.map("Primary.TButton", background=[("disabled", "#E5E5E5"), ("active", "#002FA7")],
              foreground=[("disabled", "#606060")])
    style.configure("TEntry", padding=7, fieldbackground="#FFFFFF")
    style.configure("TCombobox", padding=7, fieldbackground="#FFFFFF")
    style.configure("Horizontal.TProgressbar", background="#002FA7", troughcolor="#F7F7F8")

    class Application:
        def __init__(self):
            self.events = queue.Queue()
            self.running = False
            self.result = None
            self.controls = []
            self.source = tk.StringVar()
            self.output = tk.StringVar(value=str(Path.home() / "Ana_Rapor.xlsx"))
            self.mode = tk.StringVar(value="Alt klasöre göre")
            self.include_root = tk.BooleanVar(value=False)
            self.overwrite = tk.BooleanVar(value=False)
            self.fail_on_error = tk.BooleanVar(value=False)
            self.header_row = tk.StringVar(value="12")
            self.search_end = tk.StringVar(value="40")
            self.status = tk.StringVar(value="Başlamak için kaynak klasörünü seçin.")
            self.summary = tk.StringVar(value="Henüz işlem yapılmadı.")
            self.build()
            root.protocol("WM_DELETE_WINDOW", self.close)
            root.after(100, self.poll)

        def build(self):
            # Scrollable form keeps all controls reachable at high display scaling.
            canvas = tk.Canvas(root, background="#FFFFFF", highlightthickness=0)
            scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
            scrollbar.pack(side="right", fill="y")
            canvas.pack(fill="both", expand=True)
            body = ttk.Frame(canvas, padding=(32, 24))
            window = canvas.create_window((0, 0), window=body, anchor="nw")
            body.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
            body.columnconfigure(1, weight=1)
            ttk.Label(body, text="Excel Fusion", style="Title.TLabel").grid(
                row=0, column=0, columnspan=3, sticky="w")
            ttk.Label(body, text="Excel dosyalarınızı tek, denetlenebilir bir raporda birleştirin.",
                      style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 20))
            self.section(body, 2, "01", "Dosyalar")
            self.path_field(body, 3, "Kaynak klasör", self.source, self.choose_source)
            self.path_field(body, 4, "Çıktı raporu", self.output, self.choose_output)
            ttk.Label(body, text="XLSX, XLSM, XLTX, XLTM, XLS ve XLSB • Kaynak dosyalar korunur.",
                      style="Muted.TLabel").grid(row=5, column=1, columnspan=2, sticky="w", pady=(0, 12))
            self.section(body, 6, "02", "Birleştirme ayarları")
            ttk.Label(body, text="Gruplama").grid(row=7, column=0, sticky="w", padx=(0, 16))
            mode = ttk.Combobox(body, textvariable=self.mode, state="readonly",
                                values=("Alt klasöre göre", "Sayfa adına göre"))
            mode.grid(row=7, column=1, columnspan=2, sticky="ew", pady=6)
            mode.bind("<<ComboboxSelected>>", lambda _: self.update_mode())
            self.controls.append((mode, "readonly"))
            self.root_check = self.check(body, 8, "Ana klasördeki dosyaları da dahil et", self.include_root)
            settings = ttk.Frame(body)
            settings.grid(row=9, column=1, columnspan=2, sticky="ew", pady=8)
            for index, (label, value) in enumerate((("Başlık satırı", self.header_row),
                                                     ("Arama son satırı", self.search_end))):
                ttk.Label(settings, text=label).grid(row=0, column=index * 2, padx=(0, 8))
                entry = ttk.Entry(settings, textvariable=value, width=7)
                entry.grid(row=0, column=index * 2 + 1, padx=(0, 20))
                self.controls.append((entry, "normal"))
            self.check(body, 10, "Mevcut Excel Fusion raporunu yenile", self.overwrite)
            self.check(body, 11, "Kaynak hatası varsa rapor oluşturma", self.fail_on_error)
            self.section(body, 12, "03", "Raporu oluştur")
            actions = ttk.Frame(body)
            actions.grid(row=13, column=0, columnspan=3, sticky="w", pady=(0, 8))
            for text, dry, button_style in (("Ön kontrol", True, "TButton"),
                                             ("Rapor oluştur", False, "Primary.TButton")):
                button = ttk.Button(actions, text=text, style=button_style,
                                    command=lambda value=dry: self.start(value))
                button.pack(side="left", padx=(0, 10))
                self.controls.append((button, "normal"))
            ttk.Label(body, text="Ön kontrol Excel üretmez; .log ve .denetim.jsonl dosyalarını yazar.",
                      style="Muted.TLabel").grid(row=14, column=0, columnspan=3, sticky="w")
            self.progress = ttk.Progressbar(body, mode="indeterminate")
            self.progress.grid(row=15, column=0, columnspan=3, sticky="ew", pady=(16, 10))
            ttk.Label(body, textvariable=self.status, wraplength=670).grid(
                row=16, column=0, columnspan=3, sticky="w")
            ttk.Label(body, textvariable=self.summary, style="Muted.TLabel", wraplength=670).grid(
                row=17, column=0, columnspan=3, sticky="w", pady=(8, 10))
            results = ttk.Frame(body)
            results.grid(row=18, column=0, columnspan=3, sticky="w")
            self.open_report = ttk.Button(results, text="Raporu aç", state="disabled",
                                          command=lambda: self.open_result("output"))
            self.open_report.pack(side="left", padx=(0, 10))
            self.open_folder = ttk.Button(results, text="Çıktı klasörünü aç", state="disabled",
                                          command=lambda: self.open_result("folder"))
            self.open_folder.pack(side="left")

        def section(self, body, row, number, title):
            ttk.Separator(body).grid(row=row, column=0, columnspan=3, sticky="new")
            ttk.Label(body, text=number, style="Step.TLabel").grid(
                row=row, column=0, sticky="w", pady=(14, 12))
            ttk.Label(body, text=title, style="Heading.TLabel").grid(
                row=row, column=1, columnspan=2, sticky="w", pady=(14, 12))

        def path_field(self, body, row, title, variable, command):
            ttk.Label(body, text=title).grid(row=row, column=0, sticky="w", padx=(0, 16))
            entry = ttk.Entry(body, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", pady=6)
            button = ttk.Button(body, text="Seç…", command=command)
            button.grid(row=row, column=2, padx=(10, 0))
            self.controls.extend(((entry, "normal"), (button, "normal")))

        def check(self, body, row, text, variable):
            widget = ttk.Checkbutton(body, text=text, variable=variable)
            widget.grid(row=row, column=1, columnspan=2, sticky="w", pady=4)
            self.controls.append((widget, "normal"))
            return widget

        def update_mode(self):
            sheet_mode = self.mode.get() == "Sayfa adına göre"
            self.root_check.configure(state="disabled" if self.running or sheet_mode else "normal",
                                      text="Ana klasördeki dosyalar otomatik dahil edilir" if sheet_mode
                                      else "Ana klasördeki dosyaları da dahil et")

        def choose_source(self):
            selected = filedialog.askdirectory(parent=root, title="Kaynak Excel klasörü", mustexist=True)
            if selected:
                self.source.set(selected)

        def choose_output(self):
            selected = filedialog.asksaveasfilename(parent=root, title="Raporun kaydedileceği yer",
                                                    defaultextension=".xlsx", initialfile="Ana_Rapor.xlsx",
                                                    filetypes=[("Excel raporu", "*.xlsx")])
            if selected:
                self.output.set(selected)

        def start(self, dry_run):
            if self.running:
                return
            try:
                options = RunOptions(
                    self.source.get(), self.output.get(),
                    "sheet_name" if self.mode.get() == "Sayfa adına göre" else "subfolder",
                    self.include_root.get(), self.overwrite.get(), dry_run,
                    int(self.header_row.get()), int(self.search_end.get()), self.fail_on_error.get())
                options.config()
                validate_paths(options)
            except (ValueError, OSError) as exc:
                messagebox.showerror("Ayarları kontrol edin", str(exc), parent=root)
                return
            self.result = None
            self.running = True
            self.summary.set("İşlem sürerken uygulamayı açık tutun.")
            self.status.set("İşlem başlatılıyor…")
            for widget, _ in self.controls:
                widget.configure(state="disabled")
            self.open_report.configure(state="disabled")
            self.open_folder.configure(state="disabled")
            self.progress.start(15)
            threading.Thread(target=self.work, args=(options,), daemon=False).start()

        def work(self, options):
            # The worker never touches Tk objects. Only the UI thread consumes events.
            try:
                result = run_report(options, lambda text: self.events.put(("progress", text)))
                self.events.put(("done", result))
            except Exception as exc:  # noqa: BLE001 -- worker boundary must report failures to Tk.
                self.events.put(("error", f"{type(exc).__name__}: {exc}"))

        def poll(self):
            try:
                while True:
                    kind, value = self.events.get_nowait()
                    if kind == "progress":
                        self.status.set(value)
                    else:
                        self.finish(kind, value)
            except queue.Empty:
                pass
            root.after(100, self.poll)

        def finish(self, kind, value):
            self.running = False
            self.progress.stop()
            for widget, state in self.controls:
                widget.configure(state=state)
            self.update_mode()
            if kind == "error":
                self.status.set("İşlem tamamlanamadı.")
                self.summary.set("Çıktı Excel'de açıksa kapatın. Varsa .log ve .denetim.jsonl dosyalarını inceleyin.")
                messagebox.showerror("İşlem tamamlanamadı", value, parent=root)
                return
            self.result = value
            title = "Rapor oluşturuldu." if value.output else "Ön kontrol tamamlandı."
            if not value.records:
                title += " Birleştirilecek kayıt bulunamadı; denetimi kontrol edin."
            elif value.errors or value.warnings:
                title += " Denetim sonuçlarını inceleyin."
            self.status.set(title)
            self.summary.set(f"{value.records} kayıt  ·  {value.groups} grup  ·  {value.warnings} uyarı  ·  "
                             f"{value.errors} hata  ·  {value.quarantined} karantina satırı")
            self.open_report.configure(state="normal" if value.output else "disabled")
            self.open_folder.configure(state="normal")

        def open_result(self, kind):
            if self.result is None:
                return
            path = self.result.audit.parent if kind == "folder" else self.result.output
            if path is not None:
                try:
                    open_path(path)
                except OSError as exc:
                    messagebox.showerror("Açılamadı", str(exc), parent=root)

        def close(self):
            if self.running:
                messagebox.showinfo("İşlem sürüyor", "Rapor tamamlandığında pencereyi kapatabilirsiniz.", parent=root)
                return
            root.destroy()

    Application()
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        from fusion_smoke import check

        root.update()
        try:
            check(Path(sys.argv[2]), started)
        finally:
            root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
