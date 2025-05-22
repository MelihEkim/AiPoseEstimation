import cv2
import sys
import time
from datetime import datetime
from exercises import squat, pushup, plank, lunge, jumping_jack, situp, mountain_climber, side_plank, shoulder_press, high_knees, dumbbell_curl
from utils import draw_timer, draw_success
from audio_utils import create_audio_feedback, play_correct_instruction, stop_audio
from analysis_utils import get_firebase
import mediapipe as mp
import threading

# Kamerayı thread ile yöneten sınıf
class VideoStream:
    def __init__(self, src=0, width=640, height=480):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while self.running:
            self.ret, self.frame = self.cap.read()

    def read(self):
        return self.ret, self.frame

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

# Parametreler
movement = sys.argv[1]
duration_min = int(sys.argv[2])
user_email = sys.argv[3]
duration_sec = duration_min * 60

# Video akışını başlat
vs = VideoStream()
time.sleep(1)

pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5)

count = 0
stage = None
uyari_verildi = False
dogru_yapiliyor = False
kayit_edildi = False
last_instruction_time = 0
start_time = time.time()
initial_instruction_given = False

module_map = {
    "squat": squat,
    "pushup": pushup,
    "plank": plank,
    "lunge": lunge,
    "jumping_jack": jumping_jack,
    "situp": situp,
    "mountain_climber": mountain_climber,
    "side_plank": side_plank,
    "shoulder_press": shoulder_press,
    "high_knees": high_knees,
    "dumbbell_curl": dumbbell_curl
}
movement_module = module_map[movement]

print("Kamera thread ile başlatıldı.")


if not initial_instruction_given:
    play_correct_instruction(movement)
    initial_instruction_given = True

while True:
    success, frame = vs.read()
    if not success:
        break

    elapsed_time = int(time.time() - start_time)
    remaining_time = max(0, duration_sec - elapsed_time)
    minutes = remaining_time // 60
    seconds = remaining_time % 60

    frame = cv2.flip(frame, 1)
    frame, count, stage, uyari, dogru = movement_module.detect(frame, count, stage, pose)

    if movement not in ["plank", "side_plank"]:
        cv2.putText(frame, f'{movement} Tekrar: {count}', (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    draw_timer(frame, minutes, seconds)

    now = time.time()
    if uyari:
        if not uyari_verildi or now - last_instruction_time > 10:
            uyari_verildi = True
            last_instruction_time = now
            create_audio_feedback("Hareketi yanlış yapıyorsunuz, dikkatli olun. Şimdi tarif ediyorum.")
            play_correct_instruction(movement)
    else:
        uyari_verildi = False
        stop_audio()

    if dogru:
        draw_success(frame)

    if remaining_time <= 0 and not kayit_edildi:
        kayit_edildi = True
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kayit = {
            "hareket": movement,
            "tekrar": count,
            "sure": duration_sec // 60,
            "tarih": tarih
        }
        user_key = user_email.replace(".", "_")
        get_firebase().child("users").child(user_key).child("history").push(kayit)
        stop_audio()
        
    cv2.imshow('MotionMind - Spor Takibi', frame)

    if cv2.waitKey(1) & 0xFF == 27 or remaining_time <= 0:
        break

vs.stop()
cv2.destroyAllWindows()
print("Kamera kapatıldı.")

