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

        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
            mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
        )

        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                          landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

        right_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
        left_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)

        cv2.putText(frame, f"R:{int(right_angle)}",
                    tuple(np.multiply(right_elbow, [frame.shape[1], frame.shape[0]]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.putText(frame, f"L:{int(left_angle)}",
                    tuple(np.multiply(left_elbow, [frame.shape[1], frame.shape[0]]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Doğru form kontrolü
        correct_form = (right_angle > 160 and left_angle > 160) or (right_angle < 50 and left_angle < 50)

        # Doğru formdaysa dogru = True
        if correct_form:
            dogru = True
        else:
            uyari = True

        # Stage geçiş ve sayım sadece doğru formda çalışacak
        if dogru:
            if right_angle > 160 and left_angle > 160:
                stage = "down"
            if right_angle < 50 and left_angle < 50 and stage == "down":
                stage = "up"
                count += 1  # SAYIM SADECE DOĞRU FORMDA
        else:
            # Doğru form değilse stage güncellenmesin, count artmasın
            pass

    return frame, count, stage, uyari, dogru

