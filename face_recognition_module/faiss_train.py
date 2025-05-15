'''
import os
import cv2
import torch
import numpy as np
from tqdm import tqdm
from facenet_pytorch import MTCNN, InceptionResnetV1
import faiss
import json

# Initialize face detector and recognition model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Directory containing face folders
dataset_path = 'known_faces'

# Output files
faiss_index_file = 'face_index.faiss'
label_file = 'labels.json'

# Store embeddings and labels
embeddings = []
names = []

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
            face = face.unsqueeze(0).to(device)
            with torch.no_grad():
                embedding = model(face)
                embeddings.append(embedding.squeeze(0).cpu().numpy())
                names.append(person_name)

print(f"Processed {len(embeddings)} faces.")

# Convert to NumPy array
embedding_matrix = np.array(embeddings).astype('float32')

# Build FAISS index
index = faiss.IndexFlatL2(embedding_matrix.shape[1])  # L2 distance
index.add(embedding_matrix)

# Save index and labels
faiss.write_index(index, faiss_index_file)
with open(label_file, 'w') as f:
    json.dump(names, f)

print(f"FAISS index saved to {faiss_index_file}")
print(f"Labels saved to {label_file}")
'''
import os
import cv2
import torch
import numpy as np
from tqdm import tqdm
from facenet_pytorch import MTCNN, InceptionResnetV1
import faiss
import json

# Initialize face detector and recognition model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, device=device)
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Directory containing face folders
dataset_path = 'known_faces'

# Output files
faiss_index_file = 'face_index.faiss'
label_file = 'labels.json'

# Store embeddings and labels
embeddings = []
names = []

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
            face = face.unsqueeze(0).to(device)
            with torch.no_grad():
                embedding = model(face)  # Shape: [1, 512]
                embeddings.append(embedding.squeeze(0).cpu().numpy())
                names.append(person_name)

print(f"Processed {len(embeddings)} faces.")

# Convert to NumPy array (float32 required for FAISS)
embedding_matrix = np.array(embeddings).astype('float32')

# Build FAISS index (L2 distance)
index = faiss.IndexFlatL2(embedding_matrix.shape[1])
index.add(embedding_matrix)

# Save index
faiss.write_index(index, faiss_index_file)

# Save labels as a dictionary
label_dict = {str(i): name for i, name in enumerate(names)}
with open(label_file, 'w') as f:
    json.dump(label_dict, f)

print(f"FAISS index saved to {faiss_index_file}")
print(f"Labels saved to {label_file} as dictionary")
