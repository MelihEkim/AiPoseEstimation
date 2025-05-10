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

        # İskelet çizimi
        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )

        # Sol kalça ve diz (öne gelme mesafesi kontrolü)
        hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
               landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]

        distance = abs(knee[1] - hip[1])  # ne kadar yukarı gelmiş

        # Tekrar sayımı
        if distance < 0.1:
            if stage != "up":
                stage = "up"
                count += 1
                dogru = True
        else:
            stage = "down"
            uyari = True

        # Sayıya debug yazısı
        cv2.putText(frame, f"Mesafe: {distance:.2f}", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 255, 200), 2)

    return frame, count, stage, uyari, dogru
