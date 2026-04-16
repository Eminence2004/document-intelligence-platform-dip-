import requests
from typing import Dict, List
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class BookScraper:
    """Scrapes book data from Open Library API with Selenium fallback for Goodreads"""
    
    def __init__(self, use_selenium_fallback=True):
        self.use_selenium_fallback = use_selenium_fallback
        self.driver = None
        
    def _setup_selenium_driver(self):
        """Setup Chrome driver for Selenium"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Use webdriver_manager to automatically handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return self.driver
    
    def _scrape_goodreads(self, url: str) -> Dict:
        """Scrape book data from Goodreads using Selenium"""
        try:
            driver = self._setup_selenium_driver()
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            
            # Extract data with multiple selector attempts
            title = None
            try:
                title = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "h1[data-testid='bookTitle'], h1.TextContainer__title")
                )).text
            except:
                try:
                    title = driver.find_element(By.CSS_SELECTOR, "h1").text
                except:
                    title = "Unknown"
            
            # Get author
            author = "Unknown"
            try:
                author_elem = driver.find_element(By.CSS_SELECTOR, 
                    "div[data-testid='authorName'] a, span.ContributorLink__contributor")
                author = author_elem.text
            except:
                pass
            
            # Get rating
            rating = 0.0
            try:
                rating_elem = driver.find_element(By.CSS_SELECTOR, 
                    "div[data-testid='ratingValue'], div.RatingStatistics__rating")
                rating_text = rating_elem.text.split()[0]
                rating = float(rating_text)
            except:
                pass
            
            # Get description
            description = "No description available"
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, 
                    "div[data-testid='description'], div.BookPage__description")
                description = desc_elem.text
                if not description:
                    description = "No description available"
            except:
                pass
            
            return {
                'title': title,
                'author': author,
                'rating': rating,
                'description': description,
                'book_url': url,
                'cover_image': '',
                'source': 'goodreads'
            }
            
        except Exception as e:
            print(f"Goodreads scraping error: {e}")
            return None
    
    def search_book(self, query: str) -> List[Dict]:
        """Search for books by title using Open Library API"""
        url = f"https://openlibrary.org/search.json?q={query}&limit=5"
        response = requests.get(url)
        data = response.json()
        
        books = []
        for doc in data.get('docs', []):
            # Get description (first sentence or key)
            description = doc.get('first_sentence', ['No description'])[0] if doc.get('first_sentence') else 'No description available'
            if description == 'No description available' and doc.get('key'):
                # Try to get full description
                work_url = f"https://openlibrary.org{doc.get('key')}.json"
                try:
                    work_response = requests.get(work_url)
                    if work_response.status_code == 200:
                        work_data = work_response.json()
                        desc = work_data.get('description', {})
                        if isinstance(desc, dict):
                            description = desc.get('value', 'No description available')
                        elif isinstance(desc, str):
                            description = desc
                except:
                    pass
            
            book = {
                'title': doc.get('title', 'Unknown'),
                'author': ', '.join(doc.get('author_name', ['Unknown'])),
                'description': description[:1000],  # Limit length
                'rating': doc.get('ratings_average', 0),
                'book_url': f"https://openlibrary.org{doc.get('key', '')}",
                'cover_image': f"https://covers.openlibrary.org/b/id/{doc.get('cover_i', '')}-L.jpg" if doc.get('cover_i') else '',
                'source': 'openlibrary'
            }
            books.append(book)
        
        return books
    
    def get_book_by_isbn(self, isbn: str) -> Dict:
        """Get book by ISBN using Open Library API"""
        url = f"https://openlibrary.org/isbn/{isbn}.json"
        response = requests.get(url)
        
        if response.status_code != 200:
            # Try Goodreads as fallback
            if self.use_selenium_fallback:
                return self._scrape_goodreads(f"https://www.goodreads.com/search?q={isbn}")
            return None
            
        data = response.json()
        
        # Get author info
        author_key = data.get('authors', [{}])[0].get('key', '')
        author_name = 'Unknown'
        if author_key:
            author_url = f"https://openlibrary.org{author_key}.json"
            author_response = requests.get(author_url)
            if author_response.status_code == 200:
                author_name = author_response.json().get('name', 'Unknown')
        
        # Get description
        description = data.get('description', 'No description available')
        if isinstance(description, dict):
            description = description.get('value', 'No description available')
        
        return {
            'title': data.get('title', 'Unknown'),
            'author': author_name,
            'description': description[:1000],
            'rating': 0,
            'book_url': f"https://openlibrary.org/isbn/{isbn}",
            'cover_image': f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg",
            'source': 'openlibrary'
        }
    
    def scrape_goodreads_url(self, url: str) -> Dict:
        """Specifically scrape a Goodreads URL"""
        if 'goodreads.com' in url:
            return self._scrape_goodreads(url)
        return None
    
    def scrape_book_from_url(self, book_url: str) -> Dict:
        """Handle different URL types with fallback"""
        book_data = None
        
        # Check if it's a Goodreads URL
        if 'goodreads.com' in book_url and self.use_selenium_fallback:
            book_data = self._scrape_goodreads(book_url)
            if book_data:
                return book_data
        
        # Check if it's an ISBN
        isbn_clean = re.sub(r'[^0-9]', '', book_url)
        if len(isbn_clean) in [10, 13]:
            book_data = self.get_book_by_isbn(isbn_clean)
            if book_data:
                return book_data
        
        # Search by title/query
        if ' ' in book_url or len(book_url) < 50:
            books = self.search_book(book_url)
            if books:
                return books[0]
        
        # Try to extract ISBN from URL
        isbn_match = re.search(r'(\d{10}|\d{13})', book_url)
        if isbn_match:
            book_data = self.get_book_by_isbn(isbn_match.group(1))
            if book_data:
                return book_data
        
        # Try to extract title from URL and search
        title = book_url.split('/')[-1].replace('-', ' ').replace('_', ' ')
        if title:
            books = self.search_book(title)
            if books:
                return books[0]
        
        return None
    
    def bulk_scrape(self, queries: List[str]) -> List[Dict]:
        """Scrape multiple books"""
        books_data = []
        for query in queries:
            book_data = self.scrape_book_from_url(query)
            if book_data:
                books_data.append(book_data)
            time.sleep(1)  # Be respectful to APIs
        return books_data
    
    def close(self):
        """Close Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None