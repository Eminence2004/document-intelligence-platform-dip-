# 📚 Document Intelligence Platform

A full-stack web application with AI/RAG integration that processes book data and enables intelligent querying.

## 🎯 Features

### Core Features
- ✅ **Automated Book Scraping** - Collect book data from OpenLibrary API and Goodreads
- ✅ **AI-Powered Insights** - Generate summaries, genre classification, and sentiment analysis
- ✅ **RAG Pipeline** - Complete Retrieval-Augmented Generation for intelligent Q&A
- ✅ **Vector Search** - FAISS/ChromaDB for semantic similarity search
- ✅ **Smart Chunking** - Semantic, sliding window, and paragraph chunking with overlap

### Bonus Features
- ✅ **Caching** - AI response caching to reduce latency
- ✅ **Streaming Responses** - Word-by-word answer streaming
- ✅ **Chat History** - Per-book conversation storage
- ✅ **Dark Mode** - Toggle between light and dark themes
- ✅ **Toast Notifications** - Beautiful UI notifications
- ✅ **Custom Modals** - Confirmation dialogs instead of browser alerts

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | Django REST Framework, Python |
| **Database** | MySQL (metadata), FAISS/ChromaDB (vectors) |
| **Frontend** | ReactJS, Tailwind CSS |
| **AI/LLM** | LM Studio (local LLM hosting) |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2) |
| **Automation** | Selenium, OpenLibrary API |

## 📋 Prerequisites

- Python 3.10+
- Node.js 16+
- MySQL 8.0+
- LM Studio (for local LLM)
- Chrome browser (for Selenium)

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Eminence2004/document-intelligence-platform-dip-.git
cd document-intelligence-platform-dip-