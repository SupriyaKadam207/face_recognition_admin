import os
import cv2
import torch
import numpy as np
from tqdm import tqdm
from facenet_pytorch import MTCNN, InceptionResnetV1
from torchvision import transforms
import pickle

# Initialize face detector and recognition model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Directory containing face folders
dataset_path = 'known_faces'

# Output files
embedding_file = 'face_embeddings.pkl'

# Store embeddings and labels
embeddings = []
names = []

# Preprocessing transform
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5])
])

# Process each person
for person_name in os.listdir(dataset_path):
    person_dir = os.path.join(dataset_path, person_name)
    if not os.path.isdir(person_dir):
        continue
    
    for image_name in os.listdir(person_dir):
        image_path = os.path.join(person_dir, image_name)
        img = cv2.imread(image_path)
        if img is None:
            continue

        # Detect and align face
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face = mtcnn(img_rgb)
        
        if face is not None:
            face = face.unsqueeze(0).to(device)  # [1, 3, 160, 160]
            with torch.no_grad():
                embedding = model(face)  # [1, 512]
                embeddings.append(embedding.squeeze(0).cpu().numpy())
                names.append(person_name)

print(f"Processed {len(embeddings)} faces.")

# Save embeddings and names
with open(embedding_file, 'wb') as f:
    pickle.dump({'embeddings': embeddings, 'names': names}, f)

print(f"Embeddings saved to {embedding_file}")
