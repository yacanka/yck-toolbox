"""Run with a Tk-enabled Python and display; headless settings/service tests are separate."""
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fusion_diagnostics import sample_configuration
from fusion_settings import SettingsError, default_settings


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Opt in explicitly: packaging's display-free discovery must remain usable.
        if os.environ.get('FUSION_GUI_TESTS') != '1':
            raise unittest.SkipTest('Ekran testi için FUSION_GUI_TESTS=1 ve Tk destekli Python kullanın.')
        import tkinter as tk
        cls.root = tk.Tk()
        cls.root.geometry('920x760')

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.enterContext(sample_configuration())
        from fusion_settings_ui import SettingsPanel
        self.panel = SettingsPanel(self.root, default_settings())
        self.panel.pack(fill='both', expand=True)
        self.root.update()

    def tearDown(self):
        self.panel.destroy()

    def test_form_roundtrip_and_edit(self):
        self.assertEqual(self.panel.get_settings(), default_settings())
        self.panel.fields['REPORT_TITLE'].set('Türkçe rapor')
        self.panel.fields['ROW_REQUIRED_COLUMNS'].set(('Notes',))
        value = self.panel.get_settings()
        self.assertEqual(value.config['REPORT_TITLE'], 'Türkçe rapor')
        self.assertEqual(value.config['ROW_REQUIRED_COLUMNS'], ('Notes',))

    def test_chart_pairs_also_accept_engine_list_form(self):
        settings = default_settings()
        settings.config['CHARTS'] = [['Entity', 'bar']]
        self.panel.set_settings(settings)
        self.assertEqual(self.panel.get_settings().config['CHARTS'], (('Entity', 'bar'),))

    def test_mode_dependencies_and_running_lock(self):
        self.panel.fields['REPORT_GROUP_MODE'].set('sheet_name')
        self.panel.refresh_states()
        self.assertTrue(self.panel.fields['INCLUDE_ROOT_FILES'].disabled)
        self.panel.set_running(True)
        self.assertTrue(all(field.disabled for field in self.panel.fields.values()))
        self.panel.set_running(False)
        self.assertFalse(self.panel.fields['REPORT_TITLE'].disabled)
        self.assertTrue(self.panel.fields['INCLUDE_ROOT_FILES'].disabled)

    def test_rename_updates_choices_and_references(self):
        column = replace(self.panel.columns[1], name='Varlık')
        self.panel.edit_column(1, column)
        settings = self.panel.get_settings()
        self.assertIn('Varlık', settings.config['HEADER_ANCHORS'])
        self.assertIn('Varlık', self.panel.fields['ROW_ID_COLUMN'].choices)
        self.assertNotIn('Entity', self.panel.fields['ROW_ID_COLUMN'].choices)

    def test_invalid_number_selects_field_tab(self):
        self.panel.fields['FUZZY_THRESHOLD'].set('yanlış')
        with self.assertRaises(SettingsError) as error:
            self.panel.get_settings()
        self.panel.show_error(error.exception)
        self.assertEqual(self.panel.notebook.tab(self.panel.notebook.select(), 'text'), 'Eşleştirme')

    def test_keyboard_focus_scrolls_offscreen_control_into_view(self):
        tab = self.panel.tabs['Dosyalar']
        control = self.panel.fields['FAIL_ON_FILE_ERROR'].editor
        control.event_generate('<FocusIn>')
        self.root.update()
        self.assertGreater(tab.canvas.yview()[0], 0)
        self.assertGreaterEqual(control.winfo_rooty(), tab.canvas.winfo_rooty())
        self.assertLess(control.winfo_rooty(), tab.canvas.winfo_rooty() + tab.canvas.winfo_height())

    def test_column_reorder_and_referenced_delete(self):
        self.panel.move_column(1, -1)
        self.assertEqual(self.panel.get_settings().columns[0].name, 'Entity')
        with self.assertRaises(SettingsError):
            self.panel.delete_column(0)

    def test_pending_list_and_column_edits_are_not_silently_discarded(self):
        editor = self.panel.fields['EXCLUDE_SHEETS'].editor
        editor.entry_value.set('Kapak')
        with self.assertRaises(SettingsError):
            self.panel.get_settings()
        editor.add()
        self.assertIn('Kapak', self.panel.get_settings().config['EXCLUDE_SHEETS'])
        self.panel.column_editor.name.set('Kaydedilmedi')
        with self.assertRaises(SettingsError):
            self.panel.get_settings()

    def test_reorder_shows_invalid_field_instead_of_escaping_callback(self):
        self.panel.column_editor.load(1)
        self.panel.fields['FUZZY_THRESHOLD'].set('abc')
        self.panel.column_editor.move(-1)
        self.assertIn('sayı', self.panel.error.get())
        self.assertEqual(self.panel.notebook.tab(self.panel.notebook.select(), 'text'), 'Eşleştirme')

    def test_required_source_literals_and_selected_standard_columns_rename_independently(self):
        editor = self.panel.fields['ROW_REQUIRED_COLUMNS'].editor
        editor.entry_value.set('Entity')
        editor.reference_kind.set('Şema sütunu')
        editor.add()
        editor.entry_value.set('Notes')
        editor.reference_kind.set('Kaynak başlığı')
        editor.add()
        self.panel.edit_column(1, replace(self.panel.columns[1], name='Varlık'))
        settings = self.panel.get_settings()
        self.assertEqual(settings.config['ROW_REQUIRED_COLUMNS'], ('Varlık', 'Notes'))
        self.assertEqual(settings.required_column_refs, ('Varlık',))


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('FUSION_GUI_TESTS') != '1':
            raise unittest.SkipTest('Ekran testi için FUSION_GUI_TESTS=1 ve Tk destekli Python kullanın.')

    def setUp(self):
        import tkinter as tk

        from excel_fusion_gui import Application
        self.enterContext(sample_configuration())
        self.root = tk.Tk()
        self.app = Application(self.root)
        self.root.update()
        self.addCleanup(self.root.destroy)

    def test_bad_profile_does_not_replace_form_or_paths(self):
        self.app.panel.fields['REPORT_TITLE'].set('Mevcut taslak')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.json'
            path.write_text('{')
            with self.assertRaises(ValueError):
                self.app.load_profile_path(path)
        self.assertEqual(self.app.panel.get_settings().config['REPORT_TITLE'], 'Mevcut taslak')

    def test_profile_load_preserves_paths_and_disables_overwrite(self):
        from fusion_settings import save_profile
        self.app.panel.fields['INPUT_DIR'].set('/tmp/kaynak')
        self.app.panel.fields['OUTPUT_FILE'].set('/tmp/rapor.xlsx')
        self.app.panel.fields['OVERWRITE'].set(True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            save_profile(path, default_settings())
            self.app.load_profile_path(path)
        values = self.app.panel.get_settings().config
        self.assertEqual(str(values['INPUT_DIR']), '/tmp/kaynak')
        self.assertEqual(str(values['OUTPUT_FILE']), '/tmp/rapor.xlsx')
        self.assertFalse(values['OVERWRITE'])
        self.assertFalse(self.app.dirty)

    def test_worker_failure_restores_controls_and_close_warns_unsaved(self):
        self.app.running = True
        self.app.panel.set_running(True)
        with patch('excel_fusion_gui.messagebox.showerror'):
            self.app.finish('error', 'test failure')
        self.assertFalse(self.app.panel.fields['REPORT_TITLE'].disabled)
        self.app.panel.fields['REPORT_TITLE'].set('Değişiklik')
        with patch('excel_fusion_gui.messagebox.askyesno', return_value=False) as confirm:
            self.app.close()
        confirm.assert_called_once()
        self.assertTrue(self.root.winfo_exists())


if __name__ == '__main__':
    unittest.main()
