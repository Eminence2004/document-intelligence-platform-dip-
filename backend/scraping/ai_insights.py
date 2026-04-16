import openai
from typing import Dict, List
import requests
import json
import os
import re

class AIInsightsGenerator:
    """Generates AI insights for books using LLM"""
    
    def __init__(self, use_local_lmstudio=False, local_url="http://localhost:1234/v1"):
        # Fix: properly initialize instance variables
        self.use_local_lmstudio = use_local_lmstudio
        self.local_url = local_url
        
        if not use_local_lmstudio:
            # Use OpenAI (optional - only if you have API key)
            openai.api_key = os.getenv('OPENAI_API_KEY', '')
    
    def _call_llm(self, prompt: str, max_tokens=500) -> str:
        """Generic LLM call - works with LM Studio or OpenAI"""
        try:
            if self.use_local_lmstudio:
                # LM Studio local endpoint
                response = requests.post(
                    f"{self.local_url}/completions",
                    json={
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "stop": ["\n\n", "Human:", "Assistant:"]
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result:
                        return result['choices'][0].get('text', '').strip()
                    elif 'response' in result:
                        return result['response'].strip()
                    else:
                        return self._get_mock_response(prompt)
                else:
                    print(f"LM Studio error: {response.status_code}")
                    return self._get_mock_response(prompt)
            else:
                # Return mock responses since OpenAI might not be configured
                return self._get_mock_response(prompt)
        except Exception as e:
            print(f"LLM call error: {e}")
            return self._get_mock_response(prompt)
    
    def _get_mock_response(self, prompt: str) -> str:
        """Provide mock responses when LLM is unavailable"""
        prompt_lower = prompt.lower()
        
        if "summary" in prompt_lower:
            return "This book offers valuable insights and perspectives on its subject matter. It explores key themes and provides thought-provoking content that will engage readers interested in this topic."
        elif "genre" in prompt_lower:
            # Try to detect genre from prompt
            if "finance" in prompt_lower or "money" in prompt_lower:
                return "Finance"
            elif "fiction" in prompt_lower or "story" in prompt_lower:
                return "Fiction"
            elif "psychology" in prompt_lower:
                return "Psychology"
            else:
                return "Non-Fiction"
        elif "sentiment" in prompt_lower:
            return "0.6"
        elif "recommend" in prompt_lower:
            return "Similar books you might enjoy"
        else:
            return "Based on the book's content, this is a thoughtful and informative work that provides valuable insights."
    
    def generate_summary(self, book_data: Dict) -> str:
        """Generate book summary"""
        # Try to extract a reasonable summary from description
        description = book_data.get('description', '')
        if description and len(description) > 50:
            # Use first few sentences as summary
            sentences = re.split(r'[.!?]+', description)
            summary = '. '.join(sentences[:2]) + '.'
            if len(summary) > 300:
                summary = summary[:300] + '...'
            return summary
        else:
            prompt = f"""Generate a concise 2-3 sentence summary of the following book:
            
            Title: {book_data.get('title', 'Unknown')}
            Author: {book_data.get('author', 'Unknown')}
            
            Summary:"""
            return self._call_llm(prompt, max_tokens=150)
    
    def classify_genre(self, book_data: Dict) -> str:
        """Classify book genre based on title and description"""
        title = book_data.get('title', '').lower()
        description = book_data.get('description', '').lower()
        
        # Simple keyword-based genre detection
        genre_keywords = {
            'Fiction': ['story', 'novel', 'tale', 'fiction'],
            'Mystery': ['mystery', 'detective', 'murder', 'crime'],
            'Romance': ['romance', 'love', 'relationship'],
            'Science Fiction': ['sci-fi', 'space', 'future', 'alien', 'robot'],
            'Fantasy': ['magic', 'dragon', 'wizard', 'fantasy'],
            'Thriller': ['thriller', 'suspense', 'chase'],
            'Biography': ['life', 'memoir', 'autobiography', 'biography'],
            'History': ['history', 'war', 'ancient', 'century'],
            'Self-Help': ['self-help', 'improve', 'success', 'habits'],
            'Finance': ['money', 'invest', 'wealth', 'finance', 'economy']
        }
        
        for genre, keywords in genre_keywords.items():
            for keyword in keywords:
                if keyword in title or keyword in description:
                    return genre
        
        # If no match, try LLM
        prompt = f"""Classify the genre of this book from these categories: 
        Fiction, Mystery, Romance, Science Fiction, Fantasy, Thriller, Biography, History, Self-Help, Finance, Other.
        
        Title: {book_data.get('title', 'Unknown')}
        Description: {book_data.get('description', '')[:300]}
        
        Genre (just one word):"""
        
        genre = self._call_llm(prompt, max_tokens=20).strip()
        
        # Clean up the response
        valid_genres = ['Fiction', 'Mystery', 'Romance', 'Science Fiction', 'Fantasy', 
                       'Thriller', 'Biography', 'History', 'Self-Help', 'Finance', 'Other']
        for valid in valid_genres:
            if valid.lower() in genre.lower():
                return valid
        return "General"
    
    def analyze_sentiment(self, book_data: Dict) -> float:
        """Analyze sentiment from description"""
        description = book_data.get('description', '').lower()
        
        # Simple sentiment based on positive/negative words
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'insightful', 'helpful', 'positive']
        negative_words = ['bad', 'poor', 'terrible', 'disappointing', 'boring', 'confusing', 'negative']
        
        positive_count = sum(1 for word in positive_words if word in description)
        negative_count = sum(1 for word in negative_words if word in description)
        
        total = positive_count + negative_count
        if total > 0:
            score = (positive_count - negative_count) / total
            return max(-0.8, min(0.8, score))
        
        return 0.3  # Slightly positive default
    
    def get_recommendations(self, book_title: str, all_books: List[Dict]) -> List[Dict]:
        """Get book recommendations based on similarity"""
        if not all_books:
            return []
        
        # Simple recommendation based on genre matching
        current_book = None
        for book in all_books:
            if book.get('title') == book_title:
                current_book = book
                break
        
        if not current_book:
            return all_books[:3]
        
        current_genre = current_book.get('genre', '')
        
        # Find books with same genre
        same_genre = [b for b in all_books if b.get('genre') == current_genre and b.get('title') != book_title]
        
        if same_genre:
            return same_genre[:3]
        
        return all_books[:3]