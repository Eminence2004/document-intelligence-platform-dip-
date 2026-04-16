from typing import List, Dict
import re
from sentence_transformers import SentenceTransformer

class SmartChunker:
    """Implements advanced chunking strategies for better RAG"""
    
    def __init__(self):
        self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def semantic_chunking(self, text: str, max_chunk_size=500, overlap=50) -> List[str]:
        """Chunk text based on semantic boundaries"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > max_chunk_size and current_chunk:
                # Add overlap from previous chunk
                if overlap > 0 and chunks:
                    overlap_text = ' '.join(current_chunk[-overlap:]) if overlap < len(current_chunk) else ' '.join(current_chunk)
                    current_chunk = [overlap_text] + current_chunk
                
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def sliding_window_chunking(self, text: str, window_size=300, stride=200) -> List[str]:
        """Create overlapping chunks using sliding window"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), stride):
            chunk = ' '.join(words[i:i + window_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def paragraph_chunking(self, text: str, max_chars=1000) -> List[str]:
        """Chunk by paragraphs"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            if current_length + len(para) > max_chars:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(para)
            current_length += len(para)
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks