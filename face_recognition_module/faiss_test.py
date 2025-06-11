import cv2
import torch
import numpy as np
import faiss
import json
import os
import logging
import csv
from datetime import datetime, timedelta
from facenet_pytorch import MTCNN, InceptionResnetV1

# ------------------ Logging Setup ------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('face_recognition.log', encoding='utf-8')
    ]
)

# ------------------ Global Initialization ------------------
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=112, margin=0, keep_all=True, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(BASE_DIR, 'face_index.faiss')
label_path = os.path.join(BASE_DIR, 'labels.json')

index = faiss.read_index(index_path)
with open(label_path, 'r') as f:
    name_dict = json.load(f)

RECOGNITION_THRESHOLD = 1.0
FRAME_SKIP = 2
ATTENDANCE_TIMEOUT = 60  # seconds

csv_log_path = os.path.join(BASE_DIR, 'recognition_log.csv')
if not os.path.isfile(csv_log_path):
    with open(csv_log_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Name', 'Score'])

# ------------------ Attendance Tracker ------------------
attendance_tracker = {}

def update_attendance(name):
    now = datetime.now()

    if name == "Unknown":
        return

    if name not in attendance_tracker:
        attendance_tracker[name] = {
            'in_time': now,
            'last_seen': now,
            'out_time': None,
            'logged': False
        }
        logging.info(f"[ATTENDANCE] {name} entered at {now}")
    else:
        attendance_tracker[name]['last_seen'] = now

def finalize_attendance():
    now = datetime.now()
    for name, data in attendance_tracker.items():
        if data['out_time'] is None and (now - data['last_seen']).seconds > ATTENDANCE_TIMEOUT:
            data['out_time'] = data['last_seen']
            duration = data['out_time'] - data['in_time']
            if not data['logged']:
                logging.info(f"[ATTENDANCE] {name} exited at {data['out_time']} (Duration: {duration})")
                with open(csv_log_path, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        data['in_time'].strftime("%Y-%m-%d %H:%M:%S"),
                        name,
                        "IN"
                    ])
                    writer.writerow([
                        data['out_time'].strftime("%Y-%m-%d %H:%M:%S"),
                        name,
                        f"OUT ({str(duration)})"
                    ])
                data['logged'] = True

# ------------------ Recognition from Frame ------------------
def run_faiss_recognition_from_frame(frame):
    recognized_faces = []

    try:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, _ = mtcnn.detect(img_rgb)

        if boxes is not None:
            faces = mtcnn.extract(img_rgb, boxes, save_path=None)

            for i, face in enumerate(faces):
                if face is None:
                    continue

                face = face.unsqueeze(0).to(device)
                with torch.no_grad():
                    emb = model(face).cpu().numpy().astype('float32')

                D, I = index.search(emb, k=1)
                best_score = D[0][0]
                best_idx = I[0][0]

                name = name_dict.get(str(best_idx), "Unknown") if best_score < RECOGNITION_THRESHOLD else "Unknown"

                update_attendance(name)

                x1, y1, x2, y2 = map(int, boxes[i])
                w, h = x2 - x1, y2 - y1
                recognized_faces.append((x1, y1, w, h, name))

    except Exception as e:
        logging.error(f"⚠️ Error during recognition: {e}")

    return recognized_faces

# ------------------ Webcam Recognition ------------------
def run_faiss_recognition():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.error("Failed to open webcam.")
        return

    logging.info("🎥 Starting webcam recognition with FAISS. Press 'q' to quit.")
    frame_count = 0
    results = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % FRAME_SKIP == 0:
            results = run_faiss_recognition_from_frame(frame)

        for (x, y, w, h, name) in results:
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Face Recognition (FAISS)", frame)
        frame_count += 1

        finalize_attendance()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    run_faiss_recognition()
