# Confirmed Statement of Intent: Phase 4 — Kişisel Asistan & Sekreterlik

* **Outcome:** Jarvis'e Google Calendar ve Gmail hesaplarına (resmi OAuth 2.0 ile) bağlanarak takvim etkinliklerini ve teslim tarihlerini (*deadlines*) yönetme, gelen e-postaları özetleyip kategorize etme ve sabahları sesli olarak günün ajandasını (*"Bugün neyim var?"*, *"Günaydın"*) sunan kişisel bir sekreterlik yeteneği kazandırmak.
* **User:** Bilgisayar başında eller serbest şekilde sesli komutlarla takvimini, teslim tarihlerini ve e-posta kutusunu yönetmek; günün başlangıcında hızlıca odaklanması gereken acil işleri öğrenmek isteyen kullanıcı.
* **Why now:** Aşama 1 (Ses & Persona), Aşama 2 (İşletim Sistemi Araç Motoru) ve Aşama 3 (Ekran Görme / Vision) başarıyla tamamlandı; asistanı sadece bir işletim sistemi yöneticisi olmaktan çıkarıp gerçek bir kişisel dijital çalışma arkadaşına dönüştürmenin tam zamanı.
* **Success:** 
  1. *"12 Kasım saat 15'e proje toplantısı ekle"*, *"3 gün sonraya tez teslim tarihi ekle"* gibi komutlarda etkinliğin Google Calendar'a anında işlenmesi.
  2. *"Bugün neyim var?"*, *"Yarına ne yetişmeli?"*, *"X toplantısı ne zamandı?"* sorularına Jarvis'in doğrudan takvimi ve teslim tarihlerini tarayıp net sesli yanıt vermesi.
  3. *"Gelen kutumu özetle"* dendiğinde önemli e-postaları 1-2 cümlede sesli özetlemesi.
  4. *"Gereksiz abonelikleri temizle"* dendiğinde bulunan reklam/bülten listeleri için sesli teyit isteyip (*"X bülteninden çıkayım mı efendim?"*) onay gelirse abonelikten çıkarması.
  5. Sabah *"Günaydın"* dendiğinde günün randevularını, yaklaşan teslim tarihlerini ve acil mailleri akıcı bir sesli brifing olarak sunması.
* **Constraint:**
  - Sıfır ek maliyet; Google'ın resmi Python kütüphaneleri (`google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`).
  - Güvenlik & Gizlilik: Yerel `token.json` ile kalıcı yetki; kullanıcı şifresi asla saklanmaz.
  - Güvenlik Teyidi: Abonelikten çıkma veya e-posta silme gibi eylemlerde `ConfirmationPolicy.REQUIRE_CONFIRMATION` zorunludur.
  - Piper TTS Uyumlu: Tüm takvim ve e-posta yanıtları seslendirmeye uygun, net, 1-3 cümle ve tek bir *"efendim"* ile tamamlanacaktır.
* **Out of scope:**
  - Kullanıcının yerine kendi inisiyatifiyle yeni e-posta yazıp göndermek (Aşama 4 yalnızca okuma, özetleme ve abonelik temizleme odaklıdır).
  - Outlook / Exchange kurumsal posta sunucuları entegrasyonu (yalnızca Google Workspace / Gmail odaklıdır).
