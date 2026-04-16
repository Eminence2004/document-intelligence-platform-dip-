# rag/recommendations.py
import requests
from typing import List, Dict
from scraping.book_scraper import BookScraper
from scraping.ai_insights import AIInsightsGenerator

class RecommendationEngine:
    """Generates book recommendations from external sources"""
    
    def __init__(self):
        self.scraper = BookScraper(use_selenium_fallback=False)
        self.ai = AIInsightsGenerator(use_local_lmstudio=True)
    
    def get_similar_books(self, book_title: str, genre: str = None) -> List[Dict]:
        """Get similar books from Open Library"""
        recommendations = []
        search_terms = [book_title]
        
        if genre and genre != 'Unclassified':
            search_terms.append(genre)
        
        for term in search_terms:
            results = self.scraper.search_book(term)
            for result in results:
                # Skip if it's the same book
                if result['title'].lower() != book_title.lower():
                    # Check if not already in list
                    if not any(r['title'] == result['title'] for r in recommendations):
                        recommendations.append(result)
                    
                    if len(recommendations) >= 5:
                        break
            if len(recommendations) >= 5:
                break
        
        return recommendations[:5]
    
    def get_recommendations_by_genre(self, genre: str) -> List[Dict]:
        """Get books by genre"""
        if not genre or genre == 'Unclassified':
            return []
        
        results = self.scraper.search_book(f"best {genre} books")
        return results[:5]
    
    def get_popular_books(self) -> List[Dict]:
        """Get popular books from Open Library"""
        results = self.scraper.search_book("bestseller")
        return results[:5]