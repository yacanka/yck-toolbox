# Excel Fusion Dinamik Arayüz Implementation Plan

> For agentic workers: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Motoru değiştirmeden tüm konfigürasyonu ve sütun şemasını Türkçe arayüzden düzenlemek.

**Architecture:** Tkinter sekmeleri, ortak alan kataloğu ve bağımsız ayar modeli kullanır.
Servis her çalıştırmada konfigürasyon ve şemanın kopyasını mevcut motora geçirir.
JSON profilleri arayüz ayarlarını taşır; motorun veri formatını değiştirmez.

**Tech Stack:** Python 3.11+, Tkinter/ttk, mevcut Excel bağımlılıkları ve unittest.

**Spec:** Kullanıcının 2026-09-28 tarihinde onayladığı konuşma planı; kapsam aşağıda korunmuştur.

## Global Constraints

- `excel_fusion.py` değiştirilmez; motorun çalışma şekli, CLI ve kaynak koruması korunur.
- Yeni uygulama bağımlılığı eklenmez; mevcut Windows/offline paketleme akışı korunur.
- Tüm `CONFIG` alanları ve `COLUMN_SCHEMA` arayüzden düzenlenebilir.
- Sekmeler: Dosyalar, Sütunlar, Eşleştirme, Satır kuralları, Rapor.
- Sütun adları, alternatif başlıklar, zorunluluk, eşik, genişlik ve sıra düzenlenir.
- Sütun seçimleri şemayı izler; kaynak başlığı olarak yazılmış değerler korunur.
- Kaydet/yükle profilleri kullanılır; otomatik son oturum kaydı yapılmaz.
- Kaynak/çıktı yolları ve üzerine yazma izni profile dahil edilmez.
- İşlem boyunca form kilitlenir; Tk yalnızca ana thread üzerinde kullanılır.

## Review Focus

- Şema adı değişirken alias kullanan kaynaklarda zorunlu satır bağlantıları bozulmamalı.
- Geçersiz profil mevcut formu veya eski profil dosyasını bozmamalı.
- Başlıkta zorunluluk ve satır doluluğu farklı kurallar olarak sunulmalı.
- Tamamlanmamış liste/sütun girişleri sessizce kaybolmamalı.
- Küçük pencerede, klavyeyle ve yüksek ölçeklemede kontroller erişilebilir olmalı.

## Task 1: Ayar modeli ve profiller

Dosyalar: `fusion_settings.py`, `test_fusion_settings.py`.
Arayüzler: `FusionSettings`, `default_settings`, `validate_settings`, `load_profile`, `save_profile`.

- [x] Varsayılan kopyalama, alan kapsamı, geçersiz tür/sınır/alias, profil roundtrip ve atomik kayıt testleri.
- [x] Yeni modül bulunmadığında testlerin başarısız olduğunu doğrulama.
- [x] Alan kataloğu, motor doğrulamasına delegasyon, şema bağlantıları, sürüm 1 JSON profilleri.
- [x] Doğrudan ayar/profil testlerini geçirme.

## Task 2: Servis entegrasyonu

Dosyalar: `fusion_service.py`, `test_fusion_service.py`.
Arayüz: `RunOptions.settings: FusionSettings | None`; mevcut parametreler kendi alanlarında önceliklidir.

- [x] Özel şema, ayar snapshot'ı, mevcut API önceliği ve doğrudan motorla eşdeğerlik testleri.
- [x] Yeni RunOptions alanı bulunmadığında testi başarısız görme.
- [x] Validate/collect/save çağrılarında aynı konfigürasyon ve şemayı kullanma.
- [x] Servis testlerini geçirme; motor ve global ayarlar değişmez.

## Task 3: Sekmeli arayüz

Dosyalar: `excel_fusion_gui.py`, `fusion_settings_ui.py`, `test_fusion_gui.py`.
Arayüz: `SettingsPanel.get_settings()`, `set_settings()`, `set_running()`, `show_error()`.

- [x] Form roundtrip, bağımlılıklar, yeniden adlandırma, sıralama, hata gösterimi ve taslak koruma testleri.
- [x] Yeni panel/API bulunmadığında gerçek Tk testlerini başarısız görme.
- [x] Sekmeler, liste/grafik ve sütun düzenleyicileri; sabit işlem/sonuç alanı.
- [x] Profil yükleme/kaydetme/sıfırlama ve kaydedilmemiş değişiklik bildirimleri.
- [x] Gerçek Tk oturumunda arayüz testlerini geçirme.

## Task 4: Entegrasyon ve doğrulama

- [x] README ve Windows compile kontrolünü yeni modüller için güncelleme.
- [x] Bağımsız kod incelemesi; iki bulguyu regresyon testleriyle düzeltme.
- [x] Klavye odağındaki ekran dışı alanları görünür kılma.
- [x] Ruff ve Python derleme kontrolleri.
- [ ] Hedef Windows x64 ortamında EXE üretimi ve yüksek DPI kontrolü (macOS'ta gerçekleştirilemez).

## Uygulama kararları

- Kullanıcının onayladığı çalışma klasöründe değişiklikler hazırlanır; commit/push yapılmaz.
- `required_column_refs` profil metadata'sı şema bağlantısı ile kaynak başlığını ayırır.
  Bu alan motora geçirilmez. Alan bulunmayan sürüm 1 profillerinde değerler kaynak başlığıdır.
- Sütun silme bağlantı varsa engellenir; yeniden adlandırma açık bağlantıları günceller.
- Geçersiz JSON/tür/sürüm yüklemeleri forma uygulanmadan reddedilir.
- GUI testleri `FUSION_GUI_TESTS=1` ile ekran oturumunda etkinleşir; headless keşif bunları açıkça atlar.

## Doğrulama kaydı

- Başlangıç: 48 mevcut test geçti.
- Sonuç: Tk destekli Python 3.12 ile `FUSION_GUI_TESTS=1 python -m unittest discover -q`: 77 test geçti, atlanan test yok.
- Gerçek Tk penceresi ve Excel okuma/yazma smoke testi: `ok: true`.
- Ruff, compileall ve `git diff --check`: geçti.
- 760×680 pencerede Tk ölçekleri 1.5 ve 2.0: tüm işlem düğmeleri görünür.
- Motorun HEAD ve çalışma dosyası SHA-256 değerleri aynı: `896f50ac1c495ca6cdbf76ec66927850f2d019356ad52aad6e0c1104487e7cd0`.
- Standart proje sanal ortamında Tk modülü yok. GUI doğrulaması Tk içeren test runtime'ında yapıldı;
  mevcut `python-calamine==0.6.2` bağımlılığının bu runtime'a uygun wheel'i yalnızca `/tmp` altına kuruldu.
- Windows x64 EXE doğrulaması hedef Windows ortamına kalır.
