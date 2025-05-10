from datetime import datetime, timedelta

def analyze_progress(db, user_key):
    history_data = db.child("users").child(user_key).child("history").get().val()
    
    if not history_data:
        return "Henüz hiç antrenman kaydı bulunamadı. Hadi başlayalım!"
    
    bu_hafta = 0
    gecen_hafta = 0
    
    simdi = datetime.now()
    bir_hafta_once = simdi - timedelta(days=7)
    iki_hafta_once = simdi - timedelta(days=14)

    for kayit in history_data.values():
        try:
            tarih = datetime.strptime(kayit["tarih"], "%Y-%m-%d %H:%M:%S")
            tekrar = int(kayit.get("tekrar", 0))
        except Exception as e:
            print(f"Kayıt işleme hatası: {e}")
            continue

        if bir_hafta_once <= tarih <= simdi:
            bu_hafta += tekrar
        elif iki_hafta_once <= tarih < bir_hafta_once:
            gecen_hafta += tekrar

    if gecen_hafta == 0:
        if bu_hafta == 0:
            yorum = "Henüz hiç antrenman kaydı bulunamadı. Hadi başlayalım!"
        else:
            yorum = f"Bu hafta {bu_hafta} tekrar yaptınız. Harika başlangıç!"
    else:
        oran = ((bu_hafta - gecen_hafta) / gecen_hafta) * 100
        if oran > 0:
            yorum = f"Bu hafta performansınız geçen haftaya göre % {int(oran)} arttı. Harika gidiyorsunuz!"
        elif oran < 0:
            yorum = f"Bu hafta performansınız % {abs(int(oran))} azaldı. Daha iyisini yapabilirsiniz!"
        else:
            yorum = "Bu hafta performansınız sabit kaldı. Dengeli çalışmaya devam!"

    return yorum

def analyze_progress_chart_data(history_data):
    if not history_data:
        return [], []

    from collections import defaultdict
    tarih_dict = defaultdict(int)

    for kayit in history_data.values():
        try:
            tarih_str = kayit.get("tarih", "")
            tekrar = int(kayit.get("tekrar", 0))
            tarih_obj = datetime.strptime(tarih_str, "%Y-%m-%d %H:%M:%S")
            tarih_key = tarih_obj.strftime("%d.%m.%Y")
            tarih_dict[tarih_key] += tekrar
        except Exception as e:
            print(f"Tarih verisi işlenemedi: {e}")
            continue

    labels = sorted(tarih_dict.keys())
    values = [tarih_dict[t] for t in labels]

    return labels, values

def get_firebase():
    import pyrebase
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
    db = firebase.database()
    return db
