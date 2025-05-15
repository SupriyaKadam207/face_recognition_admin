import cv2
import torch
import numpy as np
import pickle
from facenet_pytorch import MTCNN, InceptionResnetV1
from sklearn.metrics.pairwise import cosine_similarity

def run_recognition():
    # Load known face embeddings
    with open('face_recognition_module/face_embeddings.pkl', 'rb') as f:
        data = pickle.load(f)

    known_embeddings = np.array(data['embeddings'])
    known_names = data['names']

    # Initialize detector and model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    mtcnn = MTCNN(image_size=160, margin=0, keep_all=True, device=device)
    model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    # Start webcam
    cap = cv2.VideoCapture(0)

    print("Starting webcam recognition. Press 'q' to quit.")

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
                    emb = model(face).cpu().numpy()

                sims = cosine_similarity(emb, known_embeddings)[0]
                best_idx = np.argmax(sims)
                best_score = sims[best_idx]
                name = known_names[best_idx] if best_score > 0.5 else "Unknown"

                # Draw bounding box and name
                x1, y1, x2, y2 = map(int, boxes[i])
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f'{name} ({best_score:.2f})', (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
