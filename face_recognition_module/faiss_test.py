import cv2
import torch
import numpy as np
import faiss
import json
from facenet_pytorch import MTCNN, InceptionResnetV1

def run_faiss_recognition():
    # Load FAISS index and label dictionary
    index = faiss.read_index('face_recognition_module/face_index.faiss')
    with open('face_recognition_module/labels.json', 'r') as f:
        name_dict = json.load(f)

    # Initialize face detector and embedding model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    mtcnn = MTCNN(image_size=160, margin=0, keep_all=True, device=device)
    model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    # Start webcam
    cap = cv2.VideoCapture(0)
    print("Starting webcam recognition with FAISS. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, _ = mtcnn.detect(img_rgb)

        if boxes is not None:
            faces = mtcnn.extract(img_rgb, boxes, save_path=None)

            for i, face in enumerate(faces):
                face = face.unsqueeze(0).to(device)
                with torch.no_grad():
                    emb = model(face).cpu().numpy().astype('float32')  # FAISS requires float32

                # Search the FAISS index
                D, I = index.search(emb, k=1)
                best_score = D[0][0]
                best_idx = I[0][0]

                # Retrieve name using dictionary (keys are strings)
                name = name_dict.get(str(best_idx), "Unknown") if best_score < 1.0 else "Unknown"

                # Draw result
                x1, y1, x2, y2 = map(int, boxes[i])
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f'{name} ({best_score:.2f})', (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Face Recognition (FAISS)", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
