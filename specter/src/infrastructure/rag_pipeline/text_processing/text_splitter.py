"""
Text Splitter for RAG Pipeline

Comprehensive text splitting with multiple strategies:
- LangChain integration for advanced splitting
- Recursive character text splitter
- Sentence-based splitting
- Token-based splitting with tiktoken
- Code-aware splitting
- Markdown structure preservation
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from abc import ABC, abstractmethod

try:
    from langchain.text_splitter import (
        RecursiveCharacterTextSplitter,
        TokenTextSplitter,
        MarkdownHeaderTextSplitter,
        Language,
        RecursiveCharacterTextSplitter
    )
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from ..config.rag_config import TextProcessingConfig, TextSplitterType

logger = logging.getLogger("specter.text_splitter")


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def length(self) -> int:
        return len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'chunk_index': self.chunk_index,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'token_count': self.token_count,
            'metadata': self.metadata
        }


class BaseTextSplitter(ABC):
    """Base class for text splitters."""
    
    def __init__(self, config: TextProcessingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def split_text(self, text: str) -> List[TextChunk]:
        """Split text into chunks."""
        pass
    
    def _create_chunk(self, content: str, index: int, start: int, end: int, 
                     metadata: Optional[Dict[str, Any]] = None) -> TextChunk:
        """Create a text chunk with metadata."""
        chunk = TextChunk(
            content=content.strip(),
            chunk_index=index,
            start_char=start,
            end_char=end,
            metadata=metadata or {}
        )
        
        # Add token count if possible
        if TIKTOKEN_AVAILABLE and self.config.length_function == "tiktoken":
            try:
                encoding = tiktoken.get_encoding(self.config.tokenizer_name)
                chunk.token_count = len(encoding.encode(chunk.content))
            except Exception as e:
                self.logger.warning(f"Token counting failed: {e}")
        
        return chunk


class RecursiveTextSplitter(BaseTextSplitter):
    """Recursive character text splitter with LangChain integration."""
    
    def __init__(self, config: TextProcessingConfig):
        super().__init__(config)
        self.separators = ["\n\n", "\n", " ", ""]
        
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain package is required for recursive character splitting. Install langchain to use this splitter.")
        self._setup_langchain_splitter()
    
    def _setup_langchain_splitter(self):
        """Setup LangChain recursive character text splitter."""
        length_function = len
        
        if self.config.length_function == "tiktoken" and TIKTOKEN_AVAILABLE:
            try:
                encoding = tiktoken.get_encoding(self.config.tokenizer_name)
                length_function = lambda x: len(encoding.encode(x))
            except Exception as e:
                logger.warning(f"Failed to setup tiktoken length function: {e}")
        
        self.langchain_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=length_function,
            separators=self.separators,
            keep_separator=True,
            is_separator_regex=False
        )
    
    def split_text(self, text: str) -> List[TextChunk]:
        """Split text using recursive character splitting."""
        if LANGCHAIN_AVAILABLE:
            return self._split_with_langchain(text)
        else:
            return self._split_fallback(text)
    
    def _split_with_langchain(self, text: str) -> List[TextChunk]:
        """Split using LangChain splitter."""
        text_chunks = self.langchain_splitter.split_text(text)
        
        chunks = []
        current_pos = 0
        
        for i, chunk_text in enumerate(text_chunks):
            # Find the position in the original text
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                # Fallback - use current position
                start_pos = current_pos
            
            end_pos = start_pos + len(chunk_text)
            
            chunk = self._create_chunk(chunk_text, i, start_pos, end_pos)
            chunks.append(chunk)
            
            current_pos = end_pos - self.config.chunk_overlap
        
        return chunks
    
    def _split_fallback(self, text: str) -> List[TextChunk]:
        """Fallback splitting implementation."""
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # Determine chunk end position
            end_pos = min(current_pos + self.config.chunk_size, len(text))
            
            # Try to split at a good boundary
            chunk_text = text[current_pos:end_pos]
            
            # If we're not at the end and chunk_size allows, try to break at separator
            if end_pos < len(text) and len(chunk_text) >= self.config.chunk_size:
                for separator in self.separators:
                    if separator in chunk_text:
                        # Find the last occurrence of separator
                        last_sep = chunk_text.rfind(separator)
                        if last_sep > len(chunk_text) // 2:  # Don't break too early
                            end_pos = current_pos + last_sep + len(separator)
                            chunk_text = text[current_pos:end_pos]
                            break
            
            if chunk_text.strip():
                chunk = self._create_chunk(chunk_text, chunk_index, current_pos, end_pos)
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position with overlap
            current_pos = end_pos - self.config.chunk_overlap
            if current_pos >= end_pos:
                current_pos = end_pos
        
        return chunks


class SentenceTextSplitter(BaseTextSplitter):
    """Sentence-based text splitter."""
    
    def __init__(self, config: TextProcessingConfig):
        super().__init__(config)
        # Simple sentence splitting regex
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')
    
    def split_text(self, text: str) -> List[TextChunk]:
        """Split text by sentences."""
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        start_pos = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if (current_length + sentence_length > self.config.chunk_size and 
                current_chunk and 
                current_length >= self.config.sentence_min_length):
                
                # Create chunk from current sentences
                chunk_text = ' '.join(current_chunk)
                end_pos = start_pos + len(chunk_text)
                
                chunk = self._create_chunk(chunk_text, chunk_index, start_pos, end_pos)
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
                start_pos = end_pos - sum(len(s) for s in overlap_sentences)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining sentences as final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            end_pos = start_pos + len(chunk_text)
            chunk = self._create_chunk(chunk_text, chunk_index, start_pos, end_pos)
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = self.sentence_pattern.split(text)
        
        # Filter out empty sentences and apply length constraints
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if (sentence and 
                len(sentence) >= self.config.sentence_min_length and
                len(sentence) <= self.config.sentence_max_length):
                filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get sentences for overlap."""
        overlap_chars = self.config.chunk_overlap
        overlap_sentences = []
        chars_count = 0
        
        # Take sentences from the end until we reach overlap size
        for sentence in reversed(sentences):
            if chars_count + len(sentence) <= overlap_chars:
                overlap_sentences.insert(0, sentence)
                chars_count += len(sentence)
            else:
                break
        
        return overlap_sentences


class TokenTextSplitter(BaseTextSplitter):
    """Token-based text splitter using tiktoken."""
    
    def __init__(self, config: TextProcessingConfig):
        super().__init__(config)
        
        if not TIKTOKEN_AVAILABLE:
            raise ValueError("tiktoken not available - required for token-based splitting")
        
        try:
            self.encoding = tiktoken.get_encoding(self.config.tokenizer_name)
        except Exception as e:
            logger.warning(f"Failed to load tokenizer {self.config.tokenizer_name}: {e}")
            self.encoding = tiktoken.get_encoding("cl100k_base")  # fallback
    
    def split_text(self, text: str) -> List[TextChunk]:
        """Split text based on token count."""
        # Encode the entire text
        tokens = self.encoding.encode(text)
        
        chunks = []
        chunk_index = 0
        
        for i in range(0, len(tokens), self.config.chunk_size - self.config.chunk_overlap):
            # Get chunk tokens
            chunk_tokens = tokens[i:i + self.config.chunk_size]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            if chunk_text.strip():
                # Find positions in original text (approximate)
                start_pos = len(self.encoding.decode(tokens[:i])) if i > 0 else 0
                end_pos = start_pos + len(chunk_text)
                
                chunk = self._create_chunk(chunk_text, chunk_index, start_pos, end_pos)
                chunk.token_count = len(chunk_tokens)
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks


class CodeTextSplitter(BaseTextSplitter):
    """Code-aware text splitter that preserves structure."""
    
    def __init__(self, config: TextProcessingConfig):
        super().__init__(config)
        
        # Language-specific patterns
        self.language_patterns = {
            'python': {
                'class': re.compile(r'^class\s+\w+.*?:', re.MULTILINE),
                'function': re.compile(r'^def\s+\w+.*?:', re.MULTILINE),
                'import': re.compile(r'^(?:from\s+\S+\s+)?import\s+.+', re.MULTILINE)
            },
            'javascript': {
                'function': re.compile(r'(?:function\s+\w+|const\s+\w+\s*=.*?=>)', re.MULTILINE),
                'class': re.compile(r'class\s+\w+.*?{', re.MULTILINE),
                'import': re.compile(r'import\s+.+', re.MULTILINE)
            }
        }
    
    def split_text(self, text: str) -> List[TextChunk]:
        """Split code while preserving logical structure."""
        # Try to detect language
        language = self._detect_language(text)
        
        if language and language in self.language_patterns:
            return self._split_by_structure(text, language)
        else:
            # Fallback to line-based splitting with indentation awareness
            return self._split_by_lines(text)
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect programming language from text content."""
        # Simple heuristic-based detection
        if re.search(r'def\s+\w+.*?:', text):
            return 'python'
        elif re.search(r'function\s+\w+.*?{', text):
            return 'javascript'
        return None
    
    def _split_by_structure(self, text: str, language: str) -> List[TextChunk]:
        """Split by code structure (functions, classes, etc.)."""
        patterns = self.language_patterns[language]
        lines = text.split('\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        start_line = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line starts a new structure
            is_structure_start = any(pattern.match(line) for pattern in patterns.values())
            
            if (is_structure_start and current_chunk and 
                current_length + len(line) > self.config.chunk_size):
                
                # Create chunk from current lines
                chunk_text = '\n'.join(current_chunk)
                start_char = sum(len(lines[j]) + 1 for j in range(start_line)) 
                end_char = start_char + len(chunk_text)
                
                chunk = self._create_chunk(chunk_text, chunk_index, start_char, end_char, 
                                         {'language': language})
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk
                current_chunk = []
                current_length = 0
                start_line = i
            
            current_chunk.append(line)
            current_length += len(line) + 1  # +1 for newline
            i += 1
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            start_char = sum(len(lines[j]) + 1 for j in range(start_line))
            end_char = start_char + len(chunk_text)
            
            chunk = self._create_chunk(chunk_text, chunk_index, start_char, end_char,
                                     {'language': language})
            chunks.append(chunk)
        
        return chunks
    
    def _split_by_lines(self, text: str) -> List[TextChunk]:
        """Split by lines with indentation awareness."""
        lines = text.split('\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        start_line = 0
        
        for i, line in enumerate(lines):
            # If adding this line would exceed chunk size
            if current_length + len(line) > self.config.chunk_size and current_chunk:
                
                chunk_text = '\n'.join(current_chunk)
                start_char = sum(len(lines[j]) + 1 for j in range(start_line))
                end_char = start_char + len(chunk_text)
                
                chunk = self._create_chunk(chunk_text, chunk_index, start_char, end_char)
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with some overlap
                overlap_lines = max(1, self.config.chunk_overlap // 50)  # rough line estimate
                current_chunk = current_chunk[-overlap_lines:] + [line]
                current_length = sum(len(l) + 1 for l in current_chunk)
                start_line = i - overlap_lines
            else:
                current_chunk.append(line)
                current_length += len(line) + 1
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            start_char = sum(len(lines[j]) + 1 for j in range(start_line))
            end_char = start_char + len(chunk_text)
            
            chunk = self._create_chunk(chunk_text, chunk_index, start_char, end_char)
            chunks.append(chunk)
        
        return chunks


class TextSplitterFactory:
    """Factory for creating text splitters based on configuration."""
    
    @staticmethod
    def create_splitter(config: TextProcessingConfig) -> BaseTextSplitter:
        """Create appropriate text splitter based on configuration."""
        
        if config.splitter_type == TextSplitterType.RECURSIVE_CHARACTER:
            if not LANGCHAIN_AVAILABLE:
                raise ImportError("RecursiveCharacterTextSplitter requires langchain package. Please install langchain.")
            return RecursiveTextSplitter(config)
        elif config.splitter_type == TextSplitterType.SENTENCE:
            return SentenceTextSplitter(config)
        elif config.splitter_type == TextSplitterType.TOKEN:
            return TokenTextSplitter(config)
        elif config.splitter_type == TextSplitterType.CODE:
            return CodeTextSplitter(config)
        else:
            raise ValueError(f"Unsupported splitter type: {config.splitter_type}")


def split_text(text: str, config: TextProcessingConfig) -> List[TextChunk]:
    """Convenience function to split text using configuration."""
    splitter = TextSplitterFactory.create_splitter(config)
    return splitter.split_text(text)