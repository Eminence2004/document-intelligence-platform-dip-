import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

const BookDetail = () => {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [answering, setAnswering] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [useStreaming, setUseStreaming] = useState(true);
  const [streamingAnswer, setStreamingAnswer] = useState('');
  const [recommendations, setRecommendations] = useState([]);
  const [addingBook, setAddingBook] = useState(null);
  const [existingBooks, setExistingBooks] = useState(new Set());
  const [darkMode, setDarkMode] = useState(false);
  const chatContainerRef = useRef(null);

  const API_URL = 'http://localhost:8000/api';

  useEffect(() => {
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode === 'true') {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    } else {
      setDarkMode(false);
      document.documentElement.classList.remove('dark');
    }
    
    fetchBookDetails();
    fetchChatHistory();
    fetchExistingBooks();
    fetchRecommendations();
  }, [id]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    if (newMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('darkMode', 'true');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('darkMode', 'false');
    }
  };

  const fetchBookDetails = async () => {
    try {
      const response = await axios.get(`${API_URL}/books/${id}/`);
      setBook(response.data);
    } catch (error) {
      console.error('Error fetching book details:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchExistingBooks = async () => {
    try {
      const response = await axios.get(`${API_URL}/books/`);
      const books = Array.isArray(response.data) ? response.data : (response.data.results || []);
      const bookTitles = new Set(books.map(b => b.title.toLowerCase()));
      setExistingBooks(bookTitles);
    } catch (error) {
      console.error('Error fetching existing books:', error);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/books/${id}/chat_history/`);
      setChatHistory(response.data);
    } catch (error) {
      console.error('Error fetching chat history:', error);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await axios.get(`${API_URL}/books/${id}/recommendations/`);
      const recs = response.data.recommendations || response.data;
      // Filter out books that are already in library
      const filteredRecs = Array.isArray(recs) 
        ? recs.filter(rec => !existingBooks.has(rec.title?.toLowerCase()) && rec.title?.toLowerCase() !== book?.title?.toLowerCase())
        : [];
      setRecommendations(filteredRecs);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      setRecommendations([]);
    }
  };

  const addBookToLibrary = async (recBook) => {
    // Double-check if book already exists
    if (existingBooks.has(recBook.title.toLowerCase())) {
      alert(`📚 "${recBook.title}" is already in your library!`);
      // Remove from recommendations
      setRecommendations(prev => prev.filter(r => r.title !== recBook.title));
      return;
    }
    
    setAddingBook(recBook.title);
    try {
      // Try to add by title first
      await axios.post(`${API_URL}/books/upload_book/`, { 
        url: recBook.title 
      });
      alert(`✅ "${recBook.title}" has been added to your library!`);
      
      // Update existing books set
      setExistingBooks(prev => new Set([...prev, recBook.title.toLowerCase()]));
      
      // Remove this book from recommendations
      setRecommendations(prev => prev.filter(r => r.title !== recBook.title));
      
      // Refresh recommendations
      fetchRecommendations();
    } catch (error) {
      // If title fails, try by ISBN if available
      if (recBook.isbn) {
        try {
          await axios.post(`${API_URL}/books/upload_book/`, { url: recBook.isbn });
          alert(`✅ "${recBook.title}" has been added to your library!`);
          setExistingBooks(prev => new Set([...prev, recBook.title.toLowerCase()]));
          setRecommendations(prev => prev.filter(r => r.title !== recBook.title));
          fetchRecommendations();
        } catch (err) {
          alert(`❌ Couldn't add "${recBook.title}". Try searching for it manually.`);
        }
      } else {
        alert(`❌ Couldn't add "${recBook.title}". Try searching for it manually.`);
      }
    } finally {
      setAddingBook(null);
    }
  };

  const clearChatHistory = async () => {
    if (window.confirm('Clear all chat history for this book?')) {
      try {
        await axios.delete(`${API_URL}/books/${id}/clear_chat_history/`);
        setChatHistory([]);
        alert('Chat history cleared!');
      } catch (error) {
        console.error('Error clearing history:', error);
        alert('Failed to clear chat history');
      }
    }
  };

  const deleteBook = async () => {
    if (window.confirm(`Are you sure you want to delete "${book?.title}"? This action cannot be undone.`)) {
      try {
        await axios.delete(`${API_URL}/books/${id}/`);
        alert(`"${book?.title}" has been deleted!`);
        window.location.href = '/';
      } catch (error) {
        console.error('Error deleting book:', error);
        alert('Failed to delete book');
      }
    }
  };

  const askQuestionStream = async () => {
    if (!question.trim()) return;
    
    setAnswering(true);
    setAnswer(null);
    setStreamingAnswer('');
    
    try {
      const response = await fetch(`${API_URL}/books/${id}/ask_question_stream/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question })
      });
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullAnswer = '';
      let sources = [];
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line);
              if (data.type === 'word') {
                fullAnswer += data.content;
                setStreamingAnswer(fullAnswer);
              } else if (data.type === 'sources') {
                sources = data.content;
                setAnswer({ answer: fullAnswer, sources: sources });
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
      
      await fetchChatHistory();
      setQuestion('');
      setAnswer({ answer: fullAnswer, sources: sources });
      setStreamingAnswer('');
      
    } catch (error) {
      console.error('Streaming error:', error);
      askQuestionNonStream();
    } finally {
      setAnswering(false);
    }
  };

  const askQuestionNonStream = async () => {
    if (!question.trim()) return;
    
    setAnswering(true);
    try {
      const response = await axios.post(`${API_URL}/books/${id}/ask_question/`, {
        question: question
      });
      setAnswer(response.data);
      await fetchChatHistory();
      setQuestion('');
    } catch (error) {
      console.error('Error asking question:', error);
      alert('Failed to get answer. Please try again.');
    } finally {
      setAnswering(false);
    }
  };

  const askQuestion = () => {
    if (useStreaming) {
      askQuestionStream();
    } else {
      askQuestionNonStream();
    }
  };

  const getSentimentEmoji = (score) => {
    if (score > 0.5) return '😊 Very Positive';
    if (score > 0) return '🙂 Positive';
    if (score > -0.5) return '😐 Neutral';
    return '😞 Negative';
  };

  const getRatingStars = (rating) => {
    if (!rating || rating === 0) return null;
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const stars = [];
    for (let i = 0; i < fullStars; i++) stars.push('★');
    if (hasHalfStar) stars.push('½');
    return stars.join('');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex justify-center items-center transition-colors duration-300">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading book details...</p>
        </div>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex justify-center items-center transition-colors duration-300">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">Book not found</h2>
          <Link to="/" className="text-blue-600 dark:text-blue-400 hover:underline mt-4 inline-block">← Back to Library</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <Link to="/" className="text-blue-600 dark:text-blue-400 hover:underline inline-block">
            ← Back to Library
          </Link>
          <button
            onClick={toggleDarkMode}
            className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200"
          >
            {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>
        
        {/* Book Details Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 transition-colors duration-300">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">{book.title}</h1>
              <p className="text-xl text-gray-600 dark:text-gray-400">by {book.author}</p>
            </div>
            <div className="flex gap-2">
              {book.book_url && (
                <a
                  href={book.book_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-200"
                >
                  🔗 Source
                </a>
              )}
              <button
                onClick={deleteBook}
                className="px-4 py-2 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-800/50 transition-colors duration-200"
              >
                🗑️ Delete
              </button>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-4 mb-6">
            {book.rating > 0 && (
              <div className="flex items-center bg-yellow-100 dark:bg-yellow-900/50 px-3 py-1 rounded-full">
                <span className="text-yellow-600 dark:text-yellow-400 mr-1">★</span>
                <span className="font-semibold text-gray-700 dark:text-gray-300">{book.rating}</span>
                <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                  ({getRatingStars(book.rating)})
                </span>
              </div>
            )}
            {book.genre && book.genre !== 'Unclassified' && (
              <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 rounded-full">
                📚 {book.genre}
              </span>
            )}
            {book.sentiment_score !== 0 && (
              <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300 rounded-full">
                {getSentimentEmoji(book.sentiment_score)}
              </span>
            )}
          </div>
          
          {book.summary && (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">🤖 AI Summary</h2>
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-4 rounded-lg">
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{book.summary}</p>
              </div>
            </div>
          )}
          
          {book.description && book.description !== 'No description available' && (
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">📖 Description</h2>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{book.description}</p>
            </div>
          )}
        </div>

        {/* Recommendations Section - Shows ONLY NEW books from external sources */}
        {recommendations.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 transition-colors duration-300">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔍</span>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
                You Might Also Like
              </h2>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Based on your interest in <strong className="text-blue-600 dark:text-blue-400">"{book.title}"</strong>, 
              here are some similar books you might enjoy:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition hover:border-blue-300 dark:hover:border-blue-700"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="text-3xl">
                      {rec.genre === 'Fiction' ? '📖' : '📘'}
                    </div>
                    {rec.rating > 0 && (
                      <div className="flex items-center gap-1">
                        <span className="text-yellow-500 text-sm">★</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">{rec.rating}</span>
                      </div>
                    )}
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-base line-clamp-2">
                    {rec.title}
                  </h3>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">by {rec.author}</p>
                  {rec.genre && rec.genre !== 'Unclassified' && rec.genre !== 'General' && (
                    <span className="inline-block mt-2 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded">
                      {rec.genre}
                    </span>
                  )}
                  <button
                    onClick={() => addBookToLibrary(rec)}
                    disabled={addingBook === rec.title}
                    className="mt-3 w-full px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    {addingBook === rec.title ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                        Adding...
                      </>
                    ) : (
                      '📚 Add to Library'
                    )}
                  </button>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-4 text-center">
              ✨ These recommendations are from external sources and are not in your library yet
            </p>
          </div>
        )}

        {/* Q&A Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 transition-colors duration-300">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">💬 Ask Questions</h2>
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <input
                type="checkbox"
                checked={useStreaming}
                onChange={(e) => setUseStreaming(e.target.checked)}
                className="rounded"
              />
              <span>✨ Streaming response</span>
            </label>
          </div>
          
          <div className="flex gap-4 mb-6">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && askQuestion()}
              placeholder="e.g., What is the main theme? Who is the protagonist?"
              className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-colors duration-300"
            />
            <button
              onClick={askQuestion}
              disabled={answering}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
            >
              {answering ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  {useStreaming ? 'Streaming...' : 'Thinking...'}
                </>
              ) : (
                'Ask AI'
              )}
            </button>
          </div>
          
          {/* Answer Display */}
          {(answer || streamingAnswer) && (
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border-l-4 border-green-500">
              <h3 className="font-semibold text-lg mb-2 text-gray-900 dark:text-white flex items-center gap-2">
                <span>🤖 AI Answer</span>
                {answer?.cached && (
                  <span className="text-xs bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300 px-2 py-1 rounded">
                    📦 Cached
                  </span>
                )}
              </h3>
              <p className="text-gray-700 dark:text-gray-300 mb-3 leading-relaxed whitespace-pre-wrap">
                {useStreaming && streamingAnswer ? streamingAnswer : answer?.answer}
                {answering && useStreaming && <span className="animate-pulse"> ▌</span>}
              </p>
              {answer?.sources && answer.sources.length > 0 && (
                <div className="text-sm text-gray-500 dark:text-gray-400 mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                  <strong>📚 Sources:</strong>
                  <ul className="list-disc list-inside mt-1">
                    {answer.sources.map((source, idx) => (
                      <li key={idx}>{source}</li>
                    ))}
                  </ul>
                </div>
              )}
              {answer?.confidence && (
                <div className="mt-2 text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Confidence: </span>
                  <span className="font-semibold text-green-600 dark:text-green-400">
                    {(answer.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Chat History Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors duration-300">
          <div className="flex justify-between items-center mb-4">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2"
            >
              <span>📜 Chat History</span>
              <span className="text-sm text-gray-500 dark:text-gray-400">({chatHistory.length} messages)</span>
            </button>
            {chatHistory.length > 0 && (
              <button
                onClick={clearChatHistory}
                className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition"
              >
                Clear All
              </button>
            )}
          </div>
          
          {showHistory && (
            <div 
              ref={chatContainerRef}
              className="space-y-3 max-h-96 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-900/50"
            >
              {chatHistory.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                  No questions yet. Ask something about this book!
                </p>
              ) : (
                chatHistory.map((chat, idx) => (
                  <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2 bg-white dark:bg-gray-800 rounded-r-lg">
                    <p className="font-medium text-gray-800 dark:text-gray-200">
                      <span className="text-blue-600 dark:text-blue-400">Q:</span> {chat.question}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
                      <span className="text-green-600 dark:text-green-400">A:</span> {chat.answer.substring(0, 200)}
                      {chat.answer.length > 200 && '...'}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {new Date(chat.created_at).toLocaleString()}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BookDetail;