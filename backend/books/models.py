from django.db import models
from django.utils import timezone

class Book(models.Model):
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    book_url = models.URLField(max_length=1000, blank=True)
    cover_image = models.URLField(max_length=1000, blank=True)
    genre = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True, null=True)
    sentiment_score = models.FloatField(default=0.0)
    published_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class BookChunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chunks')
    chunk_text = models.TextField()
    chunk_index = models.IntegerField()
    embedding_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        unique_together = ['book', 'chunk_index']

class ChatHistory(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chats')
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Q: {self.question[:50]}..."