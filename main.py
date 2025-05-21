from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify
import pyrebase
from datetime import datetime
import cv2
import mediapipe as mp
import threading
import time
from exercises import squat, pushup, plank, lunge, jumping_jack, situp, mountain_climber, side_plank, shoulder_press, high_knees, dumbbell_curl, lateral_raise, biceps_hammer_curl
from utils import draw_timer, draw_success
from audio_utils import speak_exercise_explanation, speak_congratulations, stop_audio
from analysis_utils import analyze_progress_chart_data, get_firebase, analyze_progress

def format_movement_name(name):
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
            if "EMAIL_EXISTS" in error_message:
                return "Bu e-posta zaten kayıtlı."
            elif "WEAK_PASSWORD" in error_message:
                return "Şifre çok zayıf. En az 6 karakter olmalı."
            elif "INVALID_EMAIL" in error_message:
                return "Geçerli bir e-posta adresi girin."
            else:
                return f"Kayıt başarısız: {error_message}"
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
    if 'user' not in session:
        return redirect('/')
    global user_email
    if not user_email and 'user' in session:
         user_email = session['user']
    return render_template("select.html", brand="MotionMind")

@app.route('/start', methods=['POST'])
def start():
    stop_camera()
    global movement, duration_sec, start_time, count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, last_instruction_time, is_paused, elapsed_before_pause, last_congrats_time, congrats_given_for_hold, user_email
    if 'user' not in session:
        return redirect('/')
    if 'user' in session:
        user_email = session['user']
    else:
        return redirect('/')
    form_movement = request.form.get('movement')
    if form_movement:
        movement = form_movement.lower().replace(" ", "_")
    elif session.get('last_movement'):
        movement = session['last_movement']
    else:
        return redirect('/select')
    form_duration = request.form.get('duration')
    if form_duration:
        duration = int(form_duration)
    elif session.get('last_duration'):
        duration = int(session.get('last_duration'))
    else:
        return redirect('/select')
    duration_sec = duration * 60
    start_time = time.time()
    count = 0
    stage = None
    uyari_verildi = False
    dogru_yapiliyor = False
    kayit_edildi = False
    last_instruction_time = 0
    is_paused = False
    elapsed_before_pause = 0
    last_congrats_time = 0
    congrats_given_for_hold = False
    if hasattr(generate_frames, 'last_count_for_visual'):
        delattr(generate_frames, 'last_count_for_visual')
    else:
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
    if 'user' not in session:
        return redirect('/')
    current_user_email = session.get('user', user_email)
    if not current_user_email:
         return redirect('/')
    user_key = current_user_email.replace(".", "_")
    yorum = analyze_progress(db, user_key)
    completed_movement_name = format_movement_name(session.get('last_movement', movement))
    completed_rep_count = count
    completed_duration_min = session.get('last_duration', duration_sec // 60)
    return render_template("completed.html",
                           movement=completed_movement_name,
                           count=completed_rep_count,
                           duration=completed_duration_min,
                           hedef=completed_rep_count + 2,
                           yorum=yorum,
                           brand="MotionMind")

@app.route('/history')
def history_route():
    stop_camera()
    if 'user' not in session:
        return redirect('/')
    current_user_email = session.get('user', user_email)
    if not current_user_email:
         return redirect('/')
    user_key = current_user_email.replace(".", "_")
    try:
        history_data = db.child("users").child(user_key).child("history").get().val()
    except Exception as e:
        print(f"Firebase'den geçmiş verisi alınırken hata: {e}")
        history_data = None
    return render_template("history.html", history=history_data, brand="MotionMind")

@app.route('/progress')
def progress():
    stop_camera()
    if 'user' not in session:
        return redirect('/')
    current_user_email = session.get('user', user_email)
    if not current_user_email:
         return redirect('/')
    user_key = current_user_email.replace(".", "_")
    try:
        history_data = db.child("users").child(user_key).child("history").get().val()
    except Exception as e:
        print(f"Firebase'den ilerleme verisi alınırken hata: {e}")
        history_data = None
    labels, values = analyze_progress_chart_data(history_data)
    return render_template("progress.html", labels=labels, values=values, brand="MotionMind")

@app.route('/logout')
def logout():
    global user_email, movement, duration_sec, count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, start_time, last_instruction_time, is_paused, elapsed_before_pause, last_congrats_time, congrats_given_for_hold
    session.pop('user', None)
    session.pop('last_movement', None)
    session.pop('last_duration', None)
    user_email = ""; movement = ""; duration_sec = 0; count = 0; stage = None; uyari_verildi = False; dogru_yapiliyor = False; kayit_edildi = False; start_time = 0; last_instruction_time = 0; is_paused = False; elapsed_before_pause = 0; last_congrats_time = 0; congrats_given_for_hold = False
    if hasattr(generate_frames, 'last_count_for_visual'):
        delattr(generate_frames, 'last_count_for_visual')
    stop_camera()
    return redirect('/')

@app.route('/stop_and_select', methods=['POST'])
def stop_and_select():
    global kayit_edildi
    kayit_edildi = True
    stop_camera()
    return redirect('/select')

chat_rules = {
    "merhaba": "Merhaba! Ben MotionMind Asistanı. Antrenmanlarınız veya site kullanımı hakkında yardımcı olabilirim.",
    "selam": "Selam! Ben MotionMind Asistanı. Nasıl yardımcı olabilirim?",
    "nasılsın": "Harikayım! Antrenmana hazır mısınız?",
    "yardım": "Elbette! Bana şunları sorabilirsiniz: \n<ul><li>Çalıştırmak istediğiniz kas grubu (örn: 'omuz', 'bacak çalışmak istiyorum', 'pazu')</li><li>Egzersiz bilgisi (örn: 'squat nedir?', 'dumbbell curl', 'lateral raise nedir')</li><li>Sayfaya gitme (örn: 'geçmiş sayfasına git', 'ilerlememi göster')</li></ul>",
    "teşekkürler": "Rica ederim! Başka sorunuz var mı?",
    "teşekkür ederim": "Rica ederim! Yardımcı olabildiğime sevindim.",
    "geçmiş": "Antrenman geçmişinizi <a href='/history' target='_blank'>Geçmiş Kayıtları</a> sayfasında görebilirsiniz.",
    "kayıtlar": "Antrenman kayıtlarınız için <a href='/history' target='_blank'>Geçmiş Kayıtları</a> sayfasına bakabilirsiniz.",
    "ilerleme": "Haftalık ilerlemenizi <a href='/progress' target='_blank'>Gelişim Grafiği</a> sayfasında takip edebilirsiniz.",
    "grafik": "Gelişim grafiğiniz <a href='/progress' target='_blank'>Gelişim Grafiği</a> sayfasındadır.",
    "anasayfa": "Hareket ve süre seçimi için <a href='/select' target='_blank'>Ana Sayfa</a>'ya gidebilirsiniz.",
    "seçim": "Hareket ve süre seçimi için <a href='/select' target='_blank'>Ana Sayfa</a>'ya gidebilirsiniz.",
    "başla": "Yeni bir antrenmana başlamak için <a href='/select' target='_blank'>Ana Sayfa</a>'dan seçim yapmalısınız.",
    "çıkış": "Hesabınızdan güvenle çıkmak için <a href='/logout'>Çıkış Yap</a> bağlantısını kullanın.",
    "kapat": "Oturumu kapatmak için <a href='/logout'>Çıkış Yap</a> bağlantısını kullanın.",
    "giriş": "Giriş yapmak için <a href='/'>Giriş Sayfası</a>'na gidin.",
    "login": "Giriş yapmak için <a href='/'>Giriş Sayfası</a>'na gidin.",
    "kayıt ol": "Yeni bir hesap oluşturmak için <a href='/register'>Kayıt Ol</a> sayfasına gidin.",
    "üye ol": "Yeni bir hesap oluşturmak için <a href='/register'>Kayıt Ol</a> sayfasına gidin.",
    "omuz": "Omuz kaslarınız için 'Shoulder Press' veya 'Lateral Raise' egzersizlerini öneririm. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "bacak": "Bacak ve kalça kasları için 'Squat' veya 'Lunge' harika seçeneklerdir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "kalça": "Kalça ve bacakları şekillendirmek için 'Squat' ve 'Lunge' yapabilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "popo": "Kalça (popo) ve bacaklar için 'Squat' ve 'Lunge' etkilidir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "göğüs": "Göğüs, omuz ve arka kol için 'Push-up' (Şınav) idealdir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "gogus": "Göğüs, omuz ve arka kol için 'Push-up' (Şınav) idealdir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "karın": "Karın kaslarınızı güçlendirmek için 'Sit-up', 'Plank' veya 'Side Plank' egzersizlerini yapabilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "gobek": "Göbek eritmek ve karın kası için 'Sit-up', 'Plank', 'Mountain Climber' veya 'High Knees' deneyebilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "sırt": "'Plank' ve 'Side Plank' sırtınızı da destekler, ancak doğrudan sırt egzersizimiz şu an bulunmuyor.",
    "kol": "'Push-up' arka kolu (triceps), 'Shoulder Press' omuzları çalıştırır. Ön kol (biceps/pazu) için 'Dumbbell Curl' veya 'Biceps Hammer Curl' egzersizlerini yapabilirsiniz! Hepsini <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "biceps": "Biceps (pazu) kaslarınızı çalıştırmak için 'Dumbbell Curl' veya 'Biceps Hammer Curl' egzersizlerini deneyebilirsiniz. <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "pazu": "Pazu (biceps) kaslarınızı çalıştırmak için 'Dumbbell Curl' veya 'Biceps Hammer Curl' egzersizlerini deneyebilirsiniz. <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "kardiyo": "Kalp atışınızı hızlandırmak ve kalori yakmak için 'Jumping Jack', 'High Knees' veya 'Mountain Climber' yapabilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "ısınma": "Isınma için 'Jumping Jack' veya 'High Knees' gibi hafif kardiyo hareketleri iyi olabilir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "tüm vücut": "Tüm vücudu kapsayan antrenmanlar için 'Jumping Jack', 'Mountain Climber', 'Plank' ve 'Push-up' gibi hareketleri birleştirebilirsiniz.",
    "squat nedir": "'Squat', özellikle bacak ve kalça kaslarını çalıştıran temel bir çömelme hareketidir.",
    "pushup nedir": "'Push-up' (Şınav), vücut ağırlığı ile yapılan, göğüs, omuz ve arka kolu çalıştıran bir itme hareketidir.",
    "şınav nedir": "'Push-up' (Şınav), vücut ağırlığı ile yapılan, göğüs, omuz ve arka kolu çalıştıran bir itme hareketidir.",
    "plank nedir": "'Plank', özellikle karın ve sırt kaslarını güçlendiren, sabit duruş (izometrik) egzersizidir.",
    "lunge nedir": "'Lunge', tek bacakla öne adım atılarak yapılan, bacak ve kalça kaslarını hedefleyen bir egzersizdir.",
    "jumping jack nedir": "'Jumping Jack', kollar ve bacakların senkronize olarak açılıp kapandığı bir kardiyo egzersizidir.",
    "situp nedir": "'Sit-up', sırtüstü pozisyondan üst gövdenin kaldırılarak yapıldığı bir karın kası egzersizidir.",
    "mekik nedir": "'Sit-up' (Mekik), sırtüstü pozisyondan üst gövdenin kaldırılarak yapıldığı bir karın kası egzersizidir.",
    "mountain climber nedir": "'Mountain Climber', plank pozisyonunda dizlerin sırayla karna çekildiği, kardiyo ve karın egzersizidir.",
    "side plank nedir": "'Side Plank', vücudun yan duruşta sabit kaldığı, özellikle yan karın kaslarını çalıştıran bir egzersizdir.",
    "shoulder press nedir": "'Shoulder Press', omuz kaslarını hedef alan bir egzersizdir. <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "high knees nedir": "'High Knees', yerinde koşar gibi dizlerin yükseğe çekildiği bir kardiyo ve alt karın egzersizidir.",
    "dumbbell curl": "Dumbbell Curl, pazu (biceps) kaslarınızı çalıştırmak için harika bir egzersizdir. <a href='/select'>Seçim ekranından</a> başlatıp takibini yapabilirsiniz.",
    "curl nedir": "'Dumbbell Curl', pazu (biceps) kaslarını hedef alan temel bir ağırlık egzersizidir. <a href='/select'>Seçim ekranından</a> başlatıp formunuzu takip edebilirsiniz.",
    "lateral raise nedir": "'Lateral Raise', özellikle omuzların yan kısımlarını (lateral deltoid) çalıştıran bir izolasyon egzersizidir. Kollar yana doğru kaldırılır.",
    "yan omuz açış": "'Lateral Raise', özellikle omuzların yan kısımlarını (lateral deltoid) çalıştıran bir izolasyon egzersizidir. Kollar yana doğru kaldırılır.",
    "hammer curl nedir": "'Biceps Hammer Curl', biceps brachii, brachialis ve brachioradialis kaslarını hedefleyen, avuç içlerinin birbirine baktığı nötr bir tutuşla yapılan bir curl varyasyonudur.",
    "biceps hammer curl": "Biceps Hammer Curl egzersizini <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "lateral raise": "Lateral Raise egzersizini <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
}

@app.route('/get_bot_response', methods=['POST'])
def get_bot_response():
    user_message = request.json.get('message', '').lower()
    user_message = ''.join(c for c in user_message if c.isalnum() or c.isspace() or c in ['ş','ı','ö','ç','ü','ğ','Ş','İ','Ö','Ç','Ü','Ğ'])
    user_message = ' '.join(user_message.split())
    bot_reply = "Üzgünüm, bu isteğinizi şimdilik anlayamadım. 'Yardım' yazarak neler sorabileceğinizi öğrenebilirsiniz."
    matched = False; exercise_to_select = None
    for keyword, response in sorted(chat_rules.items(), key=lambda item: len(item[0]), reverse=True):
        if keyword in user_message:
            bot_reply = response; matched = True
            if keyword in ["omuz", "shoulder press nedir"]: exercise_to_select = "shoulder_press"
            elif keyword in ["yan omuz açış", "lateral raise nedir", "lateral raise"]: exercise_to_select = "lateral_raise"
            elif keyword in ["bacak", "kalça", "popo", "squat nedir"]: exercise_to_select = "squat"
            elif keyword in ["lunge nedir"]: exercise_to_select = "lunge"
            elif keyword in ["kol", "biceps", "pazu", "dumbbell curl", "curl nedir"]: exercise_to_select = "dumbbell_curl"
            elif keyword in ["hammer curl nedir", "biceps hammer curl"]: exercise_to_select = "biceps_hammer_curl"
            break
    if not matched:
        available_exercises_map = {
            "squat": "squat", "pushup": "pushup", "şınav": "pushup", "plank": "plank",
            "lunge": "lunge", "jumping jack": "jumping_jack", "situp": "situp", "mekik": "situp",
            "mountain climber": "mountain_climber", "side plank": "side_plank",
            "shoulder press": "shoulder_press", "high knees": "high_knees",
            "dumbbell curl": "dumbbell_curl", "lateral raise": "lateral_raise", "biceps hammer curl": "biceps_hammer_curl"
        }
        for display_name, internal_name in available_exercises_map.items():
            if display_name in user_message:
                exercise_to_select = internal_name; specific_keyword_nedir = f"{display_name} nedir"
                if specific_keyword_nedir in chat_rules: bot_reply = chat_rules[specific_keyword_nedir]
                elif display_name in chat_rules: bot_reply = chat_rules[display_name]
                else: bot_reply = f"'{display_name.title()}' egzersizini <a href='/select'>Seçim ekranından</a> başlatabilirsiniz."
                matched = True; break
    return jsonify({'response': bot_reply, 'select_exercise': exercise_to_select})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)