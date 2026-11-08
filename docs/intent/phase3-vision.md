# Confirmed Statement of Intent: Phase 3 — Vision (Ekran Görme & İnceleme)

* **Outcome:** Jarvis'e kullanıcının *"Ekranda ne görüyorsun?"*, *"Buradaki hatayı açıkla"*, *"Şu tablodaki toplam nedir?"* gibi sesli taleplerinde birincil ekranın o anki görüntüsünü RAM belleğe (in-memory) alıp Google Gemini Multimodal Vision API'sine aktaran, analiz sonucunu Jarvis hitap tarzıyla (*"efendim"*) 1-3 cümlelik özlü, doğal ve seslendirilebilir bir yanıt olarak kullanıcıya aktaran `ScreenInspectionTool` (`inspect_screen`) aracını kazandırmak.
* **User:** Bilgisayar başında çalışırken ekrandaki bir hata mesajını, açık olan dokümanı, grafiği veya pencereyi ellerini klavyeden kaldırmadan Jarvis'e sesli olarak inceletmek ve anında sesli geri bildirim almak isteyen kullanıcı.
* **Why now:** 1. Aşama ses ve persona döngüsü, 2. Aşama işletim sistemi araç motoru (Tool Engine) başarıyla tamamlandı. Asistanın kullanıcının baktığı ekranı da anlayabilmesi, onu sıradan bir sesli komut aracından gerçek bir akıllı çalışma arkadaşına dönüştürmek için en kritik görsel duyudur.
* **Success:** Kullanıcı *"Ekranda ne görüyorsun?"* veya *"Ekrandaki hataya bak"* dediğinde Jarvis'in ekranı anında dondurmadan/kasmadan yakalaması, Gemini Multimodal ile 2-3 saniye içinde analiz edip *"Ekranda VS Code açık ve konsolda Python SyntaxError hatası görünüyor efendim."* şeklinde net, kısa ve sesli bir yanıt vermesi.
* **Constraint:**
  - **Gizlilik & RAM Prensibi:** Alınan ekran görüntüleri kesinlikle diske yazılmayacak (`.png`, `.jpg` olarak kaydedilmeyecek), yalnızca RAM bellekte (`io.BytesIO`) tutulup API çağrısı sonrası bellekten temizlenecektir.
  - **On-Demand (Sadece İstendiğinde):** Ekran görüntüsü her sorguda değil, sadece kullanıcının ekrana dair bir şey sorduğu durumlarda (Gemini `inspect_screen` aracını çağırdığında) anlık olarak çekilecektir.
  - **Efendim Kuralı:** Yanıt sonunda tek bir *"efendim"* yer alacak, art arda cümlelerde papağan gibi tekrarlanmayacaktır.
  - **Hafiflik & Hız:** Görüntü aktarımı öncesinde gereksiz yüksek çözünürlük bant genişliğini ve kota tüketimini önlemek için optimize edilecek (en fazla 1920x1080 ölçeklendirme, JPEG %85 sıkıştırma).
* **Out of scope:**
  - Sürekli (live stream/video) ekran kaydı veya kullanıcının fare hareketlerini 60 FPS izleme.
  - Çoklu monitörlerde monitör seçimi için karmaşık GUI pencereleri (varsayılan olarak birincil monitör veya odaklı pencere yakalanacaktır).
  - Ekrandaki düğmelere otonom tıklama / OCR ile fare koordinatı üretip GUI otomasyonu yapma (ilerleyen otomasyon aşamalarına bırakılmıştır).
