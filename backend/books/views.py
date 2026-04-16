from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.core.cache import cache
from django.http import StreamingHttpResponse
from .models import Book, ChatHistory, BookChunk
from .serializers import BookSerializer, BookDetailSerializer, QuestionRequestSerializer, ChatHistorySerializer
from scraping.book_scraper import BookScraper
from scraping.ai_insights import AIInsightsGenerator
from rag.vector_store import VectorStoreManager
from rag.query_engine import RAGQueryEngine
from rag.chunking import SmartChunker
import json
import time
import hashlib
import requests
from difflib import SequenceMatcher

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookSerializer
    
    def _is_duplicate_book(self, title, author=None, threshold=0.85):
        """Check if a book already exists in the database (fuzzy matching)"""
        existing_books = Book.objects.all()
        
        for existing in existing_books:
            # Check exact match (case insensitive)
            if existing.title.lower() == title.lower():
                return True, existing
            
            # Check fuzzy match for similar titles
            similarity = SequenceMatcher(None, title.lower(), existing.title.lower()).ratio()
            if similarity >= threshold:
                return True, existing
            
            # If author is provided, also check author match
            if author and existing.author and author != 'Unknown':
                author_similarity = SequenceMatcher(None, author.lower(), existing.author.lower()).ratio()
                if similarity >= 0.7 and author_similarity >= 0.7:
                    return True, existing
        
        return False, None
    
    def destroy(self, request, *args, **kwargs):
        """Delete a book and its associated vector index"""
        book = self.get_object()
        title = book.title
        
        try:
            vector_store = VectorStoreManager()
            vector_store.delete_collection(book.id)
            print(f"🗑️ Deleted vector index for book {book.id}")
        except Exception as e:
            print(f"Error deleting vector index: {e}")
        
        cache.delete(f"recs_{book.id}")
        response = super().destroy(request, *args, **kwargs)
        
        print(f"✅ Book '{title}' deleted successfully")
        return Response({"message": f"Book '{title}' deleted successfully"})
    
    @action(detail=False, methods=['post'])
    def upload_book(self, request):
        """Upload and process a new book with duplicate prevention"""
        url = request.data.get('url')
        
        if not url:
            return Response({"error": "URL or book title is required"}, status=400)
        
        scraper = BookScraper(use_selenium_fallback=False)
        
        try:
            book_data = scraper.scrape_book_from_url(url)
            
            if not book_data:
                return Response(
                    {"error": "Failed to find book. Try using: ISBN, book title, or URL"}, 
                    status=400
                )
            
            title = book_data.get('title', '')
            author = book_data.get('author', '')
            
            print(f"📚 Found book: {title} by {author}")
            
            # CHECK FOR DUPLICATE BEFORE SAVING
            is_duplicate, existing_book = self._is_duplicate_book(title, author)
            
            if is_duplicate:
                print(f"⚠️ Duplicate detected! Book already exists: {existing_book.title}")
                return Response({
                    "error": f"Book already exists in your library!",
                    "duplicate": True,
                    "existing_book": BookSerializer(existing_book).data,
                    "message": f"'{title}' is already in your library (added on {existing_book.created_at.strftime('%Y-%m-%d')})"
                }, status=409)  # 409 Conflict
            
            # Generate AI insights
            ai = AIInsightsGenerator(use_local_lmstudio=True)
            
            try:
                book_data['summary'] = ai.generate_summary(book_data)
                book_data['genre'] = ai.classify_genre(book_data)
                book_data['sentiment_score'] = ai.analyze_sentiment(book_data)
                print(f"🤖 AI Insights generated: Genre={book_data['genre']}, Sentiment={book_data['sentiment_score']}")
            except Exception as e:
                print(f"AI insight generation error: {e}")
                book_data['summary'] = "AI summary temporarily unavailable. Please try again later."
                book_data['genre'] = "Unclassified"
                book_data['sentiment_score'] = 0
            
            # Remove source field before saving
            book_data.pop('source', None)
            
            # Save to database
            book = Book.objects.create(**book_data)
            print(f"💾 Book saved to database with ID: {book.id}")
            
            # Process book text for RAG with smart chunking
            from rag.chunking import SmartChunker
            from rag.vector_store import VectorStoreManager
            
            chunker = SmartChunker()
            vector_store = VectorStoreManager()
            
            text_to_chunk = book_data.get('description', '')
            
            if len(text_to_chunk) < 100:
                text_to_chunk = f"""
Title: {book_data.get('title', '')}
Author: {book_data.get('author', '')}
Summary: {book_data.get('summary', '')}
Genre: {book_data.get('genre', '')}
"""
            
            print(f"📝 Processing text of length: {len(text_to_chunk)} characters")
            
            chunks = chunker.semantic_chunking(text_to_chunk, max_chunk_size=500, overlap=50)
            
            if not chunks:
                chunks = chunker.sliding_window_chunking(text_to_chunk, window_size=300, stride=200)
                print(f"📊 Used sliding window chunking")
            
            if not chunks:
                chunks = chunker.paragraph_chunking(text_to_chunk, max_chars=500)
                print(f"📊 Used paragraph chunking")
            
            if not chunks:
                chunks = [text_to_chunk[i:i+500] for i in range(0, len(text_to_chunk), 400)]
                print(f"📊 Used simple chunking as fallback")
            
            print(f"✅ Created {len(chunks)} chunks using smart chunking")
            
            if chunks:
                vector_store.add_chunks(
                    book.id, 
                    chunks, 
                    list(range(len(chunks)))
                )
                print(f"💾 Stored {len(chunks)} chunks in vector store")
                
                for idx, chunk in enumerate(chunks):
                    BookChunk.objects.create(
                        book=book,
                        chunk_text=chunk,
                        chunk_index=idx
                    )
                print(f"💾 Saved {len(chunks)} chunks to database")
            
            # Clear recommendations cache for other books since library changed
            cache.delete_pattern("recs_*")
            
            return Response({
                "message": f"Book '{book.title}' uploaded successfully",
                "book": BookSerializer(book).data,
                "chunks_created": len(chunks) if chunks else 0,
                "duplicate": False
            }, status=201)
            
        except Exception as e:
            print(f"Upload error: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
        finally:
            scraper.close()
    
    @action(detail=True, methods=['post'])
    def ask_question(self, request, pk=None):
        """RAG query endpoint with caching"""
        book = self.get_object()
        question = request.data.get('question')
        
        if not question:
            return Response({"error": "Question is required"}, status=400)
        
        cache_key = f"qa_{book.id}_{hashlib.md5(question.encode()).hexdigest()}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"📦 Cache hit for question: {question[:50]}...")
            return Response({
                **cached_result,
                "cached": True,
                "message": "This answer was retrieved from cache"
            })
        
        print(f"🔍 Cache miss, processing question: {question[:50]}...")
        
        book_data = BookSerializer(book).data
        rag_engine = RAGQueryEngine()
        result = rag_engine.answer_question(book.id, question, book_data)
        
        chat = ChatHistory.objects.create(
            book=book,
            question=question,
            answer=result['answer'],
            sources=result['sources']
        )
        print(f"💾 Saved chat history with ID: {chat.id}")
        
        response_data = {
            "answer": result['answer'],
            "sources": result['sources'],
            "confidence": result['confidence'],
            "chat_id": chat.id,
            "cached": False
        }
        
        cache.set(cache_key, response_data, 3600)
        print(f"💾 Cached answer for future requests")
        
        return Response(response_data)
    
    @action(detail=True, methods=['post'])
    def ask_question_stream(self, request, pk=None):
        """Streaming RAG query endpoint"""
        book = self.get_object()
        question = request.data.get('question')
        
        if not question:
            return Response({"error": "Question is required"}, status=400)
        
        def generate_stream():
            try:
                cache_key = f"qa_{book.id}_{hashlib.md5(question.encode()).hexdigest()}"
                cached_result = cache.get(cache_key)
                
                if cached_result:
                    yield json.dumps({'type': 'status', 'content': '📦 Found cached answer...'}) + '\n'
                    time.sleep(0.3)
                    
                    words = cached_result['answer'].split()
                    for i, word in enumerate(words):
                        chunk = word + (' ' if i < len(words)-1 else '')
                        yield json.dumps({'type': 'word', 'content': chunk}) + '\n'
                        time.sleep(0.03)
                    
                    if cached_result.get('sources'):
                        yield json.dumps({'type': 'sources', 'content': cached_result['sources']}) + '\n'
                    
                    yield json.dumps({'type': 'status', 'content': '✅ Answer retrieved from cache'}) + '\n'
                    return
                
                yield json.dumps({'type': 'status', 'content': '🔍 Searching book content...'}) + '\n'
                time.sleep(0.3)
                
                book_data = BookSerializer(book).data
                
                yield json.dumps({'type': 'status', 'content': '🧠 Analyzing with AI...'}) + '\n'
                time.sleep(0.3)
                
                rag_engine = RAGQueryEngine()
                result = rag_engine.answer_question(book.id, question, book_data)
                answer = result['answer']
                
                yield json.dumps({'type': 'status', 'content': '💬 Generating response...'}) + '\n'
                time.sleep(0.2)
                
                words = answer.split()
                for i, word in enumerate(words):
                    chunk = word + (' ' if i < len(words)-1 else '')
                    yield json.dumps({'type': 'word', 'content': chunk}) + '\n'
                    time.sleep(0.04)
                
                if result.get('sources'):
                    yield json.dumps({'type': 'sources', 'content': result['sources']}) + '\n'
                
                chat = ChatHistory.objects.create(
                    book=book,
                    question=question,
                    answer=answer,
                    sources=result.get('sources', [])
                )
                
                cache.set(cache_key, result, 3600)
                
                yield json.dumps({'type': 'status', 'content': f'✨ Answer saved (Chat ID: {chat.id})'}) + '\n'
                
            except Exception as e:
                yield json.dumps({'type': 'error', 'content': str(e)}) + '\n'
        
        return StreamingHttpResponse(
            generate_stream(),
            content_type='application/x-ndjson'
        )
    
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """Get book recommendations from external sources"""
        book = self.get_object()
        
        cache_key = f"recs_{book.id}"
        cached_recs = cache.get(cache_key)
        if cached_recs:
            print(f"📦 Returning cached recommendations for {book.title}")
            return Response({"recommendations": cached_recs, "cached": True, "source": "cache"})
        
        existing_book_titles = set(Book.objects.values_list('title', flat=True))
        existing_book_titles_lower = {title.lower() for title in existing_book_titles}
        
        print(f"📚 Existing books in library: {existing_book_titles}")
        
        recommendations = []
        
        try:
            search_queries = []
            
            if book.genre and book.genre != 'Unclassified':
                search_queries.append(f"best {book.genre} books")
                search_queries.append(f"popular {book.genre} fiction")
            
            title_words = book.title.split()[:3]
            if title_words:
                search_queries.append(' '.join(title_words))
            
            if book.author and book.author != 'Unknown':
                search_queries.append(book.author)
            
            for query in search_queries[:3]:
                url = f"https://openlibrary.org/search.json?q={query}&limit=15"
                response = requests.get(url, timeout=10)
                data = response.json()
                
                for doc in data.get('docs', []):
                    doc_title = doc.get('title', '')
                    
                    if doc_title.lower() in existing_book_titles_lower:
                        continue
                    if doc_title.lower() == book.title.lower():
                        continue
                    if any(r.get('title', '').lower() == doc_title.lower() for r in recommendations):
                        continue
                    
                    authors = doc.get('author_name', ['Unknown'])
                    author = ', '.join(authors[:2]) if authors else 'Unknown'
                    
                    subjects = doc.get('subject', [])
                    genre = subjects[0] if subjects else (book.genre if book.genre else 'General')
                    
                    rec_book = {
                        'title': doc_title,
                        'author': author,
                        'description': 'No description available',
                        'rating': doc.get('ratings_average', 0),
                        'cover_image': f"https://covers.openlibrary.org/b/id/{doc.get('cover_i', '')}-M.jpg" if doc.get('cover_i') else '',
                        'genre': genre if genre != 'Unclassified' else 'General',
                        'isbn': doc.get('isbn', [''])[0] if doc.get('isbn') else ''
                    }
                    recommendations.append(rec_book)
                    
                    if len(recommendations) >= 6:
                        break
                
                if len(recommendations) >= 6:
                    break
                        
        except Exception as e:
            print(f"Error fetching external recommendations: {e}")
        
        if recommendations:
            cache.set(cache_key, recommendations[:5], 86400)
        
        return Response({
            "recommendations": recommendations[:5], 
            "cached": False, 
            "source": "external",
            "message": f"Books you might like based on your interest in '{book.title}'"
        })
    
    @action(detail=True, methods=['get'])
    def chat_history(self, request, pk=None):
        """Get chat history for a book"""
        book = self.get_object()
        history = book.chats.all().order_by('-created_at')[:50]
        return Response(ChatHistorySerializer(history, many=True).data)
    
    @action(detail=True, methods=['delete'])
    def clear_chat_history(self, request, pk=None):
        """Clear chat history for a book"""
        book = self.get_object()
        deleted_count = book.chats.all().delete()[0]
        print(f"🗑️ Cleared {deleted_count} chat messages for book {book.id}")
        return Response({"message": f"Deleted {deleted_count} chat messages"})
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Bulk upload multiple books with duplicate prevention"""
        urls = request.data.get('urls', [])
        
        if not urls:
            return Response({"error": "URLs list required"}, status=400)
        
        scraper = BookScraper(use_selenium_fallback=False)
        books_data = scraper.bulk_scrape(urls)
        scraper.close()
        
        created_books = []
        failed_books = []
        duplicate_books = []
        
        for book_data in books_data:
            try:
                title = book_data.get('title', '')
                author = book_data.get('author', '')
                
                # Check for duplicate
                is_duplicate, existing = self._is_duplicate_book(title, author)
                
                if is_duplicate:
                    duplicate_books.append({
                        'title': title,
                        'existing_id': existing.id,
                        'existing_date': existing.created_at.strftime('%Y-%m-%d')
                    })
                    print(f"⚠️ Skipping duplicate: {title}")
                    continue
                
                ai = AIInsightsGenerator(use_local_lmstudio=True)
                book_data['summary'] = ai.generate_summary(book_data)
                book_data['genre'] = ai.classify_genre(book_data)
                book_data['sentiment_score'] = ai.analyze_sentiment(book_data)
                
                book_data.pop('source', None)
                book = Book.objects.create(**book_data)
                created_books.append(book)
                print(f"✅ Uploaded: {book.title}")
            except Exception as e:
                print(f"❌ Failed to upload book: {e}")
                failed_books.append(book_data.get('title', 'Unknown'))
        
        return Response({
            "success": BookSerializer(created_books, many=True).data,
            "failed": failed_books,
            "duplicates": duplicate_books,
            "total_success": len(created_books),
            "total_failed": len(failed_books),
            "total_duplicates": len(duplicate_books)
        }, status=201)
    
    @action(detail=True, methods=['get'])
    def chunks_info(self, request, pk=None):
        """Debug endpoint to check book chunks"""
        book = self.get_object()
        chunks = BookChunk.objects.filter(book=book)
        
        try:
            vector_store = VectorStoreManager()
            stats = vector_store.get_index_stats(book.id)
        except Exception as e:
            stats = {"error": str(e)}
        
        return Response({
            'book_id': book.id,
            'title': book.title,
            'chunks_count': chunks.count(),
            'chunking_strategy': 'semantic + sliding window + paragraph',
            'vector_store_stats': stats,
            'chunks': [{'index': c.chunk_index, 'text_preview': c.chunk_text[:100]} 
                       for c in chunks[:5]]
        })
    
    @action(detail=True, methods=['get'])
    def vector_search_test(self, request, pk=None):
        """Test endpoint to verify vector search is working"""
        book = self.get_object()
        query = request.query_params.get('q', 'main theme')
        
        try:
            vector_store = VectorStoreManager()
            results = vector_store.similarity_search(book.id, query, k=3)
            
            return Response({
                'query': query,
                'results_count': len(results),
                'results': [{'text': text[:200], 'score': score} for text, score in results]
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)