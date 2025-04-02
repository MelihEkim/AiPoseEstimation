def analyze_squat(knee_angle):
    if knee_angle < 70:
        return ("Squat çok alçak! Dizlerinizi 90 derece açıda tutun.", True)
    elif knee_angle > 150:
        return ("Squat çok yüksek! Daha fazla eğilmelisiniz.", True)
    return ("Squat Doğru", False)

def analyze_pushup(elbow_angle):
    if elbow_angle < 50:
        return ("Push-up çok düşük! Dirseklerinizi çok fazla kırıyorsunuz.", True)
    elif elbow_angle > 160:
        return ("Push-up çok yüksek! Daha fazla eğilmelisiniz.", True)
    return ("Push-up Doğru", False)

def analyze_plank(hip_angle):
    if hip_angle < 160:
        return ("Plank hatalı! Kalçanızı yukarı kaldırın ve sırtınızı düz tutun.", True)
    return ("Plank Doğru", False)

def analyze_lunge(knee_angle):
    if knee_angle < 80:
        return ("Lunge çok alçak! Dizlerinizi fazla bükmeyin.", True)
    elif knee_angle > 140:
        return ("Lunge çok yüksek! Daha fazla dizlerinizi bükmelisiniz.", True)
    return ("Lunge Doğru", False)

def analyze_biceps_curl(elbow_angle):
    if elbow_angle < 30:
        return ("Biseps Curl çok kısa! Ağırlığı tam kaldırmalısınız.", True)
    elif elbow_angle > 160:
        return ("Biceps Curl çok açık! Kollarınızı daha fazla kapatmalısınız.", True)
    return ("Biseps Curl Doğru", False)
