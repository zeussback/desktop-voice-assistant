# Confirmed Statement of Intent: Phase 2 - OS Control & Tool Engine

* **Outcome:** Jarvis'e sesli komutlarla sistem ayarlarını (ses düzeyi, parlaklık, medya oynatma/durdurma) yönetebileceği, masaüstü uygulamalarını adıyla açıp kapatabileceği, web sitelerini ve Google aramalarını açabileceği; ilerideki karmaşık görevler (dosya yönetimi, otomasyonlar ve Aşama 3'teki Vision yeteneği) için genişletilmeye hazır modüler bir Araç Motoru (*Tool Engine / Function Calling*) kazandırmak.
* **User:** Günlük bilgisayar kullanımında eller serbest şekilde sesli komutlarla temel ayarları ve uygulamaları yönetmek isteyen kullanıcı.
* **Why now:** Aşama 1'deki ses döngüsü, Jarvis karakteri ve animasyonlu arayüz başarıyla tamamlandı; asistanı sadece konuşan bir modelden işletim sistemine hükmeden gerçek bir kişisel asistana dönüştürmek için en sağlam zemin bu araç motorudur.
* **Success:** *"Spotify'ı aç"*, *"Sesi %50 yap"*, *"YouTube'u aç"*, *"Chrome'u kapat"* gibi komutlarda Jarvis'in ilgili eylemi anında yerine getirip doğal bir sesli geri bildirim (*"Spotify açıldı efendim"*) vermesi; bilgisayarı kapatma gibi kritik sistem eylemlerinde ise sesli güvenlik teyidi istemesi.
* **Constraint:** Sıfır lisans maliyeti, arka planda hafif çalışan Python kütüphaneleri (`psutil`, `pycaw`, `screen_brightness_control`), Gemini Function Calling ile tam tip/şema uyumu ve Jarvis hitap tarzı (*"efendim"*).
* **Out of scope:** Pencere boyutlandırma ve taşıma işlemleri, otonom dosya/klasör silme/düzenleme ve kontrolsüz terminal komutları çalıştırma (ilerleyen aşamalara bırakılmıştır).
