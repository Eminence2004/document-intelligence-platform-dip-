from rest_framework import serializers
from .models import Book, BookChunk, ChatHistory

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class BookDetailSerializer(serializers.ModelSerializer):
    chunks_count = serializers.IntegerField(source='chunks.count', read_only=True)
    
    class Meta:
        model = Book
        fields = '__all__'

class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'question', 'answer', 'sources', 'created_at']

class QuestionRequestSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    question = serializers.CharField(max_length=1000)