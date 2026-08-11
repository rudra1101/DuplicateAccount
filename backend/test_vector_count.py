from app.ai.vector_store import (
    faiss_account_store,
)

print()

print("Vector count")

print(faiss_account_store.count)

print()

print("Dimension")

print(faiss_account_store.dimension)