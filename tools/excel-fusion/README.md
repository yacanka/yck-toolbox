# Excel Fusion

Excel kaynaklarını birleştiren mevcut motorun Türkçe masaüstü arayüzü.
Arayüz ve komut satırı aynı `excel_fusion.py` raporlama motorunu kullanır.

## Çalıştırma

Python 3.11 ve Tcl/Tk gerekir. Windows'ta python.org kurulumunun Tcl/Tk seçeneği açık olmalıdır.

```bat
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip --disable-pip-version-check install --no-index --find-links=wheelhouse --only-binary=:all: -r requirements.txt
.\.venv\Scripts\python excel_fusion_gui.py
```

Kurulumdan önce aşağıdaki **Offline paket hazırlığı** bölümüne göre `wheelhouse` klasörünü doldurun.

macOS/Linux'ta Tk desteği olan Python ile `python3 excel_fusion_gui.py` çalıştırılabilir.
`python -m tkinter` kurulumun pencere açabildiğini kontrol eder.

## Kullanım

1. Kaynak klasörünü ve çıktı `.xlsx` dosyasını seçin.
2. **Alt klasöre göre:** her ilk düzey alt klasör ayrı rapor grubu olur. Ana klasördeki
   dosyaları dahil etmek için ilgili kutuyu işaretleyin.
3. **Sayfa adına göre:** aynı adlı sayfalar tüm alt klasörlerden ve ana klasörden birleştirilir.
4. **Sütunlar**, **Eşleştirme**, **Satır kuralları** ve **Rapor** sekmelerinden ayarları
   düzenleyin. Başlık aramasının başlangıcı ve sonu seçilebilir; başlık satırı tercih edilen konumdur.
5. **Ön kontrol** Excel üretmeden denetim çıkarır. **Rapor oluştur** Excel, denetim ve log üretir.
6. İşlem bitince raporu veya çıktı klasörünü açın. Uyarı, hata, boş sonuç ve karantina
   sayıları ayrıca gösterilir; denetim sayfaları ayrıntıları içerir.

Kaynak dosyalar değiştirilmez. Var olan kaynak Excel'in üzerine yazılamaz.
**Mevcut Excel Fusion raporunu yenile** yalnızca motorun rapor işareti taşıyan dosyalara izin verir.
Ön kontrol dahil her çalıştırma aynı çıktı adına ait `.log` ve `.denetim.jsonl` dosyalarını yeniler.
Bu dosyalar kaynak verileri içerebilir; raporla aynı erişim kurallarıyla saklayın.
İşlem sürerken yeni işlem başlatma ve pencere kapatma engellenir. Zorla iptal düğmesi yoktur.
Arayüz motorun mevcut `CONFIG` ve `COLUMN_SCHEMA` değerleriyle açılır. Her çalışma bağımsız
bir ayar kopyası kullanır; motorun kaynak kodu ve global ayarları değiştirilmez.

### Dinamik ayarlar ve sütunlar

- **Dosyalar:** yollar, gruplama, uzantılar, hariç tutulan klasör/dosya/sayfalar,
  gizli sayfalar ve hata/yenileme seçenekleri.
- **Sütunlar:** sütun ekleme, silme, yukarı/aşağı taşıma; standart ad, alternatif
  başlıklar, başlıkta zorunluluk, özel benzerlik eşiği ve Excel genişliği.
  Değişikliği **Sütunu uygula** ile onaylayın. Boş özel eşik genel eşiği kullanır.
- **Eşleştirme:** başlık aralığı/yüksekliği, metin okuma modu, referans sütunları,
  minimum eşleşme sayıları ve benzerlik eşikleri.
- **Satır kuralları:** doluluk koşulları, kayıt kimliği/regex, dipnot etiketleri,
  metin temizleme, üstten doldurma ve tekrar kontrolü. Boş kayıt kimliği seçimi
  kaynak Excel satır numarasını kullanır.
- **Rapor:** başlık ve özet sayfası, ek sütun öneki, tarih biçimleri, sayfa satır sınırı,
  en fazla dört grafik ve iş akışı özeti. Motorun renk paleti ve sabit rapor metinleri değişmez.

Listelerde değeri seçip/yazıp **Ekle** düğmesine basın; seçili öğeyi **Sil** ile kaldırın.
Tamamlanmamış liste veya sütun girişleri kaydetme/çalıştırma öncesinde bildirilir.
Sayfa adına göre gruplamada kök dosyalar otomatik dahil edilir. Kullanılmayan seçenekler
devre dışı görünür; değerleri korunur. İşlem sürerken tüm düzenleme kontrolleri kilitlenir.

**Başlıkta zorunlu** işareti, sütun bulunmayan sayfanın alınmamasını sağlar.
**Her satırda dolu olması gereken sütunlar** ise boş değeri olan satırı karantinaya alır.
Bu listede **Şema sütunu** bağlantısı yeniden adlandırmayı izler. **Kaynak başlığı**
serbest metindir ve aynı kalır; şemada bulunmayan kaynak başlıkları da kullanılabilir.
Listeden sütun seçmek şema bağlantısını seçer; gerekirse yanındaki türü değiştirin.
Bağlantısı bulunan sütun silinmeden önce ilgili seçimler kaldırılmalıdır.

### JSON ayar profilleri

**Profil kaydet** ile ayarları ve sütun sırasını UTF-8 JSON dosyasına kaydedin;
**Profil yükle** ile tekrar kullanın. Son oturum otomatik kaydedilmez.
Kaynak/çıktı yolları ve raporun üzerine yazma izni profile dahil edilmez. Profil yükleme
ve **Varsayılanlara dön**, mevcut yolları korur ve yenileme iznini kapatır.
Kaydedilmemiş değişiklikler yükleme, sıfırlama ve kapanış öncesinde bildirilir.

Profil sürümü `1` olup `version`, `config`, `columns` ve isteğe bağlı
`required_column_refs` alanlarını içerir. Son alan yalnızca arayüzdeki zorunlu sütun
bağlantılarını saklar; motorun veri formatı değişmez. Eski/elle yazılmış profillerde bu
alan yoksa zorunlu sütun adları kaynak başlığı olarak korunur. Eksik konfigürasyon
anahtarları güncel motor varsayılanlarından tamamlanır. Bilinmeyen alan, desteklenmeyen
sürüm veya geçersiz değer varsa profil reddedilir ve mevcut form korunur.
Yazma başarısız olursa mevcut profil dosyası korunur.

`CONFIG["ROW_REQUIRED_COLUMNS"]`, `COLUMN_SCHEMA` listesinden bağımsız ve öncelikli
bir karantina kuralıdır. Örneğin `"ROW_REQUIRED_COLUMNS": ("Entity", "Notes")`
ayarında bu iki sütunun **her biri** dolu olmalıdır; herhangi biri boşsa satır
`ZORUNLU_ALAN_BOŞ: <sütun adı>` nedeniyle karantinaya alınır. Kaynak başlığı veya
eşlenen çıktı adı kullanılabilir; şema dışındaki kaynak başlıkları da desteklenir.
Başlık karşılaştırmasında mevcut harf/boşluk/noktalama normalizasyonu kullanılır.
Kaynakta bulunmayan sütun boş kabul edilir. Kontrol üst satırdan doldurmadan ve diğer
karantina kurallarından önce yapılır. Boş metin, yalnızca boşluk ve sonucu okunamayan
formül veri sayılmaz; `0` ve `False` veri sayılır. `()` bu ek kontrolü kapatır
(varsayılan). Tamamen boş satırlar atlanır; diğer karantina kuralları geçerliliğini korur.

## Windows EXE paketleme

Windows x64 üzerinde Python 3.11 kurun; Tcl/Tk seçeneğini açık tutun.
`build_windows.bat` dosyasına çift tıklayın veya Komut İstemi (cmd.exe) üzerinden çalıştırın:

```bat
build_windows.bat
```

PowerShell gerekmez. BAT dosyası Python launcher (`py -3.11`) veya PATH üzerindeki
`python` komutunu kullanır; Python sürümü ve x64 mimarisi kontrol edilir.
Pencere sonunda açık kalır; otomatik çalıştırmalar için `build_windows.bat --no-pause` kullanın.
Hata halinde sıfırdan farklı çıkış kodu döner. Paketleme adımları `build_windows.py` içindedir.

Betik bağımsız bir build ortamı kurar, bağımlılıkları yükler, tüm testleri çalıştırır,
PyInstaller ile konsolsuz EXE üretir. Ardından **üretilen EXE'yi** açarak Tk ve
Excel okuma/yazma kontrolü yapar. Kontrol başarısızsa dağıtım ZIP'i oluşturmaz.
Tcl/Tk veri dizinleri çalışan Tk yorumlayıcısından alınarak EXE'ye açıkça eklenir;
`init.tcl` veya `tk.tcl` eksikse paketleme durur. EXE açılırken `Can't find a usable
init.tcl` hatası alırsanız güncel build betiğiyle yeniden paketleyin ve yeni
`dist/windows-<zaman>/ExcelFusion/ExcelFusion.exe` dosyasını kullanın. Hata Python
ortam kontrolünde de oluşuyorsa Python 3.11 x64 kurulumunun Tcl/Tk bileşenini onarın.
Kurulum önce proje kökündeki `wheelhouse/` klasöründen offline olarak denenir.
Klasör yoksa, boşsa veya yerel kurulum başarısız olursa betik PyPI üzerinden gerekli
uyumlu wheel paketlerini indirir ve `wheelhouse/` içine kaydeder. Ardından kurulum
bu klasörden yeniden yapılır; indirilen paketler sonraki offline build'lerde kullanılabilir.
Gereksinim dosyalarındaki sabit sürümler ve yalnızca wheel kullanımı korunur.
İndirme veya yeniden kurulum başarısızsa build durur; ayrıntılar pip çıktısında gösterilir.
Uygulama çalışırken internet veya Excel kurulumu gerekmez.

Çıktılar `dist/windows-<zaman>/` altındadır:

- `ExcelFusion/ExcelFusion.exe`: Python/Tk, Excel bağımlılıkları, README ve lisansları içeren tek dosyalı uygulama.
- `ExcelFusion/licenses/`: bağımlılık lisans bildirimleri.
- `ExcelFusion-Windows-x64.zip`: kullanıcıya verilecek taşınabilir paket.
- `smoke-result.json`: paketlenmiş uygulamanın kontrol sonucu.
- `build-metrics.json`: açılmış klasör/ZIP boyutu, süreler ve ZIP SHA-256 özeti.

Kullanıcı ZIP'i çıkartıp `ExcelFusion.exe` dosyasını açabilir.
EXE tek başına da kopyalanıp çalıştırılabilir; yanındaki README ve lisans klasörü inceleme kolaylığı içindir. Her build ayrı dizine yazılır; önceki dağıtımlar korunur.
ZIP oluşturulmadan önce kurumsal dağıtım için gerekiyorsa kod imzası süreci ayrıca eklenmelidir.
Mevcut betik imzasız taşınabilir paket üretir.

### Offline paket hazırlığı

Tamamen offline build için önceden hazırlık yapabilirsiniz. İnternet erişimi olan bir
**Windows x64 / Python 3.11** bilgisayarda, aynı
`requirements.txt` ve `requirements-build.txt` dosyalarıyla bir kez çalıştırın:

```bat
py -3.11 -m pip download --only-binary=:all: --dest wheelhouse -r requirements-build.txt
```

Bu ayrı hazırlık komutu internet kullanır. Build betiği de yerel paketler yeterli
olmadığında otomatik olarak indirme yapar; internet erişimli build için önceden hazırlık gerekmez.
Oluşan `wheelhouse` klasörünü offline bilgisayarda proje köküne kopyalayın,
ardından `build_windows.bat` çalıştırın. Dolaylı bağımlılıkların wheel dosyaları da
klasörde bulunmalıdır; yalnızca uygulama paketlerini kopyalamak yeterli değildir.
Gereksinimler değiştiğinde paket klasörünü de aynı dosyalara göre hazırlayın.
Python 3.11 x64 ve Tcl/Tk hedef bilgisayara önceden kurulmuş olmalıdır.
`wheelhouse/` Git'e eklenmez. macOS/Linux kaynak kurulumunda o platform ve Python
sürümüne uygun wheel dosyalarını kullanın.

### Boyut ve açılış kararı

Tkinter Python ile gelir; Electron, web sunucusu, Qt, pandas veya NumPy eklenmez.
Mevcut XLS/XLSB desteğini korumak için `python-calamine` pakette tutulur.
Excel kütüphaneleri işlem başladığında yüklenir. Sistem yazı tipleri kullanılır;
font, görsel veya tarayıcı motoru indirilmez.

PyInstaller **onefile** kullanılır. Python/Tk ve bağımlılıklar EXE içindedir;
her açılışta geçici klasöre çıkarılır. Bu işlem açılış gecikmesi ekler ve geçici
klasörde yazma izni/boş alan gerektirir. ZIP, EXE ile okunabilir lisans bildirimlerini birlikte sunar.
UPX eklenmez. Boyut ve hız için doğrulanmamış bir MB/saniye garantisi verilmez;
betik gerçek paket üzerinden ölçer.

`ui_ready_seconds_after_python_entry`, Python girişinden pencerenin hazır olmasına kadar geçen
süredir; işletim sistemi yükleme süresini kapsamaz. `launch_and_report_smoke_seconds`, süreç
başlatma + arayüz + küçük örnek raporun toplamıdır; tek başına açılış süresi değildir.
Hedef bilgisayarda soğuk açılış ve büyük gerçek kaynaklarla ayrıca ölçüm yapılmalıdır.

PyInstaller Windows çıktısını Windows üzerinde üretir. macOS'taki testler Windows EXE
doğrulamasının yerine geçmez.

Kaynaklar: [PyInstaller çalışma modeli](https://pyinstaller.org/en/stable/operating-mode.html),
[platforma göre paketleme](https://pyinstaller.org/en/stable/usage.html).

## Dosya yapısı ve doğrulama

- `excel_fusion.py`: sütun eşleştirme, karantina ve raporlama motoru.
- `fusion_service.py`: ayar/yol doğrulaması ve motor çağrıları. `CONFIG` değiştirilmez.
- `fusion_settings.py`: ayar alanları, şema bağlantıları, doğrulama ve atomik JSON profil kaydı.
- `fusion_settings_ui.py`: sekmeli ayar formu, liste/grafik ve sütun düzenleyicileri.
- `excel_fusion_gui.py`: Tkinter kabuğu; tek işçi thread, kuyruk üzerinden UI güncellemeleri.
- `fusion_smoke.py`: paket içindeki Tk penceresi açıldıktan sonra Excel doğrulaması.
- `fusion_diagnostics.py`: test ve paket kontrolü için sabit örnek ayarlar/şema.
  Kullanıcının düzenlediği `CONFIG` ve `COLUMN_SCHEMA`, örnek verinin beklenen
  sonuçlarını değiştirmez; kontrol bitince özgün ayarlar geri yüklenir.
  Normal raporlarda kullanıcı ayarları geçerlidir. Paket kontrolü gerçek ayarların
  geçerliliğini de denetler; gerçek kaynak dosyalarının uyumluluğu ayrıca kontrol edilmelidir.
- `test_fusion_service.py`: CLI eşdeğerliği, kaynak koruması, hata ve dosya akışı testleri.
- `build_windows.bat`, `build_windows.py`, `collect_licenses.py`: build, paket kontrolü, lisanslar ve ZIP dağıtımı.
- `test_build_windows.py`: hata halinde durma, argüman/yol koruması, ZIP içeriği ve ölçüm testleri.
- `build_windows.ps1`: eski çağrılar için BAT dosyasına yönlendiren uyumluluk girişi; gerekli değildir.

```sh
python -m unittest discover -v
python -m compileall -q excel_fusion_gui.py fusion_settings.py fusion_settings_ui.py fusion_service.py fusion_smoke.py collect_licenses.py
python excel_fusion_gui.py --smoke-test smoke-result.json
```

Son komut ekran oturumu gerektirir ve gerçek bir Tk penceresini kısa süre açar.
`test_fusion_settings.py` ve servis testleri ekran gerektirmez. Gerçek arayüz testlerini
Tk destekli Python ve açık ekran oturumunda ayrıca çalıştırın:

```sh
FUSION_GUI_TESTS=1 python -m unittest test_fusion_gui -v
```

Windows cmd.exe için önce `set FUSION_GUI_TESTS=1`, ardından
`python -m unittest test_fusion_gui -v` çalıştırın. Normal test keşfi bu ekran testlerini
açıkça atlar; paketleme smoke testi gerçek pencereyi ayrıca açar.
XLS/XLSB için paket kontrolü native modülün yüklenmesini doğrular; gerçek legacy dosya
uyumluluğu mevcut çekirdeğe bağlıdır ve örnek XLS/XLSB dosyasıyla ayrıca doğrulanmalıdır.
