# MotionMind - Akıllı Egzersiz Asistanı

MotionMind, web kameranızı kullanarak yaptığınız egzersizleri gerçek zamanlı olarak algılayan, duruşunuzu değerlendiren, tekrar sayan ve size sesli geri bildirimlerle yardımcı olan bir Flask tabanlı web uygulamasıdır. MediaPipe ile duruş tahmini ve OpenCV ile görüntü işleme teknolojilerini kullanır. Kullanıcıların gelişimlerini takip edebilmeleri için antrenman geçmişlerini Firebase Realtime Database üzerinde saklar.

## Özellikler

* **Kullanıcı Kimlik Doğrulama:** Güvenli kayıt ve giriş sistemi.
* **Çeşitli Egzersizler:**
    * Squat
    * Push-up (Şınav)
    * Plank
    * Lunge
    * Jumping Jack
    * Sit-up (Mekik)
    * Mountain Climber
    * Side Plank
    * Shoulder Press
    * High Knees
    * Dumbbell Curl
    * Lateral Raise
    * Biceps Hammer Curl
* **Gerçek Zamanlı Duruş Tespiti:** MediaPipe Pose ile eklem noktalarının takibi.
* **Tekrar Sayma:** Her egzersiz için doğru formda yapılan tekrarların sayılması.
* **Sesli Geri Bildirim:**
    * Egzersize başlarken hareketin doğru yapılışı hakkında talimatlar.
    * Doğru yapılan her tekrarda veya doğru formda duruşta tebrik mesajı.
* **Süre Takibi:** Belirlenen süre boyunca egzersiz yapma imkanı.
* **Antrenman Geçmişi:** Yapılan antrenmanların (tarih, hareket, tekrar, süre) kaydedilmesi ve görüntülenebilmesi (Firebase).
* **Gelişim Grafiği:** Haftalık toplam tekrar sayılarının grafiksel gösterimi.
* **Chatbot Asistanı:** Site kullanımı ve egzersizler hakkında bilgi alabileceğiniz yardımcı bir chatbot.
* **Duraklatma/Devam Etme:** Egzersiz seansı sırasında mola verme imkanı.

## Kullanılan Teknolojiler

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, JavaScript
* **Duruş Tahmini:** Google MediaPipe (Pose)
* **Görüntü İşleme:** OpenCV
* **Veritabanı & Kimlik Doğrulama:** Firebase (Pyrebase4 kütüphanesi ile)
* **Sesli Geri Bildirim:** pyttsx3
* **Grafik:** Chart.js (templates/progress.html içinde)
