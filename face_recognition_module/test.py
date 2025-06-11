import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import cv2
import torch
import numpy as np
import pickle
from facenet_pytorch import MTCNN, InceptionResnetV1
from sklearn.metrics.pairwise import cosine_similarity

# Load known embeddings and model only once for performance
with open('face_recognition_module/face_embeddings.pkl', 'rb') as f:
    data = pickle.load(f)

known_embeddings = np.array(data['embeddings'])
known_names = data['names']

# Set up the face detector and recognition model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, margin=0, keep_all=True, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def run_recognition(frame):
    """
    Process a single frame (BGR) and return list of (x, y, w, h, name).
    """
    results = []

    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, _ = mtcnn.detect(rgb_frame)

        if boxes is not None:
            faces = mtcnn.extract(rgb_frame, boxes, save_path=None)

            for i, face in enumerate(faces):
                face = face.unsqueeze(0).to(device)
                with torch.no_grad():
                    emb = model(face).cpu().numpy()

                sims = cosine_similarity(emb, known_embeddings)[0]
                best_idx = np.argmax(sims)
                best_score = sims[best_idx]
                name = known_names[best_idx] if best_score > 0.5 else "Unknown"

                x1, y1, x2, y2 = map(int, boxes[i])
                results.append((x1, y1, x2 - x1, y2 - y1, name))

    except Exception as e:
        print(f"[Recognition Error] {e}")

    return results
