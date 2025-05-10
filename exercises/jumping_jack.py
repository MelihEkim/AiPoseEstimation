import cv2
import numpy as np
import mediapipe as mp

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

        # Eller ve ayak bilekleri
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x

        # Eller yukarıda ve ayaklar açık mı?
        if left_wrist < 0.4 and right_wrist < 0.4 and abs(left_ankle - right_ankle) > 0.5:
            if stage != "open":
                stage = "open"
                count += 1
                dogru = True
        else:
            stage = "closed"
            uyari = True

    return frame, count, stage, uyari, dogru
