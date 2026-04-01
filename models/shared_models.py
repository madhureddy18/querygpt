# models/shared_models.py

from sentence_transformers import SentenceTransformer

print("[Models] Loading sentence transformer...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
print("[Models] Model ready ✓")