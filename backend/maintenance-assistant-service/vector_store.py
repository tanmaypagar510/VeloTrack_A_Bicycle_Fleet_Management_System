import os
import json
import logging
import numpy as np

logger = logging.getLogger('vector-store')

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS or sentence-transformers not available. Using simple search fallback.")


class VectorStore:
    """FAISS-based vector store for bike history embeddings"""

    def __init__(self, index_path=None, model_name='all-MiniLM-L6-v2'):
        self.index_path = index_path or '/app/data/faiss_index'
        self.documents = []
        self.metadata = []
        self.index = None
        self.encoder = None

        if FAISS_AVAILABLE:
            try:
                self.encoder = SentenceTransformer(model_name)
                self._load_or_create_index()
            except Exception as e:
                logger.error(f"Failed to initialize encoder: {e}")

    def _load_or_create_index(self):
        """Load existing index or create a new one"""
        idx_file = os.path.join(self.index_path, 'index.faiss')
        meta_file = os.path.join(self.index_path, 'metadata.json')

        if os.path.exists(idx_file) and os.path.exists(meta_file):
            try:
                self.index = faiss.read_index(idx_file)
                with open(meta_file, 'r') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', [])
                    self.metadata = data.get('metadata', [])
                logger.info(f"Loaded FAISS index with {len(self.documents)} documents")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index"""
        if self.encoder:
            dim = self.encoder.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatL2(dim)
            self.documents = []
            self.metadata = []
            logger.info(f"Created new FAISS index with dimension {dim}")

    def add_documents(self, texts, meta_list=None):
        """Add documents to the vector store"""
        if not self.encoder or not self.index:
            self.documents.extend(texts)
            if meta_list:
                self.metadata.extend(meta_list)
            return

        embeddings = self.encoder.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')
        self.index.add(embeddings)
        self.documents.extend(texts)
        if meta_list:
            self.metadata.extend(meta_list)

    def search(self, query, top_k=5):
        """Search for similar documents"""
        if not self.encoder or not self.index or self.index.ntotal == 0:
            return self._simple_search(query, top_k)

        query_embedding = self.encoder.encode([query]).astype('float32')
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents) and idx >= 0:
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx] if idx < len(self.metadata) else {},
                    'distance': float(distances[0][i])
                })
        return results

    def _simple_search(self, query, top_k=5):
        """Fallback text-based search when FAISS isn't available"""
        query_lower = query.lower()
        scored = []
        for i, doc in enumerate(self.documents):
            score = sum(1 for word in query_lower.split() if word in doc.lower())
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)

        results = []
        for score, idx in scored[:top_k]:
            results.append({
                'document': self.documents[idx],
                'metadata': self.metadata[idx] if idx < len(self.metadata) else {},
                'distance': 1.0 / (score + 1)
            })
        return results

    def save(self):
        """Save index to disk"""
        os.makedirs(self.index_path, exist_ok=True)
        if self.index and FAISS_AVAILABLE:
            faiss.write_index(self.index, os.path.join(self.index_path, 'index.faiss'))
        with open(os.path.join(self.index_path, 'metadata.json'), 'w') as f:
            json.dump({'documents': self.documents, 'metadata': self.metadata}, f)
        logger.info(f"Saved vector store with {len(self.documents)} documents")

    def clear(self):
        """Clear the index"""
        self._create_new_index()
        self.documents = []
        self.metadata = []

