# Document Intelligence Platform

A full-stack web application with AI/RAG integration that processes book data and enables intelligent querying.

## Features

✅ Automated book scraping from Goodreads
✅ AI-generated insights (summaries, genre classification, sentiment analysis)
✅ Intelligent book recommendations
✅ RAG pipeline for question answering with source citations
✅ Vector similarity search using ChromaDB
✅ Smart chunking strategies (semantic, sliding window, paragraph)
✅ Response caching for improved performance
✅ Chat history saving
✅ Bulk scraping support

## Tech Stack

- **Backend**: Django REST Framework, Python
- **Database**: MySQL, ChromaDB (vectors)
- **Frontend**: ReactJS, Tailwind CSS
- **AI**: LM Studio (local LLM) / OpenAI API
- **Automation**: Selenium, BeautifulSoup

## Setup Instructions

### Prerequisites

1. Python 3.8+
2. Node.js 14+
3. MySQL
4. Chrome browser (for Selenium)

### Backend Setup

```bash
# Clone repository
git clone https://github.com/Eminence2004/document-intelligence-platform-dip-.git
cd document-intelligence-platform-dip-/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup MySQL database
mysql -u root -p
CREATE DATABASE book_intelligence;
exit;

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start Django server
python manage.py runserver 8000