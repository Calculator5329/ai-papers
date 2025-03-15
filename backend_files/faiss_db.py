import faiss
import numpy as np
import os

FAISS_INDEX_PATH = "faiss_index.bin"

class VectorDB:
    """
    FAISS-based vector database with persistence.
    """

    def __init__(self, embedding_dim=1536, index_path=FAISS_INDEX_PATH):
        self.embedding_dim = embedding_dim
        self.index_path = index_path

        # Load existing FAISS index if available
        if os.path.exists(self.index_path):
            print("🔄 Loading existing FAISS index...")
            self.index = faiss.read_index(self.index_path)
        else:
            print("🆕 Creating new FAISS index...")
            self.index = faiss.IndexFlatL2(embedding_dim)  # L2 distance search

        self.metadata = []  # Store metadata in memory

    def save_index(self):
        """
        Saves the FAISS index to disk.
        """
        faiss.write_index(self.index, self.index_path)
        print(f"💾 FAISS index saved to {self.index_path}")

    def add(self, embeddings, metadata):
        """
        Adds new embeddings and metadata to the FAISS index in batches.
        """
        if len(embeddings) != len(metadata):
            raise ValueError("Embeddings and metadata must have the same length.")

        embeddings = np.array(embeddings, dtype=np.float32)
        self.index.add(embeddings)  # Batch insert

        self.metadata.extend(metadata)
        self.save_index()  # Save after insertion

    def search(self, query_embedding, top_k=5):
        """
        Searches for the most relevant embeddings.
        """
        if self.index.ntotal == 0:
            return []  # No results if index is empty

        query_embedding = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for j, i in enumerate(indices[0]):
            if i < len(self.metadata):
                results.append((self.metadata[i], distances[0][j]))

        return results