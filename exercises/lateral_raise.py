import cv2
import numpy as np
import mediapipe as mp
from utils import calculate_angle

def detect(frame, count, stage, pose):
    uyari = False
    dogru = False

    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = pose.process(image)
    image.flags.writeable = True

    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark

        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
            mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )

        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        
        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                          landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]

        left_arm_angle = calculate_angle(left_hip, left_shoulder, left_elbow)
        right_arm_angle = calculate_angle(right_hip, right_shoulder, right_elbow)

        cv2.putText(frame, f"L: {int(left_arm_angle)}", 
                    tuple(np.multiply(left_shoulder, [frame.shape[1], frame.shape[0] - 20]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, f"R: {int(right_arm_angle)}", 
                    tuple(np.multiply(right_shoulder, [frame.shape[1], frame.shape[0] - 20]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        angle_threshold_down = 35
        angle_threshold_up = 70 
        correct_angle_range_min = 65
        correct_angle_range_max = 100

        if left_arm_angle < angle_threshold_down and right_arm_angle < angle_threshold_down:
            stage = "down"
        elif left_arm_angle > angle_threshold_up and right_arm_angle > angle_threshold_up and stage == "down":
            stage = "up"
            count += 1
            dogru = True 
        
        if (correct_angle_range_min <= left_arm_angle <= correct_angle_range_max) and \
           (correct_angle_range_min <= right_arm_angle <= correct_angle_range_max):
            dogru = True
        elif stage == "up" and (left_arm_angle > correct_angle_range_min and right_arm_angle > correct_angle_range_min):
             dogru = True
        else:
            if not (stage == "up" and count > 0 and \
                    (left_arm_angle > angle_threshold_up and right_arm_angle > angle_threshold_up) ):
                 if not ((correct_angle_range_min <= left_arm_angle <= correct_angle_range_max) and \
                         (correct_angle_range_min <= right_arm_angle <= correct_angle_range_max)):
                    dogru = False
    return frame, count, stage, uyari, dogru