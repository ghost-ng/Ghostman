"""
LangChain Integration with Unified Session Manager

Custom LangChain components that use Ghostman's unified session manager
instead of making direct network requests.
"""

import logging
import json
from typing import List, Dict, Any, Optional, AsyncIterator
import numpy as np

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLLM
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import LLMResult, Generation
from pydantic import Field

# Import unified session manager
try:
    from ..ai.session_manager import session_manager
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False
    session_manager = None

logger = logging.getLogger("ghostman.unified_session_langchain")


class UnifiedSessionOpenAIEmbeddings(Embeddings):
    """
    OpenAI Embeddings implementation using Ghostman's unified session manager.
    
    This ensures all OpenAI API calls go through your centralized session management
    rather than making direct unauthorized requests.
    """
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_endpoint: str = "https://api.openai.com/v1",
        max_retries: int = 3,
        timeout: float = 30.0,
        dimensions: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Store configuration as private variables to avoid Pydantic conflicts
        self._model = model
        self._api_endpoint = api_endpoint
        self._max_retries = max_retries
        self._timeout = timeout
        self._dimensions = dimensions
        
        if not SESSION_MANAGER_AVAILABLE or not session_manager:
            raise RuntimeError("Unified session manager not available")
        
        self._session_manager = session_manager
        logger.info(f"Initialized UnifiedSessionOpenAIEmbeddings with {self._model}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs using unified session manager."""
        return self._embed_texts(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text using unified session manager."""
        result = self._embed_texts([text])
        return result[0] if result else []
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Internal method to embed texts using session manager."""
        if not texts:
            return []
        
        try:
            # Prepare request payload
            payload = {
                "input": texts,
                "model": self._model
            }
            
            # Add dimensions if specified (for text-embedding-3 models)
            if self._dimensions:
                payload["dimensions"] = self._dimensions
            
            # Make request through unified session manager
            response = self._session_manager.make_request(
                method="POST",
                url=f"{self._api_endpoint}/embeddings",
                json=payload,
                timeout=self._timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Embedding API error: {response.status_code} - {response.text}")
                # Return zero embeddings as fallback
                dim = self._dimensions or 1536
                return [[0.0] * dim for _ in texts]
            
            # Parse response
            data = response.json()
            embeddings = []
            
            for item in data.get("data", []):
                embedding = item.get("embedding", [])
                embeddings.append(embedding)
            
            if len(embeddings) != len(texts):
                logger.warning(f"Expected {len(texts)} embeddings, got {len(embeddings)}")
                # Pad with zero embeddings if needed
                dim = len(embeddings[0]) if embeddings else (self.dimensions or 1536)
                while len(embeddings) < len(texts):
                    embeddings.append([0.0] * dim)
            
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Return zero embeddings as fallback
            dim = self._dimensions or 1536
            return [[0.0] * dim for _ in texts]


class UnifiedSessionChatOpenAI(LLM):
    """
    ChatOpenAI implementation using Ghostman's unified session manager.
    
    Ensures all ChatGPT API calls go through centralized session management.
    """
    
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        api_endpoint: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        timeout: float = 60.0,
        **kwargs
    ):
        # Initialize with model parameter for LangChain ChatOpenAI compatibility
        super().__init__(model=model_name, **kwargs)
        
        # Store parameters as private variables to avoid Pydantic field conflicts
        self._model_name = model_name
        self._api_endpoint = api_endpoint
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._top_p = top_p
        self._frequency_penalty = frequency_penalty
        self._presence_penalty = presence_penalty
        self._timeout = timeout
        
        if not SESSION_MANAGER_AVAILABLE or not session_manager:
            raise RuntimeError("Unified session manager not available")
        
        self._session_manager = session_manager
        logger.info(f"Initialized UnifiedSessionChatOpenAI with {self._model_name}")
    
    @property
    def _llm_type(self) -> str:
        return "unified_session_openai"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the LLM using unified session manager."""
        
        # Convert prompt to messages format
        messages = [{"role": "user", "content": prompt}]
        
        return self._call_with_messages(messages, stop, run_manager, **kwargs)
    
    def _call_with_messages(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call with messages format using unified session manager."""
        
        try:
            # Prepare request payload
            payload = {
                "model": self._model_name,
                "messages": messages,
                "temperature": self._temperature,
                "max_tokens": self._max_tokens,
                "top_p": self._top_p,
                "frequency_penalty": self._frequency_penalty,
                "presence_penalty": self._presence_penalty,
            }
            
            # Add stop sequences if provided
            if stop:
                payload["stop"] = stop
            
            # Make request through unified session manager
            response = self._session_manager.make_request(
                method="POST",
                url=f"{self._api_endpoint}/chat/completions",
                json=payload,
                timeout=self._timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Chat API error: {response.status_code} - {response.text}")
                return f"Error: Failed to get response from LLM (status: {response.status_code})"
            
            # Parse response
            data = response.json()
            
            if "choices" not in data or not data["choices"]:
                logger.error("No choices in API response")
                return "Error: No response generated"
            
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "").strip()
            
            # Handle streaming tokens through callback manager
            if run_manager and content:
                # Simulate token streaming by splitting response
                tokens = content.split()
                for token in tokens:
                    run_manager.on_llm_new_token(token + " ")
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to call LLM: {e}")
            return f"Error: {str(e)}"
    
    def stream_with_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[callable] = None
    ) -> str:
        """Stream response with messages (custom method for streaming)."""
        
        try:
            # Prepare streaming request payload
            payload = {
                "model": self._model_name,
                "messages": messages,
                "temperature": self._temperature,
                "max_tokens": self._max_tokens,
                "top_p": self._top_p,
                "frequency_penalty": self._frequency_penalty,
                "presence_penalty": self._presence_penalty,
                "stream": True
            }
            
            # Make streaming request through unified session manager
            # Note: This assumes session manager supports streaming
            # If not, fall back to regular call and simulate streaming
            
            try:
                # Try streaming first
                response = self._session_manager.make_request(
                    method="POST",
                    url=f"{self._api_endpoint}/chat/completions",
                    json=payload,
                    timeout=self._timeout,
                    stream=True
                )
                
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            data_str = line_text[6:]
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                chunk_data = json.loads(data_str)
                                if 'choices' in chunk_data and chunk_data['choices']:
                                    delta = chunk_data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        full_response += content
                                        if callback:
                                            callback(content)
                            except json.JSONDecodeError:
                                continue
                
                return full_response
                
            except Exception as stream_error:
                logger.debug(f"Streaming failed, falling back to regular call: {stream_error}")
                
                # Fall back to regular call and simulate streaming
                regular_response = self._call_with_messages(messages)
                
                if callback:
                    # Simulate streaming by sending chunks
                    import time
                    words = regular_response.split()
                    for i, word in enumerate(words):
                        chunk = word + (" " if i < len(words) - 1 else "")
                        callback(chunk)
                        time.sleep(0.01)  # Small delay for visual effect
                
                return regular_response
                
        except Exception as e:
            logger.error(f"Failed to stream LLM response: {e}")
            return f"Error: {str(e)}"


class UnifiedSessionLangChainRAGPipeline:
    """
    Modified RAG pipeline that uses unified session manager instead of direct API calls.
    """
    
    def __init__(
        self,
        persist_directory: str = "./faiss_langchain_db",
        collection_name: str = "ghostman_documents",
        model_name: str = "gpt-3.5-turbo",
        embedding_model: str = "text-embedding-3-small",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """Initialize unified session RAG pipeline."""
        
        if not SESSION_MANAGER_AVAILABLE:
            raise RuntimeError("Unified session manager not available")
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize unified session embeddings (NO DIRECT API CALLS)
        logger.info(f"Initializing Unified Session Embeddings with {embedding_model}")
        self.embeddings = UnifiedSessionOpenAIEmbeddings(
            model=embedding_model,
            dimensions=1536 if "small" in embedding_model else 3072
        )
        
        # Initialize Chroma Vector Store
        from langchain_community.vectorstores import FAISS
        logger.info(f"Initializing Chroma vector store at {persist_directory}")
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        
        # Initialize unified session LLM (NO DIRECT API CALLS)
        logger.info(f"Initializing Unified Session ChatOpenAI with {model_name}")
        self.llm = UnifiedSessionChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Initialize text splitter
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Conversation chains and memories (per conversation)
        self.conversation_chains = {}
        self.conversation_memories = {}
        
        logger.info("Unified Session LangChain RAG Pipeline initialized successfully")
    
    def add_documents(self, file_paths: List[str], conversation_id: Optional[str] = None) -> List[str]:
        """Add documents using the existing pipeline logic but with unified session."""
        from langchain_community.document_loaders import TextLoader
        from langchain.schema import Document
        from pathlib import Path
        from datetime import datetime
        
        all_documents = []
        
        for file_path in file_paths:
            try:
                # Load document
                path = Path(file_path)
                extension = path.suffix.lower()
                
                if extension == '.txt':
                    loader = TextLoader(file_path, encoding='utf-8')
                    documents = loader.load()
                else:
                    # Fallback: read as plain text
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    doc = Document(
                        page_content=content,
                        metadata={"source": str(file_path), "filename": path.name}
                    )
                    documents = [doc]
                
                # Add metadata
                for doc in documents:
                    doc.metadata["added_at"] = datetime.now().isoformat()
                    if conversation_id:
                        doc.metadata["conversation_id"] = conversation_id
                    doc.metadata["file_path"] = file_path
                
                all_documents.extend(documents)
                
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {e}")
        
        if not all_documents:
            return []
        
        # Split documents into chunks
        splits = self.text_splitter.split_documents(all_documents)
        
        # Add to vector store (this will use our unified session embeddings)
        ids = self.vector_store.add_documents(documents=splits)
        
        logger.info(f"Added {len(ids)} document chunks to vector store using unified session")
        return ids
    
    def query_with_unified_session(
        self,
        conversation_id: str,
        question: str,
        streaming_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Query using unified session (no direct API calls)."""
        
        try:
            # Get retriever
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4}
            )
            
            # Retrieve relevant documents
            docs = retriever.get_relevant_documents(question)
            
            # Assemble context
            context_parts = []
            for i, doc in enumerate(docs):
                context_parts.append(f"Source {i+1}:\n{doc.page_content}")
            
            context = "\n\n".join(context_parts)
            
            # Build messages for conversation
            if conversation_id not in self.conversation_memories:
                self.conversation_memories[conversation_id] = []
            
            chat_history = self.conversation_memories[conversation_id]
            
            # Create system message with context
            system_message = {
                "role": "system",
                "content": f"You are an assistant that answers questions using the provided context. Context:\n\n{context}"
            }
            
            # Build messages array
            messages = [system_message]
            
            # Add recent chat history
            for msg in chat_history[-6:]:  # Last 6 messages
                messages.append(msg)
            
            # Add current question
            messages.append({"role": "user", "content": question})
            
            # Generate response using unified session
            if streaming_callback:
                answer = self.llm.stream_with_messages(messages, streaming_callback)
            else:
                answer = self.llm._call_with_messages(messages)
            
            # Update chat history
            chat_history.append({"role": "user", "content": question})
            chat_history.append({"role": "assistant", "content": answer})
            
            # Keep history manageable
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]
            
            self.conversation_memories[conversation_id] = chat_history
            
            return {
                "answer": answer,
                "source_documents": docs,
                "chat_history": chat_history,
                "context_used": context
            }
            
        except Exception as e:
            logger.error(f"Query with unified session failed: {e}")
            return {
                "answer": f"I encountered an error: {str(e)}",
                "source_documents": [],
                "error": str(e)
            }
    
    def remove_documents_by_ids(self, document_ids: List[str]) -> bool:
        """Remove documents from the vector store by their IDs."""
        try:
            if not document_ids:
                logger.warning("No document IDs provided for removal")
                return False
            
            # Delete documents from Chroma vector store
            self.vector_store.delete(ids=document_ids)
            
            logger.info(f"Successfully removed {len(document_ids)} documents from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove documents {document_ids}: {e}")
            return False
    
    def remove_documents_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[str]:
        """Remove documents by metadata filter and return removed IDs."""
        try:
            # Get all documents to filter by metadata
            collection_data = self.vector_store._collection.get()
            
            ids_to_remove = []
            for idx, metadata in enumerate(collection_data['metadatas']):
                # Check if metadata matches filter
                match = True
                for key, value in metadata_filter.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                
                if match:
                    ids_to_remove.append(collection_data['ids'][idx])
            
            if ids_to_remove:
                success = self.remove_documents_by_ids(ids_to_remove)
                if success:
                    logger.info(f"Removed {len(ids_to_remove)} documents matching metadata filter")
                    return ids_to_remove
            else:
                logger.info("No documents found matching metadata filter")
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to remove documents by metadata {metadata_filter}: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection = self.vector_store._collection
            return {
                "name": self.collection_name,
                "count": collection.count(),
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {"error": str(e), "name": self.collection_name}