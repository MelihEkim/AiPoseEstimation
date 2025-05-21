import cv2
import numpy as np
import mediapipe as mp
from utils import calculate_angle

def detect(frame, count, stage, pose):
    uyari = False
    dogru = False

    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image)

    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark

        # POSE çizimi
        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )

        # Sol kol (omuz-dirsek-bilek)
        shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                 landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                 landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

        # Açı hesapla
        angle = calculate_angle(shoulder, elbow, wrist)

        # Açı yazdır
        cv2.putText(frame, str(int(angle)),
                    tuple(np.multiply(elbow, [frame.shape[1], frame.shape[0]]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Tekrar sayımı
        if angle > 160:
            stage = "up"
        elif angle < 90 and stage == "up":
            stage = "down"
            count += 1

        # Doğruluk kontrolü
        if 80 <= angle <= 100:
            dogru = True
        else:
            uyari = True

    return frame, count, stage, uyari, dogru
