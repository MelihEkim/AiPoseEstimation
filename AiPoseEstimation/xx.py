import os
import cv2
import mediapipe as mp
import numpy as np
import pygame
from gtts import gTTS

# Pygame başlat (ses çalmak için)
pygame.init()  # Pygame'i başlatıyoruz
pygame.font.init()  # Font modülünü başlatıyoruz
pygame.mixer.init()

# Mediapipe başlat
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# Ana dizin belirleme
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Egzersiz hataları ve doğru hareketler
exercise_instructions = {
    "Squat": {
        "dizler": ("Dizlerin parmak uçlarını geçmemeli.", "Dizlerini büküp kalçanı geriye doğru çıkar, sırtını dik tut."),
        "sırt": ("Sırtın dik olmalı.", "Dizlerini bükerek kalçanı geriye doğru çıkar, sırtını düz tut.")
    },
    "Push-up": {
        "vücut": ("Vücudun düz olmalı.", "Vücudunu düz tutarak, ellerini omuz genişliğinde aç ve yere doğru in."),
        "kalça": ("Kalçan çok yukarıda ya da aşağıda olmamalı.", "Vücudunu düz tutarak, ellerini omuz genişliğinde aç ve yere doğru in.")
    },
    "Plank": {
        "vücut": ("Vücudun dümdüz olmalı.", "Bacaklarını düz tutarak ve ellerini omuz genişliğinde açarak düz bir çizgide dur."),
        "kalça": ("Kalçan çok yukarıda veya aşağıda olmamalı.", "Vücudunu düz tutarak, kalçanı hafifçe yukarıda tutmaya dikkat et.")
    },
    "Lunges": {
        "diz": ("Diz 90 derece açıda olmalı.", "Öndeki dizini 90 derece bükerek, arka bacağını geriye doğru uzat."),
        "öne eğilme": ("Öne fazla eğilmemelisin.", "Dik durarak dizini bük ve kalçanı aşağıya doğru indir.")
    },
    "Biceps Curl": {
        "dirsek": ("Dirsekler sabit olmalı.", "Dirseklerini sabit tutarak sadece ön kolunu hareket ettir."),
        "ön kol": ("Sadece ön kol hareket etmeli.", "Ön kolunu yukarıya doğru bükerek, dirseklerini sabit tut.")
    },
    "Deadlift": {
        "sırt": ("Sırtın düz olmalı.", "Sırtını düz tutarak, kalçanı geri doğru it ve dizlerini bükerek vücudunu yukarı kaldır."),
        "kalça": ("Kalçan çok yukarıda olmamalı.", "Kalçanı biraz aşağıda tutarak, sırtını düz tutmaya özen göster.")
    },
    "Side Plank": {
        "denge": ("Vücudun düz bir çizgide olmalı.", "Vücudunu düz bir çizgiye getirerek, dengeyi sağla.")
    },
    "Burpee": {
        "squat": ("Squat aşaması doğru yapılmalı.", "Dizlerini bükerek kalçanı geriye doğru çıkar ve yere doğru in."),
        "şınav": ("Şınav düzgün olmalı.", "Şınav aşamasında vücudunu düz tutarak, ellerini yere koy ve vücudunu aşağı indir.")
    },
    "Jumping Jack": {
        "kollar": ("Kollar tam açılmalı.", "Kollarını tam olarak açarak, bacaklarını geniş bir şekilde aç."),
        "bacaklar": ("Bacaklar yeterince açılmalı.", "Bacaklarını geniş bir şekilde açarak, kollarını yukarı doğru kaldır.")
    },
    "Mountain Climber": {
        "tempo": ("Hareketin temposunu korumalısın.", "Hareketi hızlı ve düzenli bir şekilde yaparak bacaklarını çekip ileri uzat.")
    }
}

# TTS ile seslendirme fonksiyonu
def play_tts(text, filename="correction.mp3"):
    """ Verilen metni seslendir ve oynat """
    tts_path = os.path.join(BASE_DIR, "sounds", filename)
    tts = gTTS(text=text, lang="tr")
    tts.save(tts_path)

    # Eğer müzik çalıyorsa, yeni bir ses başlamadan önce bitmesini bekle
    if pygame.mixer.music.get_busy():  # Eğer müzik çalıyorsa
        pygame.mixer.music.stop()  # Önceki sesi durdur

    pygame.mixer.music.load(tts_path)
    pygame.mixer.music.play()

    # Ses bitene kadar bekle
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)  # 10ms bekle, sesin bitmesini kontrol et

# Üç nokta arasındaki açıyı hesapla
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cos_theta = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    return np.degrees(np.arccos(cos_theta))

# Metin çizme fonksiyonu (Türkçe karakter desteğiyle)
def draw_text(frame, text, position, font=cv2.FONT_HERSHEY_SIMPLEX, size=0.7, color=(0, 255, 255), thickness=2):
    return cv2.putText(frame, text, position, font, size, color, thickness, cv2.LINE_AA)

# Egzersiz seçme
exercises = list(exercise_instructions.keys())
print("Egzersiz Seçiniz:")
for i, exercise in enumerate(exercises, start=1):
    print(f"{i}. {exercise}")

selected_index = int(input(f"Seçiminizi yapın (1-{len(exercises)}): ")) - 1
selected_exercise = exercises[selected_index]

# Kamera başlat
cap = cv2.VideoCapture(0)

last_errors = set()  # Önceki tespit edilen hatalar
no_movement_counter = 0  # Hareket algılanmazsa sayaç
is_moving = False  # Hareket kontrolü

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # BGR -> RGB dönüştür
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_frame)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        h, w, _ = frame.shape

        # Açıyı hesapla (Sol ve Sağ kol ayrı)
        left_angle = calculate_angle(
            (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x * w, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y * h),
            (landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].x * w, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].y * h),
            (landmarks[mp_pose.PoseLandmark.LEFT_WRIST].x * w, landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y * h)
        )

        right_angle = calculate_angle(
            (landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y * h),
            (landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW].y * h),
            (landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].y * h)
        )

        # Hata kontrolü
        current_errors = set()
        for error, (message, correct_move) in exercise_instructions[selected_exercise].items():
            if error == "dirsek" and not (30 <= left_angle <= 160):
                current_errors.add("dirsek")
            if error == "dirsek" and not (30 <= right_angle <= 160):
                current_errors.add("dirsek")
                
        # Hareketsizlik algılama
        if not current_errors:
            if is_moving:
                no_movement_counter += 1
                if no_movement_counter > 30:  # Hareketsizlik kontrolü
                    draw_text(frame, "⚠️ Hareketsizsin!", (50, 50), color=(0, 0, 255))
            else:
                draw_text(frame, "✅ HAREKET DOĞRU!", (50, 50), color=(0, 255, 0))
                correct_move_text = "Doğru hareket: " + exercise_instructions[selected_exercise]["dirsek"][1]
                play_tts(correct_move_text)  # Doğru hareketi seslendir
            is_moving = True  # Hareket başladı
        else:
            is_moving = False  # Hata varsa hareket durdu

        # Hata değişirse sesli uyarı ver
        if current_errors != last_errors:
            if current_errors:
                alert_text = " ve ".join([exercise_instructions[selected_exercise][err][0] for err in current_errors])
                play_tts(alert_text)
            last_errors = current_errors.copy()

        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow("Egzersiz Takibi", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
