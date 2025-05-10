import pyttsx3
import threading
import time

audio_lock = threading.Lock()

def speak(text):
    with audio_lock:
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 130)
            engine.setProperty('volume', 1.0)

            voice_id = None
            voices = engine.getProperty('voices')
            for voice in voices:
                if "female" in voice.name.lower() or "kadın" in voice.name.lower():
                    voice_id = voice.id
                    break
            if voice_id:
                engine.setProperty('voice', voice_id)

            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print("speak() hatası:", str(e))

def stop_audio():
    # Artık engine.stop() gerekmiyor çünkü engine lokal
    pass

def play_combined_instruction(movement):
    tarif_giris = "Hareketi yanlış yapıyorsunuz, dikkatli olun. Şimdi tarif ediyorum. "

    aciklamalar = {
        "squat": "Squat için: Ayaklar omuz genişliğinde açık, sırt düz, kalçayı geriye itin.",
        "pushup": "Şınav için: Vücut düz, dirsekler 90 dereceye inip kalkmalı.",
        "plank": "Plank için: Vücut düz bir çizgi halinde, kalça düşmemeli.",
        "lunge": "Lunge için: Öndeki diz 90 derece olmalı, arka diz yere yaklaşmalı.",
        "jumping_jack": "Jumping Jack için: Kollar yukarı, ayaklar yana zıplayarak açılır ve kapanır.",
        "situp": "Sit-up için: Sırt yere yatık, eller başta, gövdeyi yukarı kaldır.",
        "mountain_climber": "Mountain Climber için: Plank pozisyonunda dizleri sırayla göğse çek.",
        "side_plank": "Side Plank için: Vücut yana dönük düz bir çizgide olmalı.",
        "shoulder_press": "Shoulder Press için: Dirsekleri 90 derece bük, yukarı doğru uzat.",
        "high_knees": "High Knees için: Dizleri sırayla göğse doğru hızlıca kaldır.",
        "dumbbell_curl": "Dambıl hareketi için: Dirseği sabit tutarak ön kola ağırlığı yukarı çek, yavaşça indir."
    }

    tarif_detay = aciklamalar.get(movement, "Bu hareketin açıklaması bulunamadı.")
    metin = tarif_giris + tarif_detay

    def thread_function():
        time.sleep(0.2)
        speak(metin)

    threading.Thread(target=thread_function, daemon=True).start()

def create_audio_feedback(text):
    def thread_function():
        time.sleep(0.2)
        speak(text)

    threading.Thread(target=thread_function, daemon=True).start()