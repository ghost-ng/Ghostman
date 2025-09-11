"""
FAISS RAG Enhanced REPL Widget

PyQt6-optimized REPL widget with FAISS-only RAG integration.
Provides responsive document upload and querying without LangChain overhead.
"""

import logging
import time
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QProgressBar, QListWidget, QListWidgetItem, QFrame,
    QToolButton, QMenu, QFileDialog, QMessageBox, QTextEdit,
    QSplitter, QGroupBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QObject, 
    QPropertyAnimation, QEasingCurve, QRect
)
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette

from ...infrastructure.faiss_only_rag_coordinator import FAISSONlyRAGCoordinator
from ...infrastructure.conversation_management.services.conversation_service import ConversationService

logger = logging.getLogger("ghostman.faiss_rag_enhanced_repl")


class DocumentUploadWidget(QWidget):
    """
    Drag-and-drop document upload widget optimized for FAISS RAG.
    """
    
    # Signals
    file_uploaded = pyqtSignal(str, str)  # file_path, conversation_id
    upload_progress = pyqtSignal(str, int, str)  # job_id, progress, status
    upload_completed = pyqtSignal(str, bool, str)  # job_id, success, message
    
    def __init__(self, rag_coordinator: FAISSONlyRAGCoordinator, parent=None):
        super().__init__(parent)
        self.rag_coordinator = rag_coordinator
        self.current_conversation_id = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup upload widget UI."""
        layout = QVBoxLayout(self)
        
        # Upload area
        self.upload_frame = QFrame()
        self.upload_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.upload_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
                min-height: 100px;
            }
            QFrame:hover {
                border-color: #007acc;
                background-color: #f0f8ff;
            }
        """)
        
        upload_layout = QVBoxLayout(self.upload_frame)
        
        # Upload button
        self.upload_btn = QPushButton("📁 Upload Documents")
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.clicked.connect(self.select_files)
        
        # Status label
        self.status_label = QLabel("Drag files here or click to upload")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        
        upload_layout.addWidget(self.upload_btn)
        upload_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        
        layout.addWidget(QLabel("Document Upload"))
        layout.addWidget(self.upload_frame)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Uploaded Documents:"))
        layout.addWidget(self.file_list)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def connect_signals(self):
        """Connect RAG coordinator signals."""
        if self.rag_coordinator:
            self.rag_coordinator.document_uploaded.connect(self.on_document_uploaded)
            self.rag_coordinator.error_occurred.connect(self.on_error)
    
    def set_conversation(self, conversation_id: str):
        """Set current conversation for uploads."""
        self.current_conversation_id = conversation_id
        self.refresh_document_list()
    
    def select_files(self):
        """Open file dialog to select documents."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents to Upload",
            "",
            "All Files (*);;Text Files (*.txt);;PDF Files (*.pdf);;Markdown Files (*.md)"
        )
        
        if file_paths:
            self.upload_files(file_paths)
    
    def upload_files(self, file_paths: List[str]):
        """Upload multiple files."""
        if not self.current_conversation_id:
            QMessageBox.warning(self, "No Conversation", "Please select a conversation first.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        for file_path in file_paths:
            self.upload_single_file(file_path)
    
    def upload_single_file(self, file_path: str):
        """Upload a single file."""
        try:
            self.status_label.setText(f"Uploading {Path(file_path).name}...")
            
            job_id = self.rag_coordinator.upload_document_async(
                file_path=file_path,
                conversation_id=self.current_conversation_id,
                progress_callback=self.on_upload_progress,
                completion_callback=self.on_upload_complete
            )
            
            if not job_id:
                self.on_error("Failed to start upload job")
                
        except Exception as e:
            self.on_error(f"Upload failed: {str(e)}")
    
    def on_upload_progress(self, job_id: str, progress: int, status: str):
        """Handle upload progress updates."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def on_upload_complete(self, job_id: str, success: bool, message: str):
        """Handle upload completion."""
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText("Upload completed successfully")
            self.refresh_document_list()
            # Auto-hide success message after 3 seconds
            QTimer.singleShot(3000, lambda: self.status_label.setText("Ready for more uploads"))
        else:
            self.status_label.setText(f"Upload failed: {message}")
    
    def on_document_uploaded(self, conversation_id: str, document_id: str, chunk_count: int):
        """Handle document upload signal."""
        if conversation_id == self.current_conversation_id:
            self.refresh_document_list()
    
    def on_error(self, error_message: str):
        """Handle error messages."""
        self.status_label.setText(f"Error: {error_message}")
        self.progress_bar.setVisible(False)
        logger.error(f"Upload error: {error_message}")
    
    def refresh_document_list(self):
        """Refresh the list of uploaded documents."""
        if not self.current_conversation_id or not self.rag_coordinator:
            return
        
        try:
            documents = self.rag_coordinator.get_conversation_documents(self.current_conversation_id)
            
            self.file_list.clear()
            
            # Group documents by document_id
            doc_groups = {}
            for doc in documents:
                doc_id = doc['metadata']['document_id']
                if doc_id not in doc_groups:
                    doc_groups[doc_id] = {
                        'filename': doc['metadata'].get('filename', 'Unknown'),
                        'chunks': 0,
                        'upload_time': doc['metadata'].get('upload_timestamp', 0)
                    }
                doc_groups[doc_id]['chunks'] += 1
            
            # Add to list widget
            for doc_id, info in doc_groups.items():
                item_text = f"{info['filename']} ({info['chunks']} chunks)"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, doc_id)
                self.file_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Failed to refresh document list: {e}")
    
    # Drag and drop support
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop events."""
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        
        if file_paths:
            self.upload_files(file_paths)


class ConversationQueryWidget(QWidget):
    """
    Conversation-specific query widget with context display.
    """
    
    # Signals
    query_submitted = pyqtSignal(str, str)  # query, conversation_id
    context_updated = pyqtSignal(dict)  # context_info
    
    def __init__(self, rag_coordinator: FAISSONlyRAGCoordinator, parent=None):
        super().__init__(parent)
        self.rag_coordinator = rag_coordinator
        self.current_conversation_id = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup query widget UI."""
        layout = QVBoxLayout(self)
        
        # Query input
        query_group = QGroupBox("RAG Query")
        query_layout = QVBoxLayout(query_group)
        
        self.query_input = QTextEdit()
        self.query_input.setMaximumHeight(80)
        self.query_input.setPlaceholderText("Ask a question about your uploaded documents...")
        
        self.query_btn = QPushButton("🔍 Search Documents")
        self.query_btn.clicked.connect(self.submit_query)
        
        query_layout.addWidget(self.query_input)
        query_layout.addWidget(self.query_btn)
        
        # Results display
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        
        results_layout.addWidget(self.results_text)
        
        # Context display
        context_group = QGroupBox("Document Context")
        context_layout = QVBoxLayout(context_group)
        
        self.context_list = QListWidget()
        self.context_list.setMaximumHeight(150)
        
        context_layout.addWidget(self.context_list)
        
        layout.addWidget(query_group)
        layout.addWidget(results_group)
        layout.addWidget(context_group)
    
    def connect_signals(self):
        """Connect RAG coordinator signals."""
        if self.rag_coordinator:
            self.rag_coordinator.query_completed.connect(self.on_query_completed)
            self.rag_coordinator.error_occurred.connect(self.on_error)
    
    def set_conversation(self, conversation_id: str):
        """Set current conversation for queries."""
        self.current_conversation_id = conversation_id
        self.clear_results()
    
    def submit_query(self):
        """Submit query to RAG system."""
        if not self.current_conversation_id:
            QMessageBox.warning(self, "No Conversation", "Please select a conversation first.")
            return
        
        query_text = self.query_input.toPlainText().strip()
        if not query_text:
            QMessageBox.warning(self, "Empty Query", "Please enter a query.")
            return
        
        try:
            self.query_btn.setEnabled(False)
            self.query_btn.setText("🔄 Searching...")
            
            # Execute query synchronously (optimized for PyQt6)
            result = self.rag_coordinator.query_conversation_sync(
                query_text=query_text,
                conversation_id=self.current_conversation_id,
                top_k=5
            )
            
            self.display_results(result)
            
        except Exception as e:
            self.on_error(f"Query failed: {str(e)}")
        finally:
            self.query_btn.setEnabled(True)
            self.query_btn.setText("🔍 Search Documents")
    
    def display_results(self, result: Dict[str, Any]):
        """Display query results."""
        try:
            # Display answer
            answer = result.get('answer', 'No answer generated')
            self.results_text.setPlainText(answer)
            
            # Display sources
            sources = result.get('sources', [])
            self.context_list.clear()
            
            for i, source in enumerate(sources):
                content_preview = source['content'][:100] + "..." if len(source['content']) > 100 else source['content']
                score = source.get('score', 0.0)
                filename = source['metadata'].get('filename', 'Unknown')
                
                item_text = f"[{score:.2f}] {filename}: {content_preview}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, source)
                self.context_list.addItem(item)
            
            # Emit context update signal
            self.context_updated.emit({
                'sources_count': len(sources),
                'query_time': result.get('query_time', 0.0),
                'conversation_id': self.current_conversation_id
            })
            
        except Exception as e:
            logger.error(f"Failed to display results: {e}")
            self.results_text.setPlainText(f"Error displaying results: {str(e)}")
    
    def clear_results(self):
        """Clear query results."""
        self.query_input.clear()
        self.results_text.clear()
        self.context_list.clear()
    
    def on_query_completed(self, conversation_id: str, query: str, result_count: int):
        """Handle query completion signal."""
        if conversation_id == self.current_conversation_id:
            logger.info(f"Query completed: {result_count} results for '{query[:30]}...'")
    
    def on_error(self, error_message: str):
        """Handle error messages."""
        self.results_text.setPlainText(f"Error: {error_message}")
        logger.error(f"Query error: {error_message}")


class FAISSRAGEnhancedREPL(QWidget):
    """
    Complete FAISS RAG-enhanced REPL widget for PyQt6.
    
    Provides drag-and-drop document upload, conversation-specific querying,
    and real-time status updates without blocking the UI.
    """
    
    # Signals
    conversation_changed = pyqtSignal(str)  # conversation_id
    status_updated = pyqtSignal(str)  # status_message
    
    def __init__(self, 
                 rag_coordinator: FAISSONlyRAGCoordinator,
                 conversation_service: ConversationService,
                 parent=None):
        super().__init__(parent)
        
        self.rag_coordinator = rag_coordinator
        self.conversation_service = conversation_service
        self.current_conversation_id = None
        
        self.setup_ui()
        self.connect_signals()
        
        logger.info("FAISS RAG-enhanced REPL initialized")
    
    def setup_ui(self):
        """Setup the enhanced REPL UI."""
        layout = QVBoxLayout(self)
        
        # Status bar
        self.status_label = QLabel("FAISS RAG System Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e8f5e8;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Document upload
        self.upload_widget = DocumentUploadWidget(self.rag_coordinator)
        
        # Right panel - Query interface
        self.query_widget = ConversationQueryWidget(self.rag_coordinator)
        
        splitter.addWidget(self.upload_widget)
        splitter.addWidget(self.query_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(self.status_label)
        layout.addWidget(splitter)
    
    def connect_signals(self):
        """Connect all internal signals."""
        # RAG coordinator signals
        if self.rag_coordinator:
            self.rag_coordinator.status_changed.connect(self.update_status)
            self.rag_coordinator.error_occurred.connect(self.show_error)
        
        # Widget signals
        self.upload_widget.file_uploaded.connect(self.on_file_uploaded)
        self.query_widget.query_submitted.connect(self.on_query_submitted)
        self.query_widget.context_updated.connect(self.on_context_updated)
    
    def set_conversation(self, conversation_id: str):
        """Set current conversation for RAG operations."""
        self.current_conversation_id = conversation_id
        
        # Update child widgets
        self.upload_widget.set_conversation(conversation_id)
        self.query_widget.set_conversation(conversation_id)
        
        # Emit signal
        self.conversation_changed.emit(conversation_id)
        
        self.update_status(f"RAG context set to conversation: {conversation_id}")
        logger.info(f"FAISS RAG context set to conversation: {conversation_id}")
    
    def update_status(self, message: str):
        """Update status display."""
        self.status_label.setText(message)
        self.status_updated.emit(message)
        
        # Auto-clear status after 5 seconds for non-error messages
        if not message.lower().startswith('error'):
            QTimer.singleShot(5000, lambda: self.status_label.setText("FAISS RAG System Ready"))
    
    def show_error(self, error_message: str):
        """Show error message."""
        self.status_label.setText(f"❌ {error_message}")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ffe8e8;
                border: 1px solid #f44336;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                color: #c62828;
            }
        """)
        
        # Reset style after 10 seconds
        QTimer.singleShot(10000, self.reset_status_style)
    
    def reset_status_style(self):
        """Reset status label style to normal."""
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e8f5e8;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """)
    
    def get_rag_status(self) -> Dict[str, Any]:
        """Get comprehensive RAG status."""
        if self.rag_coordinator:
            return self.rag_coordinator.get_status()
        return {'ready': False, 'error': 'No RAG coordinator'}
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG statistics."""
        if self.rag_coordinator:
            return self.rag_coordinator.get_comprehensive_stats()
        return {}
    
    # Signal handlers
    def on_file_uploaded(self, file_path: str, conversation_id: str):
        """Handle file upload completion."""
        self.update_status(f"Document uploaded: {Path(file_path).name}")
    
    def on_query_submitted(self, query: str, conversation_id: str):
        """Handle query submission."""
        self.update_status(f"Processing query: {query[:30]}...")
    
    def on_context_updated(self, context_info: Dict[str, Any]):
        """Handle context update."""
        sources_count = context_info.get('sources_count', 0)
        query_time = context_info.get('query_time', 0.0)
        self.update_status(f"Query completed: {sources_count} sources found in {query_time:.2f}s")
    
    def clear_conversation_context(self):
        """Clear current conversation context."""
        self.current_conversation_id = None
        self.upload_widget.set_conversation("")
        self.query_widget.set_conversation("")
        self.update_status("Conversation context cleared")
    
    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up FAISS RAG-enhanced REPL...")
        self.clear_conversation_context()


def enhance_repl_with_faiss_rag(
    repl_widget,
    rag_coordinator: FAISSONlyRAGCoordinator,
    conversation_service: ConversationService
) -> FAISSRAGEnhancedREPL:
    """
    Factory function to enhance a REPL widget with FAISS RAG capabilities.
    
    This replaces the LangChain-based enhancement with optimized FAISS-only implementation.
    """
    enhanced_repl = FAISSRAGEnhancedREPL(rag_coordinator, conversation_service)
    
    logger.info("REPL widget enhanced with FAISS-only RAG capabilities")
    return enhanced_repl