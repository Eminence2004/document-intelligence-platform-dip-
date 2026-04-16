from .vector_store import VectorStoreManager
from .chunking import SmartChunker
from scraping.ai_insights import AIInsightsGenerator
from typing import Dict, List
import hashlib
from django.core.cache import cache
from books.models import BookChunk

class RAGQueryEngine:
    """Complete RAG pipeline implementation"""
    
    def __init__(self):
        self.vector_store = VectorStoreManager()
        self.chunker = SmartChunker()
        self.llm = AIInsightsGenerator(use_local_lmstudio=True)
        self.cache_ttl = 3600
    
    def _get_cache_key(self, book_id: int, question: str) -> str:
        return f"rag_query_{book_id}_{hashlib.md5(question.encode()).hexdigest()}"
    
    def answer_question(self, book_id: int, question: str, book_data: Dict) -> Dict:
        """Main RAG pipeline - answer question about a book"""
        
        # Check cache
        cache_key = self._get_cache_key(book_id, question)
        cached_answer = cache.get(cache_key)
        if cached_answer:
            return cached_answer
        
        # Try to get chunks from database first
        chunks_from_db = BookChunk.objects.filter(book_id=book_id).order_by('chunk_index')
        
        if chunks_from_db.exists():
            # Use chunks from database for context
            context = "\n\n".join([chunk.chunk_text for chunk in chunks_from_db[:5]])
            sources = [f"Excerpt from {book_data['title']} (Section {chunk.chunk_index + 1})" 
                      for chunk in chunks_from_db[:3]]
            
            print(f"Using {chunks_from_db.count()} chunks from database")
        else:
            # Try vector search as fallback
            similar_chunks = self.vector_store.similarity_search(book_id, question, k=5)
            
            if not similar_chunks:
                return {
                    "answer": "I couldn't find relevant information in this book to answer your question. Please make sure the book has been properly processed with text chunks.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            context = "\n\n".join([chunk for chunk, _ in similar_chunks[:3]])
            sources = [f"Excerpt from {book_data['title']}" for _ in similar_chunks[:3]]
        
        # Generate answer with LLM
        prompt = f"""You are a helpful assistant answering questions about the book "{book_data['title']}" by {book_data['author']}.

Context from the book:
{context}

Question: {question}

Please provide a clear, accurate answer based ONLY on the context above. If the answer cannot be found in the context, say so.
Include citations by referencing "according to the book" or similar phrasing.

Answer:"""
        
        try:
            answer = self.llm._call_llm(prompt, max_tokens=300)
        except Exception as e:
            print(f"LLM error: {e}")
            answer = f"Based on the available information about '{book_data['title']}', " + \
                     f"the book discusses {book_data.get('summary', 'various topics')}. " + \
                     f"For more specific details about '{question}', please refer to the book directly."
        
        result = {
            "answer": answer,
            "sources": sources if 'sources' in locals() else [],
            "confidence": 0.8 if chunks_from_db.exists() else 0.5
        }
        
        # Cache the result
        cache.set(cache_key, result, self.cache_ttl)
        
        return result