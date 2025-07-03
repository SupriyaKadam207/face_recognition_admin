import faiss
import numpy as np
import json

from .models import FaceData

def rebuild_faiss_index():
    faces = FaceData.objects.exclude(embedding__isnull=True)

    if not faces.exists():
        print("⚠️ No embeddings found to rebuild FAISS index.")
        return

    embeddings = []
    ids = []

    for face in faces:
        try:
            emb = np.frombuffer(face.embedding, dtype=np.float32)
            if emb.size == 0:
                print(f"⚠️ Empty embedding for {face.full_name()}")
                continue
            embeddings.append(emb)
            ids.append(face.id)
        except Exception as e:
            print(f"⚠️ Failed to load embedding for {face.full_name()}: {e}")

    if not embeddings:
        print("❌ No valid embeddings found — FAISS index not rebuilt.")
        return

    embeddings_np = np.array(embeddings).astype('float32')
    if embeddings_np.ndim != 2:
        print("❌ Invalid embedding shape. Expected 2D (N, D), got", embeddings_np.shape)
        return

    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)

    faiss.write_index(index, "faiss_index.bin")
    with open("faiss_ids.json", "w") as f:
        json.dump(ids, f)

    print("✅ FAISS index rebuilt with", len(ids), "entries.")
