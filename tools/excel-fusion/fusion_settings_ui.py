"""Tk editors for the engine configuration catalog and ordered column schema."""
from __future__ import annotations

import copy
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import excel_fusion as core
from fusion_settings import (
    FIELDS,
    FusionSettings,
    SettingsError,
    default_settings,
    get_value,
    parse_input,
    remove_column,
    rename_column,
    set_value,
    validate_settings,
)

CHOICE_LABELS = {
    'subfolder': 'Alt klasöre göre', 'sheet_name': 'Sayfa adına göre',
    'smart': 'Akıllı', 'first_line': 'Yalnızca ilk satır', 'full': 'Tüm metin',
    'bar': 'Yatay çubuk', 'column': 'Dikey sütun', 'doughnut': 'Halka',
}
SECTIONS = ('Dosyalar', 'Sütunlar', 'Eşleştirme', 'Satır kuralları', 'Rapor')


def set_enabled(widget, enabled: bool) -> None:
    """Restore editable vs read-only states, including controls inside composite editors."""
    if isinstance(widget, ttk.Combobox):
        widget.configure(state=('normal' if getattr(widget, 'editable', False) else 'readonly')
                         if enabled else 'disabled')
    elif isinstance(widget, (ttk.Entry, ttk.Button, ttk.Checkbutton, tk.Listbox)):
        widget.configure(state='normal' if enabled else 'disabled')
    elif isinstance(widget, ttk.Treeview):
        widget.state(['!disabled'] if enabled else ['disabled'])
    for child in widget.winfo_children():
        set_enabled(child, enabled)


class ScrollTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background='#FFFFFF', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.body = ttk.Frame(self.canvas, padding=(20, 16))
        self.body.columnconfigure(0, weight=1)
        window = self.canvas.create_window((0, 0), window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda event: self.canvas.itemconfigure(window, width=event.width))

    def reveal(self, widget):
        self.update_idletasks()
        top = widget.winfo_rooty() - self.body.winfo_rooty()
        self.canvas.yview_moveto(max(0, top - 12) / max(1, self.body.winfo_height()))


class SequenceEditor(ttk.Frame):
    """Ordered list with explicit add/remove, also used for aliases and chart pairs."""
    def __init__(self, parent, key, changed, *, choices=(), editable=True, charts=False):
        super().__init__(parent)
        self.key, self.changed, self.charts = key, changed, charts
        self.items = []
        self.references = set()
        self.entry_value = tk.StringVar(self)
        self.reference_kind = tk.StringVar(self, value='Kaynak başlığı')
        self.chart_kind = tk.StringVar(self, value=CHOICE_LABELS['bar'])
        self.columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(self, height=3, exportselection=False, borderwidth=1,
                                  relief='solid', selectbackground='#002FA7', selectforeground='#FFFFFF')
        self.listbox.grid(row=0, column=0, sticky='ew', columnspan=3)
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.listbox.yview)
        scroll.grid(row=0, column=3, sticky='ns')
        self.listbox.configure(yscrollcommand=scroll.set)
        self.entry = ttk.Combobox(self, textvariable=self.entry_value, values=choices)
        self.entry.editable = editable
        self.entry.configure(state='normal' if editable else 'readonly')
        self.entry.grid(row=1, column=0, sticky='ew', pady=(5, 0))
        self.entry.bind('<Return>', lambda _: self.add())
        if key == 'ROW_REQUIRED_COLUMNS':
            mode = ttk.Combobox(self, textvariable=self.reference_kind, state='readonly', width=15,
                                values=('Kaynak başlığı', 'Şema sütunu'))
            mode.grid(row=1, column=1, padx=5, pady=(5, 0))
            self.entry.bind('<<ComboboxSelected>>', lambda _: self.reference_kind.set('Şema sütunu'))
        if charts:
            kinds = ttk.Combobox(self, textvariable=self.chart_kind, width=14, state='readonly',
                                 values=tuple(CHOICE_LABELS[k] for k in ('bar', 'column', 'doughnut')))
            kinds.grid(row=1, column=1, padx=5, pady=(5, 0))
        actions = ttk.Frame(self)
        actions.grid(row=1, column=2, columnspan=2, pady=(5, 0))
        for label, command in (('Ekle', self.add), ('Sil', self.remove)):
            ttk.Button(actions, text=label, command=command, width=5).pack(side='left', padx=(4, 0))
        self.entry_value.trace_add('write', lambda *_: changed())

    def refresh(self):
        self.listbox.delete(0, 'end')
        for item in self.items:
            label = f'{item[0]} — {CHOICE_LABELS[item[1]]}' if self.charts else str(item)
            if self.key == 'ROW_REQUIRED_COLUMNS':
                label += ' (şema)' if item in self.references else ' (kaynak)'
            self.listbox.insert('end', label)

    def add(self):
        value = self.entry_value.get()
        if not value.strip() or str(self.entry.cget('state')) == 'disabled':
            return
        if self.charts and len(self.items) >= 4:
            messagebox.showerror('Grafikler', 'En fazla dört grafik eklenebilir.', parent=self)
            return
        if not self.entry.editable and value not in self.entry.cget('values'):
            return
        if self.key == 'ROW_REQUIRED_COLUMNS':
            if self.reference_kind.get() == 'Şema sütunu' and value not in self.entry.cget('values'):
                messagebox.showerror('Zorunlu sütun', 'Tanımlı bir şema sütunu seçin veya Kaynak başlığı kullanın.', parent=self)
                return
            if self.reference_kind.get() == 'Şema sütunu':
                self.references.add(value)
            else:
                self.references.discard(value)
        if self.charts:
            kind = next(key for key in ('bar', 'column', 'doughnut') if CHOICE_LABELS[key] == self.chart_kind.get())
            value = (value, kind)
        if self.charts or value not in tuple(str(item) for item in self.items):
            self.items.append(value)
        self.entry_value.set('')
        self.refresh()
        self.changed()

    def remove(self):
        if str(self.listbox.cget('state')) == 'disabled':
            return
        for index in reversed(self.listbox.curselection()):
            self.references.discard(self.items[index])
            del self.items[index]
        self.refresh()
        self.changed()

    def get(self):
        if self.entry_value.get():
            raise SettingsError(self.key, 'Yazdığınız değeri Ekle ile listeye ekleyin veya giriş alanını temizleyin.')
        return tuple(self.items)

    def set(self, values):
        self.items = [tuple(value) if self.charts else value for value in values]
        self.references.intersection_update(self.items)
        self.entry_value.set('')
        self.refresh()

    def set_choices(self, choices):
        self.entry.configure(values=choices)


class FieldControl(ttk.Frame):
    def __init__(self, parent, field, changed):
        super().__init__(parent, padding=(0, 0, 0, 12))
        self.field, self.disabled, self.choices = field, False, field.choices
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=field.label, style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.variable = tk.BooleanVar(self) if field.kind == 'bool' else tk.StringVar(self)
        self.editor = self.make_editor(changed)
        self.editor.grid(row=1, column=0, sticky='ew', pady=(5, 0))
        if field.help:
            help_label = ttk.Label(self, text=field.help, style='Muted.TLabel', wraplength=600)
            help_label.grid(row=2, column=0, sticky='ew', pady=(4, 0))
            self.bind('<Configure>', lambda event: help_label.configure(wraplength=max(120, event.width - 10)))
        self.variable.trace_add('write', lambda *_: changed())

    def make_editor(self, changed):
        field = self.field
        if field.kind in ('list', 'columns', 'source_columns', 'heights', 'charts'):
            return SequenceEditor(self, field.key, changed,
                                  choices=tuple(str(item) for item in field.choices),
                                  editable=field.kind in ('list', 'source_columns') and not field.choices,
                                  charts=field.kind == 'charts')
        if field.kind == 'bool':
            return ttk.Checkbutton(self, text='Etkin', variable=self.variable)
        if field.kind in ('choice', 'column', 'optional_column'):
            return ttk.Combobox(self, textvariable=self.variable, state='readonly',
                                values=tuple(CHOICE_LABELS.get(item, item) for item in field.choices))
        if field.kind == 'path':
            frame = ttk.Frame(self)
            entry = ttk.Entry(frame, textvariable=self.variable)
            entry.pack(side='left', fill='x', expand=True)
            ttk.Button(frame, text='Seç…', command=self.choose_path).pack(side='left', padx=(8, 0))
            return frame
        return ttk.Entry(self, textvariable=self.variable)

    def choose_path(self):
        if self.field.key == 'INPUT_DIR':
            path = filedialog.askdirectory(parent=self, title='Kaynak Excel klasörü', mustexist=True)
        else:
            path = filedialog.asksaveasfilename(parent=self, title='Çıktı raporu', defaultextension='.xlsx',
                                               initialfile='Ana_Rapor.xlsx', filetypes=[('Excel raporu', '*.xlsx')])
        if path:
            self.variable.set(path)

    def get(self):
        if isinstance(self.editor, SequenceEditor):
            values = self.editor.get()
            return tuple(int(item) for item in values) if self.field.kind == 'heights' else values
        value = self.variable.get()
        if self.field.kind == 'choice':
            value = next((key for key in self.field.choices if CHOICE_LABELS.get(key, key) == value), value)
        if self.field.kind == 'path':
            return Path(value) if value else ''
        return parse_input(self.field, value)

    def set(self, value):
        if isinstance(self.editor, SequenceEditor):
            self.editor.set(value)
        else:
            display = CHOICE_LABELS.get(value, value) if self.field.kind == 'choice' else value
            self.variable.set('' if display is None else display)

    def set_choices(self, names):
        self.choices = tuple(names)
        if isinstance(self.editor, SequenceEditor):
            self.editor.set_choices(names)
        else:
            values = ('', *names) if self.field.kind in ('column', 'optional_column') else names
            self.editor.configure(values=values)

    def enable(self, enabled):
        self.disabled = not enabled
        set_enabled(self, enabled)


class ColumnEditor(ttk.Frame):
    def __init__(self, parent, panel):
        super().__init__(parent)
        self.panel, self.index, self.dirty, self.loading = panel, None, False, True
        self.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(self, columns=('name', 'required', 'width'), show='headings', height=7,
                                 selectmode='browse')
        for key, label, width in (('name', 'Çıktı sütunu', 300), ('required', 'Başlıkta zorunlu', 130),
                                  ('width', 'Genişlik', 90)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=70)
        self.tree.grid(row=0, column=0, sticky='ew')
        scrollbar = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        scrollbar.grid(row=1, column=0, sticky='ew')
        self.tree.configure(xscrollcommand=scrollbar.set)
        vertical = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=vertical.set)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky='w', pady=8)
        for label, command in (('Yeni sütun', self.new), ('Sil', self.delete),
                               ('Yukarı', lambda: self.move(-1)), ('Aşağı', lambda: self.move(1))):
            ttk.Button(actions, text=label, command=command).pack(side='left', padx=(0, 6))
        self.name, self.width, self.threshold = (tk.StringVar(self) for _ in range(3))
        self.required = tk.BooleanVar(self)
        for row, label, variable in ((3, 'Çıktı sütun adı', self.name), (5, 'Excel sütun genişliği', self.width),
                                      (7, 'Özel eşik (boş: genel eşik)', self.threshold)):
            ttk.Label(self, text=label, style='Heading.TLabel').grid(row=row, column=0, sticky='w', pady=(10, 4))
            ttk.Entry(self, textvariable=variable).grid(row=row + 1, column=0, sticky='ew')
        ttk.Checkbutton(self, text='Bu sütun başlıkta bulunmalı', variable=self.required).grid(
            row=9, column=0, sticky='w', pady=12)
        ttk.Label(self, text='Alternatif kaynak başlıkları', style='Heading.TLabel').grid(row=10, column=0, sticky='w')
        self.aliases = SequenceEditor(self, 'COLUMN_SCHEMA', self.changed)
        self.aliases.grid(row=11, column=0, sticky='ew', pady=6)
        ttk.Button(self, text='Sütunu uygula', style='Primary.TButton', command=self.apply).grid(
            row=12, column=0, sticky='w', pady=8)
        self.notice = tk.StringVar(self)
        ttk.Label(self, textvariable=self.notice, style='Muted.TLabel', wraplength=600).grid(
            row=13, column=0, sticky='ew')
        for variable in (self.name, self.width, self.threshold, self.required):
            variable.trace_add('write', lambda *_: self.changed())
        self.refresh()
        self.load(None)

    def changed(self):
        if not self.loading:
            self.dirty = True
            self.notice.set('Sütun düzenlemesi henüz uygulanmadı.')
            self.panel.changed()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for index, column in enumerate(self.panel.columns):
            self.tree.insert('', 'end', iid=str(index), values=(column.name, 'Evet' if column.required else 'Hayır', column.width))

    def load(self, index):
        self.loading = True
        self.index = index
        column = self.panel.columns[index] if index is not None else core.ColumnSpec('')
        self.name.set(column.name)
        self.width.set(str(column.width))
        self.threshold.set('' if column.threshold is None else str(column.threshold))
        self.required.set(column.required)
        self.aliases.set(column.aliases)
        self.dirty = False
        self.notice.set('Yeni sütun bilgilerini girin.' if index is None else 'Sütun adı değişince bağlı seçimler güncellenir.')
        self.loading = False

    def can_leave(self):
        return not self.dirty or messagebox.askyesno('Uygulanmamış sütun',
            'Bu sütundaki uygulanmamış değişikliklerden vazgeçilsin mi?', parent=self)

    def select(self, _):
        if self.panel.running:
            return
        selection = self.tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if index == self.index:
            return
        if self.can_leave():
            self.load(index)
        elif self.index is not None:
            self.tree.selection_set(str(self.index))
        else:
            self.tree.selection_remove(*selection)

    def new(self):
        if self.can_leave():
            self.tree.selection_remove(*self.tree.selection())
            self.load(None)

    def apply(self):
        try:
            column = core.ColumnSpec(self.name.get(), self.aliases.get(), self.required.get(),
                                     float(self.threshold.get()) if self.threshold.get() else None,
                                     float(self.width.get()))
            index = len(self.panel.columns) if self.index is None else self.index
            self.panel.edit_column(index, column)
            self.load(index)
            self.tree.selection_set(str(index))
        except (ValueError, TypeError) as exc:
            self.panel.show_error(exc if isinstance(exc, SettingsError) else SettingsError('COLUMN_SCHEMA', str(exc)))

    def delete(self):
        if self.index is None or not self.can_leave():
            return
        try:
            self.panel.delete_column(self.index)
            self.load(None)
        except SettingsError as exc:
            self.panel.show_error(exc)

    def move(self, delta):
        if self.index is None or not self.can_leave():
            return
        target = self.index + delta
        if 0 <= target < len(self.panel.columns):
            try:
                self.panel.move_column(self.index, delta)
                self.load(target)
                self.tree.selection_set(str(target))
            except SettingsError as exc:
                self.panel.show_error(exc)


class SettingsPanel(ttk.Frame):
    def __init__(self, parent, settings: FusionSettings, changed=lambda: None):
        super().__init__(parent)
        self.on_change, self.running, self.loading = changed, False, True
        self.columns, self.fields, self.tabs = settings.columns, {}, {}
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        for section in SECTIONS:
            tab = ScrollTab(self.notebook)
            self.notebook.add(tab, text=section)
            self.tabs[section] = tab
        self.column_editor = ColumnEditor(self.tabs['Sütunlar'].body, self)
        self.column_editor.grid(row=0, column=0, sticky='ew')
        for field in FIELDS:
            control = FieldControl(self.tabs[field.section].body, field, self.changed)
            control.grid(sticky='ew')
            self.fields[field.key] = control
        self.error = tk.StringVar(self)
        ttk.Label(self, textvariable=self.error, foreground='#A32121', wraplength=700).pack(fill='x', pady=(4, 0))
        self.set_settings(settings)
        self._bindings = []
        top = self.winfo_toplevel()
        for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self._bindings.append((event, top.bind(event, self.wheel, add='+')))
        self._bindings.append(('<FocusIn>', top.bind('<FocusIn>', self.reveal_focus, add='+')))

    def destroy(self):
        for event, binding in self._bindings:
            self.winfo_toplevel().unbind(event, binding)
        super().destroy()

    def wheel(self, event):
        # List/table widgets keep their own native scrolling.
        if isinstance(event.widget, (tk.Listbox, ttk.Treeview, ttk.Combobox)):
            return
        section = self.notebook.tab(self.notebook.select(), 'text')
        delta = getattr(event, 'delta', 0)
        direction = -1 if delta > 0 or getattr(event, 'num', None) == 4 else 1
        self.tabs[section].canvas.yview_scroll(direction * 3, 'units')

    def reveal_focus(self, event):
        section = self.notebook.tab(self.notebook.select(), 'text')
        tab = self.tabs[section]
        ancestor = event.widget
        while ancestor is not None and ancestor != tab.body:
            ancestor = getattr(ancestor, 'master', None)
        if ancestor is None:
            return
        top = event.widget.winfo_rooty()
        viewport = tab.canvas.winfo_rooty()
        bottom = top + event.widget.winfo_height()
        if top < viewport or bottom > viewport + tab.canvas.winfo_height():
            tab.reveal(event.widget)

    def changed(self):
        if self.loading:
            return
        self.error.set('')
        self.refresh_states()
        self.on_change()

    def refresh_states(self):
        cfg = {key: self.fields[key].get() for key in (
            'REPORT_GROUP_MODE', 'HEADER_TEXT_MODE', 'DROP_DUPLICATES', 'WORKFLOW_SUMMARY.ENABLED')}
        inactive = set()
        if cfg['REPORT_GROUP_MODE'] == 'sheet_name':
            inactive.update(('INCLUDE_ROOT_FILES', 'ROOT_GROUP_NAME'))
        if cfg['HEADER_TEXT_MODE'] != 'smart':
            inactive.add('HEADER_MAX_PREFIX_LINES')
        if not cfg['DROP_DUPLICATES']:
            inactive.add('DEDUP_KEYS')
        if not cfg['WORKFLOW_SUMMARY.ENABLED']:
            inactive.update(field.key for field in FIELDS if field.key.startswith('WORKFLOW_SUMMARY.')
                            and field.key != 'WORKFLOW_SUMMARY.ENABLED')
        for key, control in self.fields.items():
            control.enable(not self.running and key not in inactive)
        set_enabled(self.column_editor, not self.running)

    def set_running(self, running):
        self.running = running
        self.refresh_states()

    def refresh_choices(self):
        names = tuple(column.name for column in self.columns)
        for field in FIELDS:
            if field.kind in ('columns', 'column', 'optional_column', 'source_columns'):
                self.fields[field.key].set_choices(names)
        self.fields['CHARTS'].set_choices(tuple(dict.fromkeys(('Klasör', *names))))

    def set_settings(self, settings):
        self.loading = True
        self.columns = tuple(settings.columns)
        # Some controls may be disabled by the previous configuration.
        for field in FIELDS:
            self.fields[field.key].enable(True)
            self.fields[field.key].set(get_value(settings.config, field.key))
        required = self.fields['ROW_REQUIRED_COLUMNS'].editor
        required.references = set(settings.required_column_refs)
        required.refresh()
        self.refresh_choices()
        self.column_editor.refresh()
        self.column_editor.load(None)
        self.error.set('')
        self.loading = False
        self.refresh_states()

    def read_fields(self):
        config = copy.deepcopy(core.CONFIG)
        for field in FIELDS:
            set_value(config, field.key, self.fields[field.key].get())
        required = self.fields['ROW_REQUIRED_COLUMNS'].editor
        refs = tuple(name for name in config['ROW_REQUIRED_COLUMNS'] if name in required.references)
        return FusionSettings(config, self.columns, refs)

    def get_settings(self):
        if self.column_editor.dirty:
            raise SettingsError('COLUMN_SCHEMA', 'Önce düzenlediğiniz sütunu Sütunu uygula ile onaylayın.')
        settings = self.read_fields()
        validate_settings(settings)
        return settings

    def edit_column(self, index, column):
        settings = self.read_fields()
        if index < len(self.columns):
            settings = rename_column(settings, self.columns[index].name, column.name)
        columns = list(settings.columns)
        if index == len(columns):
            columns.append(column)
        else:
            columns[index] = column
        settings.columns = tuple(columns)
        self.validate_schema(settings.columns)
        self.set_settings(settings)
        self.on_change()

    @staticmethod
    def validate_schema(columns):
        # Schema edits may temporarily leave row/header rules incomplete. Only validate
        # the schema here; the entire configuration is validated before saving/running.
        settings = default_settings()
        settings.columns = columns
        settings.config.update(HEADER_ANCHORS=(), MIN_HEADER_ANCHORS=0, MIN_HEADER_MATCHES=1,
                               ROW_REQUIRE_ANY=(), FILL_DOWN_COLUMNS=(), DEDUP_KEYS=(),
                               ROW_ID_COLUMN=None, CHARTS=())
        settings.config['WORKFLOW_SUMMARY']['ENABLED'] = False
        validate_settings(settings)

    def delete_column(self, index):
        if len(self.columns) == 1:
            raise SettingsError('COLUMN_SCHEMA', 'En az bir sütun tanımlı olmalı.')
        settings = remove_column(self.read_fields(), self.columns[index].name)
        self.set_settings(settings)
        self.on_change()

    def move_column(self, index, delta):
        target = index + delta
        if not 0 <= target < len(self.columns):
            return
        settings = self.read_fields()
        columns = list(settings.columns)
        columns[index], columns[target] = columns[target], columns[index]
        settings.columns = tuple(columns)
        self.set_settings(settings)
        self.on_change()

    def show_error(self, error):
        self.error.set(str(error))
        key = error.key
        control = self.fields.get(key)
        section = control.field.section if control else 'Sütunlar'
        self.notebook.select(self.tabs[section])
        widget = control if control else self.column_editor
        self.tabs[section].reveal(widget)
        if control and not control.disabled:
            control.editor.focus_set()
