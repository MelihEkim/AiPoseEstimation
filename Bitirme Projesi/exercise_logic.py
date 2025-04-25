import json
import numpy as np
from pose_utils import calculate_angle
import cv2
from data_logger import log_session

with open("exercise_config.json", "r") as f:
    CONFIG = json.load(f)

class ExerciseSession:
    def __init__(self, exercise_name):
        self.name = exercise_name
        self.config = CONFIG[self.name]
        self.counter = 0
        self.stage = None
        self.form_status = ""
    
    def update(self, landmarks, image):
        joint_indices = self.config["joints"]
        points = [ [landmarks[i].x, landmarks[i].y] for i in joint_indices ]
        angle = calculate_angle(*points)

        # Açı ekrana yazdır
        cv2.putText(image, f"{int(angle)}°", tuple(np.multiply(points[1], [640, 480]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Tekrar sayımı
        if angle > self.config["angle_thresholds"]["down"]:
            self.stage = "down"
        if angle < self.config["angle_thresholds"]["up"] and self.stage == "down":
            self.stage = "up"
            self.counter += 1

        # Form analizi
        form_min, form_max = self.config["form_range"]
        if form_min <= angle <= form_max:
            self.form_status = "Good Form"
            color = (0, 255, 0)
        else:
            self.form_status = "Bad Form"
            color = (0, 0, 255)

        cv2.putText(image, self.form_status,
                    (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    def render_ui(self, image):
        cv2.rectangle(image, (0, 0), (225, 73), (245, 117, 16), -1)
        cv2.putText(image, 'REPS', (15, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)
        cv2.putText(image, str(self.counter), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)
        cv2.putText(image, 'STAGE', (65, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)
        cv2.putText(image, self.stage or "", (60, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)

    def save_session(self):
        log_session(self.name, self.counter)
