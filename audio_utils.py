
import pyttsx3
import threading
import time

audio_lock = threading.Lock()

ACIKLAMALAR = {
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
    "dumbbell_curl": "Dambıl hareketi için: Dirseği sabit tutarak ön kola ağırlığı yukarı çek, yavaşça indir.",
    "lateral_raise": "Lateral Raise için: Kollarınızı hafifçe bükerek veya düz tutarak omuz hizasına kadar yanlara doğru kaldırın ve yavaşça indirin. Gövdenizi dik tutun.",
    "biceps_hammer_curl": "Hammer Curl için: Avuç içleriniz vücudunuza bakacak şekilde dambılları tutun. Dirseklerinizi sabit tutarak ağırlıkları omuzlarınıza doğru kaldırın ve yavaşça başlangıç pozisyonuna indirin."
}

def speak(text):
    with audio_lock:
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 130) 
            engine.setProperty('volume', 1.0)

            voice_id = None
            voices = engine.getProperty('voices')
            
            for voice in voices:
                if "turkish" in voice.name.lower() or "türkçe" in voice.name.lower() or "female" in voice.name.lower() or "kadın" in voice.name.lower():
                    voice_id = voice.id
                    if "female" in voice.name.lower() or "kadın" in voice.name.lower(): 
                        break 
            if voice_id:
                engine.setProperty('voice', voice_id)
            
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"speak() fonksiyonunda hata: {e}")


def stop_audio():
    
    pass

def speak_exercise_explanation(movement):
    """Sadece egzersizin nasıl yapılacağını açıklar."""
    tarif_detay = ACIKLAMALAR.get(movement, "Bu hareketin açıklaması bulunamadı.")
    
    def thread_function():
        time.sleep(0.2) 
        speak(tarif_detay)

    threading.Thread(target=thread_function, daemon=True).start()

def speak_congratulations():
    """Sadece tebrik mesajını seslendirir."""
    message = "Tebrikler, doğru yaptınız!"
    
    def thread_function():
        time.sleep(0.2)
        speak(message)
        
    threading.Thread(target=thread_function, daemon=True).start()

def create_audio_feedback(text): 
    def thread_function():
        time.sleep(0.2)
        speak(text)
    threading.Thread(target=thread_function, daemon=True).start()
