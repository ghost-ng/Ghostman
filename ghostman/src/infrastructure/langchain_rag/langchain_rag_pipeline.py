"""
LangChain-based RAG Pipeline with Conversation History

Proper implementation using LangChain components:
- OpenAIEmbeddings for vector embeddings
- Chroma for vector storage
- ConversationalRetrievalChain for chat with history
- Document loaders and text splitters
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

# LangChain imports
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    CSVLoader,
    JSONLoader,
    UnstructuredHTMLLoader
)
from langchain.schema import Document
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler

# For the new recommended approach
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger("ghostman.langchain_rag")


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses."""
    
    def __init__(self, callback_func=None):
        self.callback_func = callback_func
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Run on new LLM token."""
        if self.callback_func:
            self.callback_func(token)


class LangChainRAGPipeline:
    """
    Complete RAG pipeline using LangChain components.
    
    Features:
    - OpenAI embeddings with text-embedding-3-large
    - Chroma vector store with persistence
    - Conversation memory management
    - Multiple document format support
    - Streaming response support
    """
    
    def __init__(
        self,
        persist_directory: str = "./chroma_langchain_db",
        collection_name: str = "ghostman_documents",
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4",
        embedding_model: str = "text-embedding-3-large",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        Initialize LangChain RAG pipeline.
        
        Args:
            persist_directory: Directory for Chroma persistence
            collection_name: Name of the Chroma collection
            openai_api_key: OpenAI API key (uses env var if not provided)
            model_name: OpenAI model to use for generation
            embedding_model: OpenAI embedding model
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            temperature: LLM temperature
            max_tokens: Maximum tokens for response
        """
        # Set API key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        elif not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize OpenAI Embeddings
        logger.info(f"Initializing OpenAI Embeddings with {embedding_model}")
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            # You can specify dimensions for text-embedding-3 models
            # dimensions=1536  # Optional: reduce dimensions for efficiency
        )
        
        # Initialize Chroma Vector Store
        logger.info(f"Initializing Chroma vector store at {persist_directory}")
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        
        # Initialize OpenAI Chat Model
        logger.info(f"Initializing ChatOpenAI with {model_name}")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True  # Enable streaming
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Conversation chains storage (per conversation)
        self.conversation_chains: Dict[str, ConversationalRetrievalChain] = {}
        self.conversation_memories: Dict[str, ConversationBufferMemory] = {}
        
        logger.info("LangChain RAG Pipeline initialized successfully")
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        Load a document using appropriate loader.
        
        Args:
            file_path: Path to the document
            
        Returns:
            List of Document objects
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        try:
            if extension == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif extension == '.pdf':
                loader = PyPDFLoader(file_path)
            elif extension == '.md':
                loader = UnstructuredMarkdownLoader(file_path)
            elif extension == '.csv':
                loader = CSVLoader(file_path)
            elif extension == '.json':
                loader = JSONLoader(file_path, jq_schema='.', text_content=False)
            elif extension in ['.html', '.htm']:
                loader = UnstructuredHTMLLoader(file_path)
            else:
                # Default to text loader
                loader = TextLoader(file_path, encoding='utf-8')
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents from {file_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load document {file_path}: {e}")
            # Fallback: try to read as plain text
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
                doc = Document(
                    page_content=content,
                    metadata={"source": str(file_path), "filename": path.name}
                )
                return [doc]
            except Exception as e2:
                logger.error(f"Fallback loading failed: {e2}")
                return []
    
    def add_documents(
        self,
        file_paths: List[str],
        conversation_id: Optional[str] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            file_paths: List of file paths to add
            conversation_id: Optional conversation ID for metadata
            
        Returns:
            List of document IDs
        """
        all_documents = []
        
        for file_path in file_paths:
            # Load document
            documents = self.load_document(file_path)
            
            # Add metadata
            for doc in documents:
                doc.metadata["added_at"] = datetime.now().isoformat()
                if conversation_id:
                    doc.metadata["conversation_id"] = conversation_id
                doc.metadata["file_path"] = file_path
            
            all_documents.extend(documents)
        
        if not all_documents:
            logger.warning("No documents to add")
            return []
        
        # Split documents into chunks
        logger.info(f"Splitting {len(all_documents)} documents into chunks")
        splits = self.text_splitter.split_documents(all_documents)
        logger.info(f"Created {len(splits)} chunks")
        
        # Add to vector store
        logger.info("Adding documents to Chroma vector store")
        ids = self.vector_store.add_documents(documents=splits)
        
        logger.info(f"Added {len(ids)} document chunks to vector store")
        return ids
    
    def get_or_create_conversation_chain(
        self,
        conversation_id: str,
        k: int = 4,
        use_summary_memory: bool = False
    ) -> ConversationalRetrievalChain:
        """
        Get or create a conversation chain with memory.
        
        Args:
            conversation_id: Unique conversation identifier
            k: Number of documents to retrieve
            use_summary_memory: Use summary memory instead of buffer memory
            
        Returns:
            ConversationalRetrievalChain instance
        """
        if conversation_id not in self.conversation_chains:
            # Create memory for this conversation
            if use_summary_memory:
                memory = ConversationSummaryMemory(
                    llm=self.llm,
                    memory_key="chat_history",
                    return_messages=True,
                    output_key="answer"
                )
            else:
                memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    output_key="answer"
                )
            
            self.conversation_memories[conversation_id] = memory
            
            # Create retriever
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )
            
            # Create the conversational chain
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=memory,
                return_source_documents=True,
                verbose=True
            )
            
            self.conversation_chains[conversation_id] = chain
            logger.info(f"Created new conversation chain for {conversation_id}")
        
        return self.conversation_chains[conversation_id]
    
    def create_modern_chain(self, conversation_id: str, k: int = 4):
        """
        Create a modern chain using the recommended approach.
        
        Uses create_history_aware_retriever and create_retrieval_chain
        as recommended in the latest LangChain documentation.
        """
        # Create retriever
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        
        # Contextualize question prompt
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )
        
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        # Create history-aware retriever
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, contextualize_q_prompt
        )
        
        # Answer question prompt
        system_prompt = (
            "You are an assistant for question-answering tasks. "
            "Use the following pieces of retrieved context to answer "
            "the question. If you don't know the answer, say that you "
            "don't know. Use three sentences maximum and keep the "
            "answer concise."
            "\n\n"
            "{context}"
        )
        
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        # Create question-answer chain
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        
        # Create retrieval chain
        rag_chain = create_retrieval_chain(
            history_aware_retriever,
            question_answer_chain
        )
        
        return rag_chain
    
    def query(
        self,
        conversation_id: str,
        question: str,
        use_modern_chain: bool = True,
        streaming_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system with conversation context.
        
        Args:
            conversation_id: Conversation identifier
            question: User question
            use_modern_chain: Use the modern recommended approach
            streaming_callback: Optional callback for streaming tokens
            
        Returns:
            Dictionary with answer and source documents
        """
        try:
            if use_modern_chain:
                # Use modern chain approach
                chain = self.create_modern_chain(conversation_id)
                
                # Get or create chat history for this conversation
                if conversation_id not in self.conversation_memories:
                    self.conversation_memories[conversation_id] = []
                
                chat_history = self.conversation_memories[conversation_id]
                
                # Prepare input
                chain_input = {
                    "input": question,
                    "chat_history": chat_history
                }
                
                # Execute chain
                if streaming_callback:
                    # Set up streaming
                    handler = StreamingCallbackHandler(streaming_callback)
                    response = chain.invoke(
                        chain_input,
                        config={"callbacks": [handler]}
                    )
                else:
                    response = chain.invoke(chain_input)
                
                # Update chat history
                chat_history.append(HumanMessage(content=question))
                chat_history.append(AIMessage(content=response["answer"]))
                
                # Keep only last 10 messages to avoid token limits
                if len(chat_history) > 20:
                    chat_history = chat_history[-20:]
                
                self.conversation_memories[conversation_id] = chat_history
                
                return {
                    "answer": response["answer"],
                    "source_documents": response.get("context", []),
                    "chat_history": chat_history
                }
            
            else:
                # Use traditional ConversationalRetrievalChain
                chain = self.get_or_create_conversation_chain(conversation_id)
                
                # Set up callbacks if streaming
                callbacks = []
                if streaming_callback:
                    callbacks.append(StreamingCallbackHandler(streaming_callback))
                
                # Execute chain
                response = chain(
                    {"question": question},
                    callbacks=callbacks
                )
                
                return {
                    "answer": response["answer"],
                    "source_documents": response.get("source_documents", []),
                    "chat_history": response.get("chat_history", "")
                }
        
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "answer": f"I encountered an error processing your question: {str(e)}",
                "source_documents": [],
                "error": str(e)
            }
    
    def clear_conversation_memory(self, conversation_id: str):
        """Clear memory for a specific conversation."""
        if conversation_id in self.conversation_memories:
            memory = self.conversation_memories[conversation_id]
            if hasattr(memory, 'clear'):
                memory.clear()
            else:
                # For list-based memory
                self.conversation_memories[conversation_id] = []
        
        if conversation_id in self.conversation_chains:
            del self.conversation_chains[conversation_id]
        
        logger.info(f"Cleared memory for conversation {conversation_id}")
    
    def delete_collection(self):
        """Delete the entire vector store collection."""
        try:
            self.vector_store.delete_collection()
            logger.info(f"Deleted collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
    
    def get_retriever(self, k: int = 4):
        """Get a retriever from the vector store."""
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Perform similarity search on the vector store."""
        return self.vector_store.similarity_search(query, k=k)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        try:
            # Get collection
            collection = self.vector_store._collection
            
            return {
                "name": self.collection_name,
                "count": collection.count(),
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "name": self.collection_name,
                "error": str(e)
            }