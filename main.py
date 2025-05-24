from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify
import pyrebase
from datetime import datetime
import cv2
import mediapipe as mp
import threading
import time
import google.generativeai as genai
import os

from exercises import squat, pushup, plank, lunge, jumping_jack, situp, mountain_climber, side_plank, shoulder_press, high_knees, dumbbell_curl, lateral_raise, biceps_hammer_curl
from utils import draw_timer, draw_success
from audio_utils import speak_exercise_explanation, speak_congratulations, stop_audio
from analysis_utils import analyze_progress_chart_data, get_firebase, analyze_progress

def format_movement_name(name):
    """Egzersiz adını okunabilir formata çevirir."""
    return name.replace("_", " ").title()

app = Flask(__name__)
app.secret_key = 'gizli_anahtar'

firebaseConfig = {
    "apiKey": "AIzaSyCT4mQS-Pkjqn3FkmAcYxauqhkO62IgPxc",
    "authDomain": "fitness-app-b1ac4.firebaseapp.com",
    "databaseURL": "https://fitness-app-b1ac4-default-rtdb.europe-west1.firebasedatabase.app",
    "projectId": "fitness-app-b1ac4",
    "storageBucket": "fitness-app-b1ac4.appspot.com",
    "messagingSenderId": "390747608835",
    "appId": "1:390747608835:web:85c866bf913c232c887b36"
}
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()


YOUR_GEMINI_API_KEY = "AIzaSyBx-VICqvJhakcipZj0SC6LWRGDvKo4lkI" 
IS_GEMINI_CONFIGURED = False

if YOUR_GEMINI_API_KEY:
    try:
        genai.configure(api_key=YOUR_GEMINI_API_KEY)
        print(">>> Google Gemini API anahtarı başarıyla yapılandırıldı. <<<")
        IS_GEMINI_CONFIGURED = True
    except Exception as e:
        print(f"HATA: Google Gemini API anahtarı yapılandırılamadı: {e}")
        IS_GEMINI_CONFIGURED = False
else:
    print(">>> UYARI: Google Gemini API anahtarı boş! Lütfen main.py dosyasını düzenleyin. <<<")
    IS_GEMINI_CONFIGURED = False


movement = ""
duration_sec = 0
start_time = 0
pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5)
count = 0
stage = None
uyari_verildi = False
dogru_yapiliyor = False
kayit_edildi = False
user_email = ""
cap = None
vs = None
last_instruction_time = 0
is_paused = False
elapsed_before_pause = 0
last_congrats_time = 0
congrats_given_for_hold = False

module_map = {
    "squat": squat, "pushup": pushup, "plank": plank, "lunge": lunge,
    "jumping_jack": jumping_jack, "situp": situp, "mountain_climber": mountain_climber,
    "side_plank": side_plank, "shoulder_press": shoulder_press, "high_knees": high_knees,
    "dumbbell_curl": dumbbell_curl, "lateral_raise": lateral_raise, "biceps_hammer_curl": biceps_hammer_curl
}

# VideoStream Sınıfı ve stop_camera Fonksiyonu
class VideoStream:
    def __init__(self, src=0, width=640, height=480):
        global cap
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
        if hasattr(self, 'thread') and self.thread.is_alive():
             self.thread.join(timeout=1)
        if self.cap and self.cap.isOpened():
            self.cap.release()

def stop_camera():
    global cap, vs
    try:
        if vs is not None:
            vs.stop()
            vs = None
            time.sleep(0.5)
        if cap is not None and cap.isOpened():
            cap.release()
            cap = None
    except Exception as e:
        print(f"Kamera kapatma hatası: {str(e)}")

# generate_frames Fonksiyonu
def generate_frames():
    global count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, start_time, last_instruction_time, is_paused, elapsed_before_pause, vs, movement, duration_sec, user_email, pose, last_congrats_time, congrats_given_for_hold
    previous_rep_count_for_audio = count
    if not hasattr(generate_frames, 'last_count_for_visual'):
        generate_frames.last_count_for_visual = 0
    if vs is None or not vs.running :
        stop_camera()
        vs = VideoStream()
        time.sleep(1)
    if vs is None or not vs.ret:
        return
    last_frame_bytes = None
    while True:
        if vs is None or not vs.running:
             break
        success, frame = vs.read()
        if not success or frame is None:
            if last_frame_bytes:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + last_frame_bytes + b'\r\n')
            time.sleep(0.1)
            continue
        frame = cv2.flip(frame, 1)
        if is_paused:
            if last_frame_bytes is not None:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + last_frame_bytes + b'\r\n')
            else:
                time.sleep(0.1)
            continue
        current_loop_time = time.time()
        elapsed_time_since_start = int(current_loop_time - start_time)
        remaining_time = max(0, duration_sec - elapsed_time_since_start)
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        processed_frame, new_count, new_stage, uyari_status, dogru_status = module_map[movement].detect(frame.copy(), count, stage, pose)
        count = new_count
        stage = new_stage
        dogru_yapiliyor = dogru_status
        if movement not in ["plank", "side_plank"]:
            formatted_name = format_movement_name(movement)
            cv2.putText(processed_frame, f'{formatted_name} Tekrar: {count}', (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        draw_timer(processed_frame, minutes, seconds)
        now = time.time()
        if dogru_status:
            if movement not in ["plank", "side_plank"]:
                if count > previous_rep_count_for_audio:
                    if now - last_congrats_time > 4:
                        speak_congratulations()
                        last_congrats_time = now
                    previous_rep_count_for_audio = count
            else:
                if not congrats_given_for_hold:
                    if now - last_congrats_time > 4:
                        speak_congratulations()
                        last_congrats_time = now
                        congrats_given_for_hold = True
        else:
            if movement in ["plank", "side_plank"]:
                congrats_given_for_hold = False
        if movement in ["plank", "side_plank"]:
            if dogru_status:
                draw_success(processed_frame)
        else:
            if count > generate_frames.last_count_for_visual:
                draw_success(processed_frame)
                generate_frames.last_count_for_visual = count
        if remaining_time <= 0 and not kayit_edildi:
            kayit_edildi = True
            tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            kayit = {
                "hareket": movement,
                "tekrar": count,
                "sure": duration_sec // 60,
                "tarih": tarih
            }
            if user_email:
                user_key = user_email.replace(".", "_")
                try:
                    db.child("users").child(user_key).child("history").push(kayit)
                except Exception as e:
                    print(f"Firebase kayıt hatası: {e}")
            else:
                print("HATA: generate_frames - user_email boş, Firebase'e kayıt yapılamadı.")
            stop_audio()
            stop_camera()
            break
        try:
            ret_encode, buffer = cv2.imencode('.jpg', processed_frame)
            if not ret_encode:
                continue
            frame_bytes = buffer.tobytes()
            last_frame_bytes = frame_bytes
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Frame gönderme hatası: {e}")
            break
    if vs is not None and vs.running:
        stop_camera()


# --- Flask Rotaları ---
@app.route('/')
def home():
    stop_camera()
    return render_template("login.html", brand="MotionMind")

@app.route('/register', methods=['GET', 'POST'])
def register():
    stop_camera()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            auth.create_user_with_email_and_password(email, password)
            return redirect(url_for('home'))
        except Exception as e:
            error_message = str(e)
            if "EMAIL_EXISTS" in error_message: return "Bu e-posta zaten kayıtlı."
            elif "WEAK_PASSWORD" in error_message: return "Şifre çok zayıf. En az 6 karakter olmalı."
            elif "INVALID_EMAIL" in error_message: return "Geçerli bir e-posta adresi girin."
            else: return f"Kayıt başarısız: {error_message}"
    return render_template("register.html", brand="MotionMind")

@app.route('/login', methods=['POST'])
def login():
    global user_email
    stop_camera()
    email_form = request.form['email']
    password_form = request.form['password']
    try:
        auth.sign_in_with_email_and_password(email_form, password_form)
        session['user'] = email_form
        user_email = email_form
        return redirect('/select')
    except Exception as e:
        return f"Giriş başarısız: {str(e)}"

@app.route('/select')
def select():
    stop_camera()
    if 'user' not in session: return redirect('/')
    global user_email
    if not user_email and 'user' in session: user_email = session['user']
    return render_template("select.html", brand="MotionMind")

@app.route('/start', methods=['POST'])
def start():
    stop_camera()
    global movement, duration_sec, start_time, count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, last_instruction_time, is_paused, elapsed_before_pause, last_congrats_time, congrats_given_for_hold, user_email
    if 'user' not in session: return redirect('/')
    user_email = session['user']
    form_movement = request.form.get('movement')
    if form_movement: movement = form_movement.lower().replace(" ", "_")
    elif session.get('last_movement'): movement = session['last_movement']
    else: return redirect('/select')
    form_duration = request.form.get('duration')
    if form_duration: duration = int(form_duration)
    elif session.get('last_duration'): duration = int(session.get('last_duration'))
    else: return redirect('/select')
    duration_sec = duration * 60
    start_time = time.time()
    count = 0; stage = None; uyari_verildi = False; dogru_yapiliyor = False; kayit_edildi = False
    last_instruction_time = 0; is_paused = False; elapsed_before_pause = 0
    last_congrats_time = 0; congrats_given_for_hold = False
    if hasattr(generate_frames, 'last_count_for_visual'): delattr(generate_frames, 'last_count_for_visual')
    generate_frames.last_count_for_visual = 0
    session['last_movement'] = movement
    session['last_duration'] = duration
    speak_exercise_explanation(movement)
    return render_template("session_started.html", movement=format_movement_name(movement), duration=duration, brand="MotionMind")

@app.route('/video_feed')
def video_feed():
    if 'user' not in session: return Response("Yetkisiz erişim.", status=401)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/pause', methods=['POST'])
def pause():
    global is_paused, elapsed_before_pause, start_time
    if 'user' not in session: return '', 401
    if not is_paused:
        is_paused = True
        elapsed_before_pause = time.time() - start_time
        stop_audio()
    return '', 204

@app.route('/resume', methods=['POST'])
def resume():
    global is_paused, start_time, elapsed_before_pause
    if 'user' not in session: return '', 401
    if is_paused:
        is_paused = False
        start_time = time.time() - elapsed_before_pause
    return '', 204

@app.route('/completed')
def completed():
    stop_camera()
    if 'user' not in session: return redirect('/')
    current_user_email = session.get('user', user_email)
    if not current_user_email: return redirect('/')
    user_key = current_user_email.replace(".", "_")
    yorum = analyze_progress(db, user_key)
    completed_movement_name = format_movement_name(session.get('last_movement', movement))
    completed_rep_count = count
    completed_duration_min = session.get('last_duration', duration_sec // 60)
    return render_template("completed.html",
                           movement=completed_movement_name, count=completed_rep_count,
                           duration=completed_duration_min, hedef=completed_rep_count + 2,
                           yorum=yorum, brand="MotionMind")

@app.route('/history')
def history_route():
    stop_camera()
    if 'user' not in session: return redirect('/')
    current_user_email = session.get('user', user_email)
    if not current_user_email: return redirect('/')
    user_key = current_user_email.replace(".", "_")
    try: history_data = db.child("users").child(user_key).child("history").get().val()
    except Exception as e: print(f"Firebase'den geçmiş verisi alınırken hata: {e}"); history_data = None
    return render_template("history.html", history=history_data, brand="MotionMind")

@app.route('/progress')
def progress():
    stop_camera()
    if 'user' not in session: return redirect('/')
    current_user_email = session.get('user', user_email)
    if not current_user_email: return redirect('/')
    user_key = current_user_email.replace(".", "_")
    try: history_data = db.child("users").child(user_key).child("history").get().val()
    except Exception as e: print(f"Firebase'den ilerleme verisi alınırken hata: {e}"); history_data = None
    labels, values = analyze_progress_chart_data(history_data)
    return render_template("progress.html", labels=labels, values=values, brand="MotionMind")

@app.route('/logout')
def logout():
    global user_email, movement, duration_sec, count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, start_time, last_instruction_time, is_paused, elapsed_before_pause, last_congrats_time, congrats_given_for_hold
    session.pop('user', None); session.pop('last_movement', None); session.pop('last_duration', None)
    user_email = ""; movement = ""; duration_sec = 0; count = 0; stage = None; uyari_verildi = False; dogru_yapiliyor = False; kayit_edildi = False; start_time = 0; last_instruction_time = 0; is_paused = False; elapsed_before_pause = 0; last_congrats_time = 0; congrats_given_for_hold = False
    if hasattr(generate_frames, 'last_count_for_visual'): delattr(generate_frames, 'last_count_for_visual')
    stop_camera()
    return redirect('/')

@app.route('/stop_and_select', methods=['POST'])
def stop_and_select():
    global kayit_edildi
    kayit_edildi = True
    stop_camera()
    return redirect('/select')

# --- Chatbot Rotası ---
@app.route('/get_bot_response', methods=['POST'])
def get_bot_response():
    global IS_GEMINI_CONFIGURED
    user_message = request.json.get('message', '').lower()
    bot_reply = "Üzgünüm, şu anda size yardımcı olamıyorum. Lütfen daha sonra tekrar deneyin."
    exercise_to_select = None

    if not IS_GEMINI_CONFIGURED:
         return jsonify({'response': "Google Gemini API anahtarı yapılandırılmamış veya geçersiz. Lütfen main.py dosyasını kontrol edin.", 'select_exercise': None})

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = (
            "Sen MotionMind Asistanısın, yardımsever ve teşvik edici bir fitness koçusun. "
            "Şu egzersizleri biliyorsun: Squat, Push-up (Şınav), Plank, Lunge, Jumping Jack, "
            "Sit-up (Mekik), Mountain Climber, Side Plank, Shoulder Press, High Knees, "
            "Dumbbell Curl, Lateral Raise, Biceps Hammer Curl. "
            "Kas gruplarına (omuz, bacak, göğüs, karın, kol, kardiyo) göre egzersiz önerebilirsin. "
            "Kullanıcıları şu sayfalara yönlendirebilirsin: /select (Ana Sayfa/Egzersiz Seçimi), "
            "/history (Geçmiş), /progress (Gelişim). "
            "Bir egzersiz sorulursa, kısaca açıkla ve /select sayfasından başlatabileceğini belirt. "
            "Bir sayfa sorulursa, HTML linki (<a href='...'></a>) ile yanıt ver. "
            "Yardım istenirse, yeteneklerini listele. "
            "Yanıtlarını TÜRKÇE, kısa, net ve motive edici tut.\n\n"
            f"Kullanıcı: {user_message}\n"
            "Asistan:"
        )
        response = model.generate_content(prompt)
        bot_reply = response.text.strip()
        lower_reply = bot_reply.lower()
        for key in module_map.keys():
            if key.replace("_", " ").lower() in lower_reply and "/select" in lower_reply:
                exercise_to_select = key
                break
    except Exception as e:
        print(f"Google Gemini API Hatası: {e}")
        error_str = str(e)
        if "API_KEY_INVALID" in error_str or "API key not valid" in error_str:
             bot_reply = "Google Gemini API anahtarınız geçersiz görünüyor. Lütfen doğru anahtarı girdiğinizden ve Gemini API için olduğundan emin olun."
        elif "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
             bot_reply = "Google Gemini API kullanım limitinize ulaştınız. Lütfen daha sonra tekrar deneyin veya Google AI Studio/Cloud Console'dan limitlerinizi kontrol edin."
        else:
             bot_reply = f"Google Gemini API'sinde bir sorun oluştu. Lütfen daha sonra tekrar deneyin."

    return jsonify({'response': bot_reply, 'select_exercise': exercise_to_select})



if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
