// src/components/BookList.jsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import ConfirmModal from './ConfirmModal';

const BookList = () => {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [bookToDelete, setBookToDelete] = useState(null);

  const API_URL = 'http://localhost:8000/api';

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    fetchBooks();
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode === 'true') {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    } else {
      setDarkMode(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

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

  const fetchBooks = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/books/`);
      if (Array.isArray(response.data)) {
        setBooks(response.data);
      } else if (response.data.results) {
        setBooks(response.data.results);
      } else {
        setBooks([]);
      }
    } catch (err) {
      console.error('Error fetching books:', err);
      showToast('Failed to load books. Make sure backend is running on port 8000', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!inputValue.trim()) {
      showToast('Please enter a book title, ISBN, or URL', 'warning');
      return;
    }

    setUploading(true);
    
    try {
      const response = await axios.post(`${API_URL}/books/upload_book/`, { 
        url: inputValue.trim() 
      });
      
      const bookTitle = response.data.book?.title || response.data.title;
      showToast(`✨ "${bookTitle}" has been added to your library!`, 'success');
      setInputValue('');
      await fetchBooks();
      
    } catch (err) {
      console.error('Error uploading book:', err);
      
      if (err.response?.status === 409 && err.response?.data?.duplicate) {
        const existingBook = err.response.data.existing_book;
        showToast(`⚠️ "${existingBook.title}" is already in your library!`, 'warning');
      } else {
        showToast(err.response?.data?.error || 'Failed to upload book. Try using a book title or ISBN.', 'error');
      }
    } finally {
      setUploading(false);
    }
  };

  const openDeleteModal = (bookId, bookTitle) => {
    setBookToDelete({ id: bookId, title: bookTitle });
    setModalOpen(true);
  };

  const confirmDelete = async () => {
    if (bookToDelete) {
      try {
        await axios.delete(`${API_URL}/books/${bookToDelete.id}/`);
        showToast(`🗑️ "${bookToDelete.title}" has been deleted from your library`, 'success');
        await fetchBooks();
      } catch (err) {
        console.error('Error deleting book:', err);
        showToast('Failed to delete book. Please try again.', 'error');
      } finally {
        setModalOpen(false);
        setBookToDelete(null);
      }
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setBookToDelete(null);
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

  // Toast Component inline
  const ToastNotification = () => {
    if (!toast) return null;
    
    const getIcon = () => {
      switch (toast.type) {
        case 'success': return '✅';
        case 'error': return '❌';
        case 'warning': return '⚠️';
        default: return 'ℹ️';
      }
    };
    
    const getColors = () => {
      switch (toast.type) {
        case 'success': return 'bg-green-500 dark:bg-green-600';
        case 'error': return 'bg-red-500 dark:bg-red-600';
        case 'warning': return 'bg-yellow-500 dark:bg-yellow-600';
        default: return 'bg-blue-500 dark:bg-blue-600';
      }
    };
    
    return (
      <div className="fixed top-20 right-4 z-50 animate-slide-in">
        <div className={`${getColors()} text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 min-w-[300px]`}>
          <span className="text-xl">{getIcon()}</span>
          <p className="flex-1 text-sm font-medium">{toast.message}</p>
          <button onClick={() => setToast(null)} className="hover:opacity-70">✕</button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex justify-center items-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading books...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-300">
      <ToastNotification />
      
      <ConfirmModal
        isOpen={modalOpen}
        onClose={closeModal}
        onConfirm={confirmDelete}
        title="Delete Book"
        message={`Are you sure you want to delete "${bookToDelete?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
      />
      
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              📚 AI-Powered Book Insights
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Upload books by title, ISBN, or URL and ask intelligent questions
            </p>
          </div>
          <button
            onClick={toggleDarkMode}
            className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>

        {/* Upload Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            📖 Add New Book
          </h2>
          <div className="flex flex-col md:flex-row gap-4">
            <input
              type="text"
              placeholder="Enter book title, ISBN, or URL (e.g., The Psychology of Money or 9780593714027)"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleUpload()}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Processing...
                </>
              ) : (
                '➕ Add Book'
              )}
            </button>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-3">
            💡 Try: "The Psychology of Money" or "9780593714027"
          </p>
        </div>

        {/* Books Grid */}
        {books.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-12 text-center">
            <div className="text-6xl mb-4">📚</div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Books Yet</h3>
            <p className="text-gray-600 dark:text-gray-400">Add your first book using the form above!</p>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
                Your Library ({books.length} books)
              </h2>
              <button onClick={fetchBooks} className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                🔄 Refresh
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {books.map((book) => (
                <div key={book.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-all duration-300 relative group">
                  <Link to={`/book/${book.id}`} className="block p-6">
                    <div className="flex justify-between items-start mb-3">
                      <div className="text-3xl">{book.genre === 'Fiction' ? '📖' : '📘'}</div>
                      <button
                        onClick={(e) => { 
                          e.preventDefault(); 
                          openDeleteModal(book.id, book.title);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
                      >
                        🗑️
                      </button>
                    </div>
                    
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
                      {book.title}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-2">by {book.author}</p>
                    
                    {book.rating > 0 && (
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex text-yellow-500 text-sm">{getRatingStars(book.rating)}</div>
                        <span className="text-sm text-gray-500 dark:text-gray-400">({book.rating})</span>
                      </div>
                    )}
                    
                    {book.genre && book.genre !== 'Unclassified' && (
                      <span className="inline-block px-2 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 text-xs rounded-full mb-2">
                        {book.genre}
                      </span>
                    )}
                    
                    <div className="mt-4 text-blue-600 dark:text-blue-400 text-sm font-medium">
                      Ask Questions →
                    </div>
                  </Link>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default BookList;