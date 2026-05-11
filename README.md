# 🚀 Messaging App

Modern, nesne yönelimli (OOP) ve katmanlı mimari (DAO, Service, Model) prensiplerine sadık kalınarak Python ile geliştirilmiş, güvenli masaüstü anlık mesajlaşma uygulaması. Sunucu-İstemci (Client-Server) modeliyle çalışan proje, ham TCP soketleri ve PyQt6 arayüzü ile WhatsApp/Telegram benzeri pürüzsüz bir deneyim sunar.

## ✨ Temel Özellikler

* **Gerçek Zamanlı Haberleşme:** Özelleştirilmiş paketleme (marshalling/unmarshalling) altyapısı ve TCP soketleri ile kesintisiz, kayıpsız iletişim.
* **Çevrimdışı Öncelikli (Offline-First) Yapı:** İstemci tarafında çalışan yerel SQLite önbelleği (Cache DB) sayesinde, sunucu bağlantısı olmasa bile geçmiş mesajları görüntüleyebilme ve yeni mesajları bağlantı geldiğinde iletilmek üzere bekleme kuyruğuna (Pending) alma.
* **Gelişmiş Grup Yönetimi:** Grup oluşturma, üye ekleme/çıkarma, yönetici (admin) atama işlemleri.
* **Hibrit Güvenlik Mimarisi:** * Anahtar değişimi için **RSA** (Asimetrik).
  * Mesaj içeriklerinin şifrelenmesi için **Fernet** (Simetrik).
  * Kullanıcı parolalarının güvenliği için **SHA-256 + Rastgele Salt** hashleme algoritmaları.
* **Mesaj Durum Takibi (Okundu Bilgisi):** Tıpkı modern uygulamalardaki gibi *Gönderildi (✓)*, *İletildi (✓✓)* ve *Okundu (blue✓✓)* durum bildirimleri.
* **Zengin Medya ve Büyük Dosya Transferi:** Ağ tıkanıklığını (bottleneck) önlemek amacıyla dosya ve ses kayıtlarının 128 KB'lık parçalar (chunk) halinde iletilmesi.
* **Modern Kullanıcı Arayüzü (UI):** PyQt6 ile tasarlanmış tam duyarlı (responsive) Karanlık Tema (Dark Mode), Base64 avatar desteği, ses kaydetme ve sağ tık (context menu) aksiyonları.

---

## 🏗️ Mimari Tasarım

Proje, sorumlulukların net bir şekilde ayrıldığı (Separation of Concerns) 3 ana dizinden oluşmaktadır:

* `common/`: Hem sunucu hem de istemci tarafından ortak kullanılan Veritabanı Bağlantı Yöneticisi, Veri Modelleri (User, Message vb.), Kriptografi ve Paketleme (PacketHandler) sınıfları.
* `server/`: Gelen bağlantıları `Threading` ile asenkron olarak yöneten `ServerNetworkService`, istekleri işleyen Controller yapıları ve `database.db` ile iletişim kuran sunucu DAO katmanı.
* `client/`: PyQt6 ile yazılmış olay güdümlü (Event-Driven) kullanıcı arayüzü, arka planda sunucuyu dinleyen `ClientNetworkService` ve verileri yerel diske kaydeden `cache.db` DAO katmanı.

---

### Gereksinimler
* Python 3.8 veya üzeri
* Sanal ortam (Virtual Environment) önerilir.
