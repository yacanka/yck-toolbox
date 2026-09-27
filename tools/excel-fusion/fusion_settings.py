"""Typed desktop settings and portable JSON profiles; never modify engine globals."""
from __future__ import annotations

import copy
import json
import math
import os
import re
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import excel_fusion as core


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    section: str
    kind: str = 'text'
    choices: tuple = ()
    minimum: float | None = None
    maximum: float | None = None
    help: str = ''


# One catalog drives the form and type checks. Engine values remain the defaults.
FIELDS = (
    Field('INPUT_DIR', 'Kaynak klasör', 'Dosyalar', 'path'),
    Field('OUTPUT_FILE', 'Çıktı raporu', 'Dosyalar', 'path'),
    Field('REPORT_GROUP_MODE', 'Gruplama', 'Dosyalar', 'choice', ('subfolder', 'sheet_name')),
    Field('INCLUDE_ROOT_FILES', 'Ana klasördeki dosyaları dahil et', 'Dosyalar', 'bool'),
    Field('ROOT_GROUP_NAME', 'Kök grup adı', 'Dosyalar'),
    Field('EXTENSIONS', 'Dosya uzantıları', 'Dosyalar', 'list',
          ('.xlsx', '.xlsm', '.xltx', '.xltm', '.xls', '.xlsb')),
    Field('EXCLUDE_DIRS', 'Hariç tutulan klasör adları', 'Dosyalar', 'list'),
    Field('EXCLUDE_FILES', 'Hariç tutulan dosyalar', 'Dosyalar', 'list', help='Joker karakter kullanılabilir: ~$*, *.tmp.xlsx'),
    Field('EXCLUDE_SHEETS', 'Hariç tutulan sayfalar', 'Dosyalar', 'list', help='Joker karakter kullanılabilir: *Summary*, Kapak'),
    Field('INCLUDE_HIDDEN_SHEETS', 'Gizli sayfaları dahil et', 'Dosyalar', 'bool'),
    Field('OVERWRITE', 'Mevcut Excel Fusion raporunu yenile', 'Dosyalar', 'bool'),
    Field('FAIL_ON_FILE_ERROR', 'Kaynak hatası varsa rapor oluşturma', 'Dosyalar', 'bool'),
    Field('EXPECTED_HEADER_ROW', 'Beklenen başlık satırı', 'Eşleştirme', 'int', minimum=1, maximum=1048576),
    Field('HEADER_SEARCH_START', 'Arama başlangıç satırı', 'Eşleştirme', 'int', minimum=1, maximum=1048576),
    Field('HEADER_SEARCH_END', 'Arama son satırı', 'Eşleştirme', 'int', minimum=1, maximum=1048576),
    Field('HEADER_HEIGHTS', 'Başlığın kapladığı satır sayıları', 'Eşleştirme', 'heights', (1, 2)),
    Field('HEADER_TEXT_MODE', 'Başlık metnini okuma', 'Eşleştirme', 'choice', ('smart', 'first_line', 'full')),
    Field('HEADER_MAX_PREFIX_LINES', 'Birleştirilecek en fazla başlangıç satırı', 'Eşleştirme', 'int', minimum=1, maximum=10),
    Field('MIN_HEADER_MATCHES', 'En az eşleşen sütun sayısı', 'Eşleştirme', 'int', minimum=1),
    Field('HEADER_ANCHORS', 'Başlık referans sütunları', 'Eşleştirme', 'columns'),
    Field('MIN_HEADER_ANCHORS', 'En az bulunan referans sütunu', 'Eşleştirme', 'int', minimum=0),
    Field('FUZZY_THRESHOLD', 'Genel benzerlik eşiği', 'Eşleştirme', 'float', minimum=0, maximum=100,
          help='0–100 benzerlik puanı; olasılık değildir. Düşük değer daha esnek eşleştirir.'),
    Field('AMBIGUITY_MARGIN', 'İki eşleşme arasında gereken fark', 'Eşleştirme', 'float', minimum=0, maximum=100),
    Field('SHORT_ALIAS_MAX_LENGTH', 'Tam eşleşme gereken kısa ad uzunluğu', 'Eşleştirme', 'int', minimum=0),
    Field('ROW_REQUIRED_COLUMNS', 'Her satırda dolu olması gereken sütunlar', 'Satır kuralları', 'source_columns',
          help='Her biri dolu olmalı. Şema sütunu yeniden adlandırmayı izler; kaynak başlığı yazıldığı gibi korunur.'),
    Field('MIN_ROW_VALUES', 'En az dolu hücre sayısı', 'Satır kuralları', 'int', minimum=0),
    Field('ROW_REQUIRE_ANY', 'En az biri dolu olması gereken sütunlar', 'Satır kuralları', 'columns'),
    Field('ROW_ID_COLUMN', 'Kayıt kimliği sütunu', 'Satır kuralları', 'optional_column',
          help='Seçilmezse kaynak Excel satır numarası kullanılır.'),
    Field('ROW_ID_REGEX', 'Kayıt kimliği deseni (regex)', 'Satır kuralları', 'optional_text',
          help='Boş bırakılırsa desen kontrolü yapılmaz.'),
    Field('FOOTER_LABELS', 'Dipnot / toplam satırı etiketleri', 'Satır kuralları', 'list'),
    Field('TRIM_TEXT', 'Metinlerin baş ve son boşluklarını temizle', 'Satır kuralları', 'bool'),
    Field('FILL_DOWN_COLUMNS', 'Boş hücreleri üst satırdan doldur', 'Satır kuralları', 'columns'),
    Field('DROP_DUPLICATES', 'Tekrar eden kayıtları kaldır', 'Satır kuralları', 'bool'),
    Field('DEDUP_KEYS', 'Tekrar kontrolü sütunları', 'Satır kuralları', 'columns',
          help='Boş liste tüm veri alanlarını kullanır; kaynak bilgisi hariçtir.'),
    Field('PRESERVE_SIMPLE_ZERO_FORMATS', 'Baştaki sıfırları koru (007 gibi)', 'Satır kuralları', 'bool'),
    Field('REPORT_TITLE', 'Rapor başlığı', 'Rapor'),
    Field('SUMMARY_SHEET', 'Özet sayfası adı', 'Rapor'),
    Field('EXTRA_PREFIX', 'Ek sütun öneki', 'Rapor', help='Baş ve son boşluklar olduğu gibi korunur.'),
    Field('DATE_FORMAT', 'Excel tarih biçimi', 'Rapor'),
    Field('DATETIME_FORMAT', 'Excel tarih ve saat biçimi', 'Rapor'),
    Field('MAX_ROWS_PER_SHEET', 'Sayfa başına en fazla satır', 'Rapor', 'int', minimum=1, maximum=1048568),
    Field('DASHBOARD_TOP_N', 'Grafiklerde gösterilen kategori sayısı', 'Rapor', 'int', minimum=1, maximum=30),
    Field('CHARTS', 'Grafikler', 'Rapor', 'charts', help='En fazla dört grafik. Klasör, geçerli rapor gruplarını gösterir.'),
    Field('WORKFLOW_SUMMARY.ENABLED', 'İş akışı özetini göster', 'Rapor', 'bool'),
    Field('WORKFLOW_SUMMARY.STATUS_COLUMN', 'Durum sütunu', 'Rapor', 'column'),
    Field('WORKFLOW_SUMMARY.COMPANY_COLUMN', 'Şirket sütunu', 'Rapor', 'column'),
    Field('WORKFLOW_SUMMARY.OPEN_PREFIX', 'Açık durum metni öneki', 'Rapor'),
    Field('WORKFLOW_SUMMARY.CLOSED_PREFIX', 'Kapalı durum metni öneki', 'Rapor'),
)
FIELD_BY_KEY = {field.key: field for field in FIELDS}
PATH_KEYS = {'INPUT_DIR', 'OUTPUT_FILE'}
PROFILE_EXCLUDED = PATH_KEYS | {'OVERWRITE'}
COLUMN_LIST_KEYS = ('HEADER_ANCHORS', 'ROW_REQUIRE_ANY', 'FILL_DOWN_COLUMNS', 'DEDUP_KEYS')


class SettingsError(ValueError):
    """Validation error with a field key so the GUI can reveal the relevant control."""
    def __init__(self, key: str, message: str):
        self.key = key
        label = FIELD_BY_KEY[key].label if key in FIELD_BY_KEY else key
        super().__init__(f'{label}: {message}')


@dataclass
class FusionSettings:
    config: dict
    columns: tuple[core.ColumnSpec, ...]
    # UI-only binding metadata; the engine still receives plain column-name strings.
    required_column_refs: tuple[str, ...] = ()


def default_settings() -> FusionSettings:
    names = {column.name for column in core.COLUMN_SCHEMA}
    refs = tuple(name for name in core.CONFIG.get('ROW_REQUIRED_COLUMNS', ()) if name in names)
    return FusionSettings(copy.deepcopy(core.CONFIG), tuple(copy.deepcopy(core.COLUMN_SCHEMA)), refs)


def get_value(config: dict, key: str) -> Any:
    if '.' in key:
        parent, child = key.split('.')
        return config[parent][child]
    return config[key]


def set_value(config: dict, key: str, value: Any) -> None:
    if '.' in key:
        parent, child = key.split('.')
        config[parent][child] = value
    else:
        config[key] = value


def parse_input(field: Field, value: Any) -> Any:
    """Convert form input only; JSON loading never coerces strings to numbers/bools."""
    try:
        if field.kind in ('int', 'float'):
            return int(value) if field.kind == 'int' else float(value)
        if field.kind in ('optional_column', 'optional_text'):
            return value if value != '' else None
        return value
    except (TypeError, ValueError) as exc:
        raise SettingsError(field.key, 'Geçerli bir sayı girin.') from exc


def _validate_field(field: Field, value: Any) -> None:
    kind = field.kind
    valid = True
    if kind == 'path':
        valid = isinstance(value, (str, Path))
    elif kind == 'bool':
        valid = type(value) is bool
    elif kind in ('int', 'float'):
        valid = (type(value) is int if kind == 'int' else type(value) in (int, float))
        valid = valid and _finite_number(value)
        valid = valid and (field.minimum is None or value >= field.minimum)
        valid = valid and (field.maximum is None or value <= field.maximum)
        if valid and field.key == 'FUZZY_THRESHOLD':
            valid = value > 0
        if valid and field.key == 'AMBIGUITY_MARGIN':
            valid = value < 100
    elif kind in ('list', 'columns', 'source_columns', 'heights'):
        valid = isinstance(value, (tuple, list))
        if valid and kind == 'heights':
            valid = bool(value) and all(type(item) is int and item in (1, 2) for item in value)
        elif valid:
            valid = all(isinstance(item, str) and item.strip() for item in value)
    elif kind == 'charts':
        valid = isinstance(value, (tuple, list)) and len(value) <= 4
        if valid:
            valid = all(isinstance(item, (tuple, list)) and len(item) == 2
                        and all(isinstance(part, str) for part in item) for item in value)
    elif kind in ('optional_column', 'optional_text'):
        valid = value is None or isinstance(value, str)
    else:
        valid = isinstance(value, str)
    if valid and field.choices and kind != 'heights':
        valid = (all(item in field.choices for item in value) if kind == 'list'
                 else value in field.choices)
    if not valid:
        detail = 'Değer türünü ve seçenekleri kontrol edin.'
        if kind in ('int', 'float'):
            detail = f'Geçerli sayı girin (alt sınır: {field.minimum}, üst sınır: {field.maximum or "yok"}).'
        if field.key == 'FUZZY_THRESHOLD':
            detail = '0’dan büyük, 100 veya daha küçük bir sayı girin.'
        if field.key == 'AMBIGUITY_MARGIN':
            detail = '0 veya daha büyük, 100’den küçük bir sayı girin.'
        raise SettingsError(field.key, detail)


def _finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _validate_columns(columns: tuple[core.ColumnSpec, ...]) -> None:
    for column in columns:
        if not isinstance(column, core.ColumnSpec) or not isinstance(column.name, str):
            raise SettingsError('COLUMN_SCHEMA', 'Geçersiz sütun tanımı.')
        if type(column.required) is not bool or not isinstance(column.aliases, (tuple, list)):
            raise SettingsError('COLUMN_SCHEMA', 'Zorunluluk boolean, alternatif başlıklar liste olmalı.')
        if any(not isinstance(alias, str) for alias in column.aliases):
            raise SettingsError('COLUMN_SCHEMA', 'Alternatif başlıklar metin olmalı.')
        numbers = [column.width] + ([] if column.threshold is None else [column.threshold])
        if any(not _finite_number(number) for number in numbers):
            raise SettingsError('COLUMN_SCHEMA', 'Genişlik ve eşik sonlu sayılar olmalı.')


def validate_settings(settings: FusionSettings) -> None:
    """Validate UI types, then delegate semantic rules to the unchanged engine."""
    cfg = settings.config
    for field in FIELDS:
        try:
            value = get_value(cfg, field.key)
        except (KeyError, TypeError) as exc:
            raise SettingsError(field.key, 'Ayar eksik veya geçersiz.') from exc
        _validate_field(field, value)
    _validate_columns(settings.columns)
    refs = settings.required_column_refs
    names = {column.name for column in settings.columns}
    if (not isinstance(refs, (tuple, list)) or any(not isinstance(name, str) for name in refs)
            or not set(refs) <= names & set(cfg['ROW_REQUIRED_COLUMNS'])):
        raise SettingsError('ROW_REQUIRED_COLUMNS', 'Şema bağlantıları tanımlı zorunlu sütunları göstermeli.')
    if not 1 <= cfg['EXPECTED_HEADER_ROW'] <= cfg['HEADER_SEARCH_END']:
        raise SettingsError('EXPECTED_HEADER_ROW', 'Başlık satırı 1 ile arama sonu arasında olmalı.')
    try:
        core.validate(cfg, settings.columns)
    except re.error as exc:
        raise SettingsError('ROW_ID_REGEX', 'Geçersiz düzenli ifade.') from exc
    except ValueError as exc:
        message = str(exc)
        key = next((field.key for field in FIELDS if field.key in message), 'COLUMN_SCHEMA')
        if message.startswith('Başlık arama'):
            key = 'HEADER_SEARCH_START'
        elif 'Grafik' in message or 'grafik' in message:
            key = 'CHARTS'
        elif 'önek' in message:
            key = 'WORKFLOW_SUMMARY.OPEN_PREFIX'
        elif 'Durum ve şirket' in message:
            key = 'WORKFLOW_SUMMARY.STATUS_COLUMN'
        raise SettingsError(key, message) from exc


def column_references(settings: FusionSettings, name: str) -> list[str]:
    cfg = settings.config
    keys = [key for key in COLUMN_LIST_KEYS if name in cfg[key]]
    if name in settings.required_column_refs:
        keys.append('ROW_REQUIRED_COLUMNS')
    if cfg['ROW_ID_COLUMN'] == name:
        keys.append('ROW_ID_COLUMN')
    if name != 'Klasör' and any(dimension == name for dimension, _ in cfg['CHARTS']):
        keys.append('CHARTS')
    keys.extend(key for key in ('WORKFLOW_SUMMARY.STATUS_COLUMN', 'WORKFLOW_SUMMARY.COMPANY_COLUMN')
                if get_value(cfg, key) == name)
    return keys


def rename_column(settings: FusionSettings, old: str, new: str) -> FusionSettings:
    """Rename standard references; source-header requirements deliberately remain literal."""
    result = copy.deepcopy(settings)
    result.columns = tuple(replace(column, name=new) if column.name == old else column
                           for column in result.columns)
    for key in column_references(settings, old):
        value = get_value(result.config, key)
        if key == 'CHARTS':
            value = tuple((new if dimension == old else dimension, kind) for dimension, kind in value)
        elif key in (*COLUMN_LIST_KEYS, 'ROW_REQUIRED_COLUMNS'):
            value = tuple(new if item == old else item for item in value)
        else:
            value = new
        set_value(result.config, key, value)
    result.required_column_refs = tuple(new if name == old else name for name in settings.required_column_refs)
    return result


def remove_column(settings: FusionSettings, name: str) -> FusionSettings:
    references = column_references(settings, name)
    if references:
        raise SettingsError('COLUMN_SCHEMA', 'Önce sütun bağlantılarını kaldırın: ' + ', '.join(references))
    result = copy.deepcopy(settings)
    result.columns = tuple(column for column in result.columns if column.name != name)
    return result


def _profile_columns(items: Any) -> tuple[core.ColumnSpec, ...]:
    if not isinstance(items, list):
        raise SettingsError('COLUMN_SCHEMA', 'Sütunlar liste olmalı.')
    columns = []
    allowed = {'name', 'aliases', 'required', 'threshold', 'width'}
    for item in items:
        if not isinstance(item, dict) or 'name' not in item or set(item) - allowed:
            raise SettingsError('COLUMN_SCHEMA', 'Geçersiz veya bilinmeyen sütun alanı.')
        values = dict(item)
        if isinstance(values.get('aliases'), list):
            values['aliases'] = tuple(values['aliases'])
        columns.append(core.ColumnSpec(**values))
    return tuple(columns)


def load_profile(path: Path) -> FusionSettings:
    """Load a version-1 profile, merging missing config keys with current engine defaults."""
    payload = json.loads(path.read_text(encoding='utf-8'))
    required = {'version', 'config', 'columns'}
    if (not isinstance(payload, dict) or not required <= set(payload)
            or set(payload) - required - {'required_column_refs'}):
        raise ValueError('Profil version, config ve columns alanlarından oluşmalı.')
    if type(payload['version']) is not int or payload['version'] != 1:
        raise ValueError('Desteklenmeyen profil sürümü; sürüm 1 gerekli.')
    config = payload['config']
    allowed = {field.key.split('.')[0] for field in FIELDS} - PROFILE_EXCLUDED
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError('Profilde bilinmeyen veya kaydedilemeyen ayar var.')
    result = default_settings()
    result.columns = _profile_columns(payload['columns'])
    refs = payload.get('required_column_refs', [])
    if not isinstance(refs, list):
        raise SettingsError('ROW_REQUIRED_COLUMNS', 'Şema bağlantıları liste olmalı.')
    result.required_column_refs = tuple(refs)
    for key, value in config.items():
        if key == 'WORKFLOW_SUMMARY':
            if not isinstance(value, dict) or set(value) - set(result.config[key]):
                raise SettingsError(key, 'Bilinmeyen veya geçersiz iş akışı ayarı.')
            result.config[key].update(value)
        else:
            result.config[key] = value
    result.config['OVERWRITE'] = False
    validate_settings(result)
    for field in FIELDS:
        value = get_value(result.config, field.key)
        if isinstance(value, list):
            value = tuple(tuple(item) if isinstance(item, list) else item for item in value)
            set_value(result.config, field.key, value)
    return result


def save_profile(path: Path, settings: FusionSettings) -> None:
    """Atomically save validated settings; paths and overwrite permission are session-only."""
    validate_settings(settings)
    payload = {'version': 1,
               'config': {key: value for key, value in settings.config.items() if key not in PROFILE_EXCLUDED},
               'columns': [asdict(column) for column in settings.columns],
               'required_column_refs': settings.required_column_refs}
    data = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.fusion-profile-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
