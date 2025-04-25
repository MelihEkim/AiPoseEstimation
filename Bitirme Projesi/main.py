from exercise_logic import ExerciseSession
from pose_utils import init_pose, get_landmarks
import cv2
import json
from gui.app_ui import choose_exercise

def main():
    with open("exercise_config.json", "r") as f:
        config = json.load(f)
    exercise_name = choose_exercise(config)

    cap = cv2.VideoCapture(0)
    pose = init_pose()
    session = ExerciseSession(exercise_name)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        landmarks, image = get_landmarks(pose, frame)
        if landmarks:
            session.update(landmarks, image)

        session.render_ui(image)
        cv2.imshow("Spor Analiz", image)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    session.save_session()

if __name__ == "__main__":
    main()
