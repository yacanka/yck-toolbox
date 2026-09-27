"""Turkish desktop shell; the Excel Fusion engine remains unchanged."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from fusion_service import RunOptions, run_report, validate_paths
from fusion_settings import SettingsError, default_settings, load_profile, save_profile

# Keep imports display-free for CLI/service users and packaging tests.
tk = ttk = messagebox = filedialog = None


def load_tk():
    global tk, ttk, messagebox, filedialog
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk


def open_path(path: Path) -> None:
    """Open an existing local result with the OS default application."""
    if not path.exists():
        raise FileNotFoundError('Dosya taşınmış veya silinmiş olabilir.')
    if sys.platform == 'win32':
        os.startfile(str(path))
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(path)])


def configure_window(root):
    root.title('Excel Fusion')
    root.geometry('1040x850')
    root.minsize(760, 680)
    root.configure(background='#FFFFFF')
    family = 'Helvetica Neue' if sys.platform == 'darwin' else 'Arial'
    root.option_add('*Listbox.Font', (family, 11))
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background='#FFFFFF', foreground='#191919', font=(family, 11))
    style.configure('TFrame', background='#FFFFFF')
    style.configure('TLabel', background='#FFFFFF')
    style.configure('Muted.TLabel', foreground='#606060')
    style.configure('Title.TLabel', font=(family, 28, 'bold'))
    style.configure('Heading.TLabel', font=(family, 11, 'bold'))
    style.configure('TButton', padding=(10, 7), background='#F7F7F8', borderwidth=1)
    style.configure('Primary.TButton', background='#002FA7', foreground='#FFFFFF')
    style.map('Primary.TButton', background=[('disabled', '#E5E5E5'), ('active', '#002FA7')],
              foreground=[('disabled', '#606060')])
    style.configure('TEntry', padding=6, fieldbackground='#FFFFFF')
    style.configure('TCombobox', padding=6, fieldbackground='#FFFFFF')
    style.configure('TNotebook', borderwidth=0)
    style.configure('TNotebook.Tab', padding=(14, 10), background='#F7F7F8')
    style.map('TNotebook.Tab', background=[('selected', '#002FA7')], foreground=[('selected', '#FFFFFF')])
    style.configure('Treeview', rowheight=28, fieldbackground='#FFFFFF')
    style.configure('Horizontal.TProgressbar', background='#002FA7', troughcolor='#F7F7F8')


class Application:
    def __init__(self, root):
        load_tk()
        from fusion_settings_ui import SettingsPanel

        self.root = root
        configure_window(root)
        self.events = queue.Queue()
        self.running, self.dirty = False, False
        self.result, self.profile_path = None, None
        self.controls = []
        self.profile = tk.StringVar(root, value='Motor varsayılanları')
        self.status = tk.StringVar(root, value='Başlamak için kaynak klasörünü seçin.')
        self.summary = tk.StringVar(root, value='Henüz işlem yapılmadı.')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        self.build_header()
        self.panel = SettingsPanel(root, default_settings(), self.mark_dirty)
        self.panel.grid(row=1, column=0, sticky='nsew', padx=24)
        self.build_footer()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_id = root.after(100, self.poll)

    def button(self, parent, label, command, primary=False):
        button = ttk.Button(parent, text=label, command=command,
                            style='Primary.TButton' if primary else 'TButton')
        button.pack(side='left', padx=(0, 8))
        self.controls.append(button)
        return button

    def build_header(self):
        header = ttk.Frame(self.root, padding=(24, 20, 24, 12))
        header.grid(row=0, column=0, sticky='ew')
        ttk.Label(header, text='Excel Fusion', style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text='Kaynaklarınızı seçin, sütunları ve kuralları düzenleyin, raporu oluşturun.',
                  style='Muted.TLabel').pack(anchor='w', pady=(2, 12))
        actions = ttk.Frame(header)
        actions.pack(fill='x')
        self.button(actions, 'Profil yükle', self.load_profile)
        self.button(actions, 'Profil kaydet', self.save_profile)
        self.button(actions, 'Varsayılanlara dön', self.reset)
        ttk.Label(header, textvariable=self.profile, style='Muted.TLabel', wraplength=700).pack(anchor='w', pady=(8, 0))

    def build_footer(self):
        footer = ttk.Frame(self.root, padding=(24, 8, 24, 16))
        footer.grid(row=2, column=0, sticky='ew')
        ttk.Separator(footer).pack(fill='x', pady=(0, 12))
        actions = ttk.Frame(footer)
        actions.pack(fill='x')
        self.button(actions, 'Ön kontrol', lambda: self.start(True))
        self.button(actions, 'Rapor oluştur', lambda: self.start(False), primary=True)
        self.open_folder = ttk.Button(actions, text='Çıktı klasörü', state='disabled',
                                      command=lambda: self.open_result('folder'))
        self.open_folder.pack(side='right')
        self.open_report = ttk.Button(actions, text='Raporu aç', state='disabled',
                                      command=lambda: self.open_result('output'))
        self.open_report.pack(side='right', padx=8)
        ttk.Label(footer, text='Ön kontrol Excel üretmez; .log ve .denetim.jsonl dosyalarını yeniler.',
                  style='Muted.TLabel').pack(anchor='w', pady=(8, 6))
        self.progress = ttk.Progressbar(footer, mode='indeterminate')
        self.progress.pack(fill='x', pady=(0, 8))
        for variable in (self.status, self.summary):
            label = ttk.Label(footer, textvariable=variable, wraplength=900)
            label.pack(fill='x', pady=2)
            label.bind('<Configure>', lambda event, item=label: item.configure(wraplength=max(120, event.width)))

    def mark_dirty(self):
        self.dirty = True
        name = self.profile_path.name if self.profile_path else 'Motor varsayılanları'
        self.profile.set(name + ' — kaydedilmemiş değişiklikler')

    def mark_clean(self, path=None):
        self.dirty, self.profile_path = False, path
        self.profile.set(path.name if path else 'Motor varsayılanları')

    def confirm_discard(self):
        return not self.dirty or messagebox.askyesno('Kaydedilmemiş ayarlar',
            'Kaydedilmemiş ayar değişikliklerinden vazgeçilsin mi?', parent=self.root)

    def load_profile_path(self, path: Path):
        """Apply only after full validation; loading errors leave the current form intact."""
        settings = load_profile(path)
        for key in ('INPUT_DIR', 'OUTPUT_FILE'):
            settings.config[key] = self.panel.fields[key].get()
        settings.config['OVERWRITE'] = False
        self.panel.set_settings(settings)
        self.mark_clean(path)

    def load_profile(self):
        if self.running or not self.confirm_discard():
            return
        path = filedialog.askopenfilename(parent=self.root, title='Ayar profili yükle',
                                          filetypes=[('JSON profili', '*.json')])
        if not path:
            return
        try:
            self.load_profile_path(Path(path))
        except (ValueError, OSError) as exc:
            messagebox.showerror('Profil yüklenemedi', str(exc), parent=self.root)

    def save_profile(self):
        if self.running:
            return
        try:
            settings = self.panel.get_settings()
            path = filedialog.asksaveasfilename(parent=self.root, title='Ayar profilini kaydet',
                                                defaultextension='.json',
                                                initialfile=self.profile_path.name if self.profile_path else 'Fusion-profili.json',
                                                filetypes=[('JSON profili', '*.json')])
            if not path:
                return
            save_profile(Path(path), settings)
            self.mark_clean(Path(path))
        except SettingsError as exc:
            self.panel.show_error(exc)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Profil kaydedilemedi', str(exc), parent=self.root)

    def reset(self):
        if self.running or not self.confirm_discard():
            return
        settings = default_settings()
        for key in ('INPUT_DIR', 'OUTPUT_FILE'):
            settings.config[key] = self.panel.fields[key].get()
        settings.config['OVERWRITE'] = False
        self.panel.set_settings(settings)
        self.mark_clean()

    def options(self, dry_run):
        settings = self.panel.get_settings()
        cfg = settings.config
        return RunOptions(source=str(cfg['INPUT_DIR']), output=str(cfg['OUTPUT_FILE']),
                          group_mode=cfg['REPORT_GROUP_MODE'], include_root=cfg['INCLUDE_ROOT_FILES'],
                          overwrite=cfg['OVERWRITE'], dry_run=dry_run, header_row=cfg['EXPECTED_HEADER_ROW'],
                          search_end=cfg['HEADER_SEARCH_END'], fail_on_error=cfg['FAIL_ON_FILE_ERROR'],
                          settings=settings)

    def start(self, dry_run):
        if self.running:
            return
        try:
            options = self.options(dry_run)
            options.config()
            validate_paths(options)
        except SettingsError as exc:
            self.panel.show_error(exc)
            return
        except (ValueError, OSError) as exc:
            self.panel.notebook.select(self.panel.tabs['Dosyalar'])
            messagebox.showerror('Ayarları kontrol edin', str(exc), parent=self.root)
            return
        self.result = None
        self.running = True
        self.summary.set('İşlem sürerken uygulamayı açık tutun.')
        self.status.set('İşlem başlatılıyor…')
        self.panel.set_running(True)
        for button in self.controls:
            button.configure(state='disabled')
        self.open_report.configure(state='disabled')
        self.open_folder.configure(state='disabled')
        self.progress.start(15)
        threading.Thread(target=self.work, args=(options,), daemon=False).start()

    def work(self, options):
        # Only the UI thread may access Tk objects; the worker owns its settings copy.
        try:
            result = run_report(options, lambda text: self.events.put(('progress', text)))
            self.events.put(('done', result))
        except Exception as exc:  # noqa: BLE001 -- worker boundary must report failures to Tk.
            self.events.put(('error', f'{type(exc).__name__}: {exc}'))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    self.status.set(value)
                else:
                    self.finish(kind, value)
        except queue.Empty:
            pass
        self.poll_id = self.root.after(100, self.poll)

    def finish(self, kind, value):
        self.running = False
        self.progress.stop()
        self.panel.set_running(False)
        for button in self.controls:
            button.configure(state='normal')
        if kind == 'error':
            self.status.set('İşlem tamamlanamadı.')
            self.summary.set("Çıktı Excel'de açıksa kapatın. Varsa .log ve .denetim.jsonl dosyalarını inceleyin.")
            messagebox.showerror('İşlem tamamlanamadı', value, parent=self.root)
            return
        self.result = value
        title = 'Rapor oluşturuldu.' if value.output else 'Ön kontrol tamamlandı.'
        if not value.records:
            title += ' Birleştirilecek kayıt bulunamadı; denetimi kontrol edin.'
        elif value.errors or value.warnings:
            title += ' Denetim sonuçlarını inceleyin.'
        self.status.set(title)
        self.summary.set(f'{value.records} kayıt  ·  {value.groups} grup  ·  {value.warnings} uyarı  ·  '
                         f'{value.errors} hata  ·  {value.quarantined} karantina satırı')
        self.open_report.configure(state='normal' if value.output else 'disabled')
        self.open_folder.configure(state='normal')

    def open_result(self, kind):
        if self.result is None:
            return
        path = self.result.audit.parent if kind == 'folder' else self.result.output
        if path is not None:
            try:
                open_path(path)
            except OSError as exc:
                messagebox.showerror('Açılamadı', str(exc), parent=self.root)

    def close(self):
        if self.running:
            messagebox.showinfo('İşlem sürüyor', 'Rapor tamamlandığında pencereyi kapatabilirsiniz.', parent=self.root)
            return
        if self.confirm_discard():
            self.root.after_cancel(self.poll_id)
            self.root.destroy()


def main() -> None:
    started = time.perf_counter()
    load_tk()
    root = tk.Tk()
    application = Application(root)
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        from fusion_smoke import check
        root.update()
        try:
            application.panel.get_settings()
            check(Path(sys.argv[2]), started)
        finally:
            root.after_cancel(application.poll_id)
            root.destroy()
        return
    root.mainloop()


if __name__ == '__main__':
    main()
