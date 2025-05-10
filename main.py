from flask import Flask, render_template, request, redirect, session, url_for, Response
from flask import jsonify
import pyrebase
from datetime import datetime
import os
import json
import cv2
import mediapipe as mp
import threading
import time
from exercises import squat, pushup, plank, lunge, jumping_jack, situp, mountain_climber, side_plank, shoulder_press, high_knees, dumbbell_curl
from utils import draw_timer, draw_success
from audio_utils import play_combined_instruction, stop_audio
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

class VideoStream:
    def __init__(self, src=0, width=640, height=480):
        global cap
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap = self.cap
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
    global count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, start_time, last_instruction_time, is_paused, elapsed_before_pause, vs

    stop_camera()
    vs = VideoStream()
    time.sleep(1)
    last_frame = None

    if not vs.ret:
        return

    last_count = 0

    while True:
        success, frame = vs.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)

        if is_paused:
            if last_frame is not None:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + last_frame + b'\r\n')
            continue

        elapsed_time = int(time.time() - start_time)
        elapsed_before_pause = elapsed_time
        remaining_time = max(0, duration_sec - elapsed_time)
        minutes = remaining_time // 60
        seconds = remaining_time % 60

        frame, count, stage, uyari, dogru = module_map[movement].detect(frame, count, stage, pose)

        if movement not in ["plank", "side_plank"]:
            formatted_name = format_movement_name(movement)
            cv2.putText(frame, f'{formatted_name} Tekrar: {count}', (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        draw_timer(frame, minutes, seconds)

        now = time.time()
        if uyari:
            if not uyari_verildi or now - last_instruction_time > 9:
                uyari_verildi = True
                last_instruction_time = now
                play_combined_instruction(movement)
        else:
            uyari_verildi = False
            stop_audio()

        if dogru:
            uyari_verildi = False
            stop_audio()

        if movement in ["plank", "side_plank"]:
            if dogru:
                draw_success(frame)
        else:
            if count > last_count:
                draw_success(frame)
                last_count = count

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
            stop_camera()
            break

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        last_frame = frame
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    if vs is not None:
        vs.stop()

@app.route('/')
def home():
    stop_camera()
    return render_template("login.html", brand="MotionMind")

@app.route('/register', methods=['GET', 'POST'])
def register():
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
    email = request.form['email']
    password = request.form['password']
    try:
        auth.sign_in_with_email_and_password(email, password)
        session['user'] = email
        user_email = email
        return redirect('/select')
    except Exception as e:
        return f"Giriş başarısız: {str(e)}"

@app.route('/select')
def select():
    if 'user' not in session:
        return redirect('/')
    return render_template("select.html", brand="MotionMind")

@app.route('/start', methods=['POST'])
def start():
    stop_camera()
    global movement, duration_sec, start_time, count, stage, uyari_verildi, dogru_yapiliyor, kayit_edildi, last_instruction_time, is_paused
    if 'user' not in session:
        return redirect('/')

    movement = request.form.get('movement') or session.get('last_movement')
    movement = movement.lower().replace(" ", "_")
    duration = int(request.form.get('duration') or session.get('last_duration'))
    duration_sec = duration * 60
    start_time = time.time()
    count = 0
    stage = None
    uyari_verildi = False
    dogru_yapiliyor = False
    kayit_edildi = False
    last_instruction_time = 0
    is_paused = False

    session['last_movement'] = movement
    session['last_duration'] = duration

    return render_template("session_started.html", movement=format_movement_name(movement), duration=duration, brand="MotionMind")

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/pause', methods=['POST'])
def pause():
    global is_paused, elapsed_before_pause
    is_paused = True
    elapsed_before_pause = time.time() - start_time
    return '', 204

@app.route('/resume', methods=['POST'])
def resume():
    global is_paused, start_time
    is_paused = False
    start_time = time.time() - elapsed_before_pause
    return '', 204

@app.route('/completed')
def completed():
    if 'user' not in session:
        return redirect('/')

    user_key = session['user'].replace(".", "_")
    yorum = analyze_progress(db, user_key)

    return render_template("completed.html",
    movement=format_movement_name(movement),
    count=count,
    duration=duration_sec // 60,
    hedef=count + 2,
    yorum=yorum,
    brand="MotionMind")

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')
    return render_template("history.html", history=db.child("users").child(session['user'].replace(".", "_")).child("history").get().val(), brand="MotionMind")

@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect('/')
    history = db.child("users").child(session['user'].replace(".", "_")).child("history").get().val()
    labels, values = analyze_progress_chart_data(history)
    return render_template("progress.html", labels=labels, values=values, brand="MotionMind")

@app.route('/logout')
def logout():
    session.pop('user', None)
    stop_camera()
    return redirect('/')

@app.route('/stop_and_select', methods=['POST'])
def stop_and_select():
    stop_camera()
    return redirect('/select')


# Chatbot Kısmı 

chat_rules = {
    # --- Karşılama ve Yardım ---
    "merhaba": "Merhaba! Ben MotionMind Asistanı. Antrenmanlarınız veya site kullanımı hakkında yardımcı olabilirim.",
    "selam": "Selam! Ben MotionMind Asistanı. Nasıl yardımcı olabilirim?",
    "nasılsın": "Harikayım! Antrenmana hazır mısınız?",
    "yardım": "Elbette! Bana şunları sorabilirsiniz: \n<ul><li>Çalıştırmak istediğiniz kas grubu (örn: 'omuz', 'bacak çalışmak istiyorum', 'pazu')</li><li>Egzersiz bilgisi (örn: 'squat nedir?', 'dumbbell curl')</li><li>Sayfaya gitme (örn: 'geçmiş sayfasına git', 'ilerlememi göster')</li></ul>",
    "teşekkürler": "Rica ederim! Başka sorunuz var mı?",
    "teşekkür ederim": "Rica ederim! Yardımcı olabildiğime sevindim.",

    # --- Yönlendirme Bilgilendirme ---
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

    # --- Egzersiz Önerileri (Kas Grubuna Göre) ---
    "omuz": "Omuz kaslarınız için 'Shoulder Press' egzersizini öneririm. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "bacak": "Bacak ve kalça kasları için 'Squat' veya 'Lunge' harika seçeneklerdir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "kalça": "Kalça ve bacakları şekillendirmek için 'Squat' ve 'Lunge' yapabilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "popo": "Kalça (popo) ve bacaklar için 'Squat' ve 'Lunge' etkilidir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.", 
    "göğüs": "Göğüs, omuz ve arka kol için 'Push-up' (Şınav) idealdir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "gogus": "Göğüs, omuz ve arka kol için 'Push-up' (Şınav) idealdir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "karın": "Karın kaslarınızı güçlendirmek için 'Sit-up', 'Plank' veya 'Side Plank' egzersizlerini yapabilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "gobek": "Göbek eritmek ve karın kası için 'Sit-up', 'Plank', 'Mountain Climber' veya 'High Knees' deneyebilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "sırt": "'Plank' ve 'Side Plank' sırtınızı da destekler, ancak doğrudan sırt egzersizimiz şu an bulunmuyor.",
    "kol": "'Push-up' arka kolu (triceps), 'Shoulder Press' omuzları çalıştırır. Ön kol (biceps/pazu) için ise artık 'Dumbbell Curl' egzersizini de yapabilirsiniz! Hepsini <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "biceps": "Biceps (pazu) kaslarınızı çalıştırmak için 'Dumbbell Curl' egzersizini deneyebilirsiniz. <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "pazu": "Pazu (biceps) kaslarınızı çalıştırmak için 'Dumbbell Curl' egzersizini deneyebilirsiniz. <a href='/select'>Seçim ekranından</a> başlatabilirsiniz.",
    "kardiyo": "Kalp atışınızı hızlandırmak ve kalori yakmak için 'Jumping Jack', 'High Knees' veya 'Mountain Climber' yapabilirsiniz. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "ısınma": "Isınma için 'Jumping Jack' veya 'High Knees' gibi hafif kardiyo hareketleri iyi olabilir. <a href='/select'>Seçim ekranından</a> deneyebilirsiniz.",
    "tüm vücut": "Tüm vücudu kapsayan antrenmanlar için 'Jumping Jack', 'Mountain Climber', 'Plank' ve 'Push-up' gibi hareketleri birleştirebilirsiniz.",

    # --- Egzersiz Bilgileri ---
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
   
}

@app.route('/get_bot_response', methods=['POST'])
def get_bot_response():
    user_message = request.json.get('message', '').lower()

    
    user_message = ''.join(c for c in user_message if c.isalnum() or c.isspace() or c in ['ş','ı','ö','ç','ü','ğ'])
    user_message = ' '.join(user_message.split())

    bot_reply = "Üzgünüm, bu isteğinizi şimdilik anlayamadım. 'Yardım' yazarak neler sorabileceğinizi öğrenebilirsiniz."
    matched = False

    
    for keyword, response in chat_rules.items():
        if keyword in user_message:
            bot_reply = response
            matched = True
            break

    if not matched:
       
        available_exercises = ["squat", "pushup", "şınav", "plank", "lunge", "jumping jack", "situp", "mekik", "mountain climber", "side plank", "shoulder press", "high knees", "dumbbell curl"]
       
        for exercise in available_exercises:
            
            if exercise in user_message:
           
                if f"{exercise} nedir" in chat_rules:
                    bot_reply = chat_rules[f"{exercise} nedir"] + f" <a href='/select'>Seçim ekranından</a> başlatabilirsiniz."
                elif exercise in chat_rules:
                     bot_reply = chat_rules[exercise] 
                else:
                    bot_reply = f"'{exercise.capitalize()}' egzersizini <a href='/select'>Seçim ekranından</a> başlatabilirsiniz."
                matched = True 

    return jsonify({'response': bot_reply})
# Chatbot Bitiş 



if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)




