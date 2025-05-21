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

        # İskelet çizimi (tüm vücut)
        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )

        # SOL kol: dirsek - omuz - kalça
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]

        left_angle = calculate_angle(left_elbow, left_shoulder, left_hip)

        # SAĞ kol: dirsek - omuz - kalça
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                          landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]

        right_angle = calculate_angle(right_elbow, right_shoulder, right_hip)

        # Açıları yazdır
        cv2.putText(frame, str(int(left_angle)),
                    tuple(np.multiply(left_shoulder, [frame.shape[1], frame.shape[0]]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        
        cv2.putText(frame, str(int(right_angle)),
                    tuple(np.multiply(right_shoulder, [frame.shape[1], frame.shape[0]]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        # Tekrar mantığı (her iki kol için geçerli)
        if left_angle > 160 and right_angle > 160:
            stage = "down"
        elif (left_angle < 90 or right_angle < 90) and stage == "down":
            stage = "up"
            count += 1

        # Doğruluk kontrolü
        if (90 <= left_angle <= 160) or (90 <= right_angle <= 160):
            dogru = True
        else:
            uyari = True

    return frame, count, stage, uyari, dogru
