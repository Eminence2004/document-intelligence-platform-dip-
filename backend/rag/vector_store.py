# rag/vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib

class VectorStoreManager:
    """FAISS-based vector store for optimized embedding search with caching"""
    
    def __init__(self, persist_dir="./faiss_index"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        # Use a better embedding model for improved accuracy
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.indexes = {}
        self.metadata = {}
        self.embedding_cache = {}  # Cache for embeddings (bonus optimization)
        
    def get_or_create_index(self, book_id: int):
        """Get or create FAISS index for a book"""
        index_path = self.persist_dir / f"book_{book_id}.index"
        meta_path = self.persist_dir / f"book_{book_id}.pkl"
        
        if book_id in self.indexes:
            return self.indexes[book_id]
        
        if index_path.exists():
            # Load existing index
            index = faiss.read_index(str(index_path))
            with open(meta_path, 'rb') as f:
                metadata = pickle.load(f)
            self.indexes[book_id] = index
            self.metadata[book_id] = metadata
        else:
            # Create new index (using L2 distance for similarity)
            dimension = 384  # all-MiniLM-L6-v2 dimension
            index = faiss.IndexFlatL2(dimension)
            # Add IVF for faster search on larger datasets (optional)
            # quantizer = faiss.IndexFlatL2(dimension)
            # index = faiss.IndexIVFFlat(quantizer, dimension, 100)
            self.indexes[book_id] = index
            self.metadata[book_id] = {'chunks': [], 'ids': [], 'embeddings': []}
        
        return self.indexes[book_id]
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding with caching for optimization (bonus)"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        embedding = self.encoder.encode([text])[0]
        self.embedding_cache[cache_key] = embedding
        
        # Limit cache size
        if len(self.embedding_cache) > 10000:
            # Remove oldest 1000 entries
            keys_to_remove = list(self.embedding_cache.keys())[:1000]
            for key in keys_to_remove:
                del self.embedding_cache[key]
        
        return embedding
    
    def add_chunks(self, book_id: int, chunks: List[str], chunk_indices: List[int]) -> int:
        """Add chunks to FAISS index with optimized batch processing"""
        index = self.get_or_create_index(book_id)
        
        # Generate embeddings in batch (optimized)
        embeddings = self.encoder.encode(chunks, batch_size=32, show_progress_bar=False)
        
        # Add to FAISS index
        index.add(embeddings.astype('float32'))
        
        # Store metadata
        for idx, chunk, embedding in zip(chunk_indices, chunks, embeddings):
            self.metadata[book_id]['chunks'].append(chunk)
            self.metadata[book_id]['ids'].append(f"chunk_{book_id}_{idx}")
            self.metadata[book_id]['embeddings'].append(embedding.tolist())
        
        # Persist
        self._persist(book_id)
        
        print(f"✅ Added {len(chunks)} chunks to FAISS index for book {book_id}")
        return len(chunks)
    
    def similarity_search(self, book_id: int, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar chunks using FAISS with improved scoring"""
        index = self.get_or_create_index(book_id)
        
        if index.ntotal == 0:
            print(f"⚠️ No chunks found for book {book_id}")
            return []
        
        # Encode query with caching
        query_embedding = self._get_embedding(query)
        
        # Search (k = min(k, total chunks))
        search_k = min(k, index.ntotal)
        distances, indices = index.search(query_embedding.reshape(1, -1).astype('float32'), search_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.metadata[book_id]['chunks']):
                chunk = self.metadata[book_id]['chunks'][idx]
                # Convert L2 distance to similarity score (0-1 range)
                distance = distances[0][i]
                similarity = max(0, 1 - (distance / 2))  # Normalize
                results.append((chunk, similarity))
        
        print(f"🔍 Found {len(results)} relevant chunks for query: '{query[:50]}...'")
        return results
    
    def _persist(self, book_id: int):
        """Persist FAISS index and metadata"""
        if book_id in self.indexes:
            index_path = self.persist_dir / f"book_{book_id}.index"
            meta_path = self.persist_dir / f"book_{book_id}.pkl"
            
            faiss.write_index(self.indexes[book_id], str(index_path))
            with open(meta_path, 'wb') as f:
                # Don't save embeddings to save space (recompute if needed)
                metadata_to_save = {
                    'chunks': self.metadata[book_id]['chunks'],
                    'ids': self.metadata[book_id]['ids']
                }
                pickle.dump(metadata_to_save, f)
            
            print(f"💾 Persisted FAISS index for book {book_id}")
    
    def delete_collection(self, book_id: int):
        """Delete FAISS index for a book"""
        if book_id in self.indexes:
            del self.indexes[book_id]
            del self.metadata[book_id]
        
        index_path = self.persist_dir / f"book_{book_id}.index"
        meta_path = self.persist_dir / f"book_{book_id}.pkl"
        
        if index_path.exists():
            index_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        
        print(f"🗑️ Deleted FAISS index for book {book_id}")
    
    def get_index_stats(self, book_id: int) -> Dict:
        """Get statistics about the FAISS index"""
        index = self.get_or_create_index(book_id)
        return {
            'total_chunks': index.ntotal,
            'dimension': index.d,
            'metadata_count': len(self.metadata.get(book_id, {}).get('chunks', [])),
            'is_trained': index.is_trained
        }
    
    def search_multiple_books(self, book_ids: List[int], query: str, k: int = 3) -> List[Tuple[int, str, float]]:
        """Search across multiple books (bonus feature for cross-book queries)"""
        all_results = []
        
        for book_id in book_ids:
            results = self.similarity_search(book_id, query, k)
            for chunk, score in results:
                all_results.append((book_id, chunk, score))
        
        # Sort by score and return top k
        all_results.sort(key=lambda x: x[2], reverse=True)
        return all_results[:k]

# Alias for backward compatibility
FAISSVectorStore = VectorStoreManager