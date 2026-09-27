"""Settings and profiles are usable without Tk or a display."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import excel_fusion as core
from fusion_diagnostics import sample_configuration
from fusion_settings import (
    FIELDS,
    SettingsError,
    default_settings,
    load_profile,
    remove_column,
    rename_column,
    save_profile,
    validate_settings,
)


class ConfigurationCoverageTests(unittest.TestCase):
    def test_live_engine_config_has_a_control_for_every_key(self):
        self.assertEqual({field.key.split('.')[0] for field in FIELDS}, set(core.CONFIG))
        workflow_keys = {field.key.split('.')[1] for field in FIELDS if field.key.startswith('WORKFLOW_SUMMARY.')}
        self.assertEqual(workflow_keys, set(core.CONFIG['WORKFLOW_SUMMARY']))


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(sample_configuration())
        self.settings = default_settings()

    def test_defaults_are_independent_and_every_config_key_is_covered(self):
        self.assertEqual(self.settings.config, core.CONFIG)
        self.assertEqual(self.settings.columns, tuple(core.COLUMN_SCHEMA))
        self.assertEqual({field.key.split('.')[0] for field in FIELDS}, set(core.CONFIG))
        self.settings.config['WORKFLOW_SUMMARY']['OPEN_PREFIX'] = 'açık'
        self.assertEqual(core.CONFIG['WORKFLOW_SUMMARY']['OPEN_PREFIX'], 'open')

    def test_rejects_invalid_values_with_field_location(self):
        cases = [('MIN_HEADER_MATCHES', True), ('FUZZY_THRESHOLD', float('nan')),
                 ('FUZZY_THRESHOLD', 10 ** 400), ('FUZZY_THRESHOLD', 0), ('AMBIGUITY_MARGIN', 100),
                 ('HEADER_SEARCH_START', 0), ('ROW_ID_REGEX', '['),
                 ('ROW_REQUIRED_COLUMNS', ('',)), ('INCLUDE_ROOT_FILES', 'false'),
                 ('CHARTS', (('Entity', 'pie'),)), ('HEADER_HEIGHTS', (True,)),
                 ('REPORT_TITLE', 12), ('WORKFLOW_SUMMARY', {'ENABLED': 'yes'})]
        for key, value in cases:
            with self.subTest(key=key):
                settings = default_settings()
                settings.config[key] = value
                with self.assertRaises(SettingsError) as error:
                    validate_settings(settings)
                self.assertTrue(error.exception.key.startswith(key))

    def test_preserves_significant_spaces_and_free_source_required_columns(self):
        self.settings.config.update(EXTRA_PREFIX=' Ek | ', ROW_REQUIRED_COLUMNS=('Kaynak Notu',))
        validate_settings(self.settings)
        self.assertEqual(self.settings.config['EXTRA_PREFIX'], ' Ek | ')

    def test_column_validation_handles_alias_collision_and_nonfinite_width(self):
        for column in (core.ColumnSpec('Yeni', ('Entity',)), core.ColumnSpec('Yeni', width=float('inf'))):
            with self.subTest(column=column), self.assertRaises(SettingsError):
                validate_settings(replace(self.settings, columns=(*self.settings.columns, column)))

    def test_rename_updates_explicit_references_but_preserves_source_required_names(self):
        self.settings.config['ROW_REQUIRED_COLUMNS'] = ('Entity', 'Notes')
        result = rename_column(self.settings, 'Entity', 'Varlık')
        self.assertIn('Varlık', result.config['HEADER_ANCHORS'])
        self.assertNotIn('Entity', result.config['ROW_REQUIRE_ANY'])
        self.assertEqual(result.config['ROW_REQUIRED_COLUMNS'], ('Entity', 'Notes'))
        self.assertEqual(self.settings.columns[1].name, 'Entity')
        validate_settings(result)

    def test_delete_referenced_column_explains_dependencies(self):
        with self.assertRaisesRegex(SettingsError, 'HEADER_ANCHORS'):
            remove_column(self.settings, 'Entity')
        self.settings.columns += (core.ColumnSpec('Serbest'),)
        result = remove_column(self.settings, 'Serbest')
        self.assertNotIn('Serbest', [column.name for column in result.columns])

    def test_rename_keeps_required_standard_selection_working_with_source_alias(self):
        self.settings.config['ROW_REQUIRED_COLUMNS'] = ('Entity', 'Notes')
        self.settings.required_column_refs = ('Entity',)
        result = rename_column(self.settings, 'Entity', 'Varlık')
        self.assertEqual(result.config['ROW_REQUIRED_COLUMNS'], ('Varlık', 'Notes'))
        self.assertEqual(result.required_column_refs, ('Varlık',))
        validate_settings(result)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(sample_configuration())
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / 'Türkçe.json'

    def test_roundtrip_preserves_configuration_schema_and_omits_paths_and_overwrite(self):
        settings = default_settings()
        settings.config.update(REPORT_TITLE='Türkçe rapor', EXTRA_PREFIX='Ek | ', OVERWRITE=True)
        settings.config['ROW_REQUIRED_COLUMNS'] = ('Entity', 'Kaynak notu')
        settings.required_column_refs = ('Entity',)
        settings.columns = tuple(reversed(settings.columns))
        save_profile(self.path, settings)
        payload = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertFalse({'INPUT_DIR', 'OUTPUT_FILE', 'OVERWRITE'} & payload['config'].keys())
        loaded = load_profile(self.path)
        settings.config['OVERWRITE'] = False
        self.assertEqual(loaded, settings)

    def test_partial_config_merges_nested_defaults(self):
        self.path.write_text(json.dumps({'version': 1, 'config': {
            'WORKFLOW_SUMMARY': {'OPEN_PREFIX': 'açık'}},
            'columns': [{'name': c.name, 'aliases': c.aliases} for c in core.COLUMN_SCHEMA]}))
        result = load_profile(self.path)
        self.assertEqual(result.config['WORKFLOW_SUMMARY']['OPEN_PREFIX'], 'açık')
        self.assertEqual(result.config['WORKFLOW_SUMMARY']['CLOSED_PREFIX'], 'closed')

    def test_rejects_unknown_keys_versions_types_and_malformed_json(self):
        save_profile(self.path, default_settings())
        valid = json.loads(self.path.read_text())
        cases = [dict(valid, version=2), dict(valid, version=True), dict(valid, extra=1),
                 dict(valid, config={'UNKNOWN': True}), dict(valid, config={'OVERWRITE': True}),
                 dict(valid, config={'FUZZY_THRESHOLD': '84'}), dict(valid, columns=[]),
                 dict(valid, columns=[{'name': 'Name', 'required': 'false'}]),
                 dict(valid, config={'WORKFLOW_SUMMARY': {'EXTRA': 1}})]
        for payload in cases:
            with self.subTest(payload=payload):
                self.path.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    load_profile(self.path)
        self.path.write_text('{')
        with self.assertRaises(ValueError):
            load_profile(self.path)

    def test_failed_replace_preserves_existing_profile_and_cleans_temporary_file(self):
        save_profile(self.path, default_settings())
        before = self.path.read_bytes()
        with (patch('fusion_settings.os.replace', side_effect=PermissionError('locked')),
              self.assertRaises(PermissionError)):
            save_profile(self.path, default_settings())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(Path(self.directory).iterdir()), [self.path])


if __name__ == '__main__':
    unittest.main()
