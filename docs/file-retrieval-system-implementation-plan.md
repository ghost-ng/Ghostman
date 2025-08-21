# Ghostman File Retrieval System - Implementation Plan

## Executive Summary

The Ghostman File Retrieval System will enable users to upload documents (PDF, DOCX, PPTX, TXT, MD, JSON, LOG) to enhance AI responses through OpenAI's vector stores and assistants API. This document provides a comprehensive implementation plan for integrating file processing, upload, and AI enhancement capabilities into the existing Ghostman desktop application.

### System Goals
- **User Experience**: Seamless file integration via drag-drop, right-click "Send To", and manual selection
- **AI Enhancement**: Document content enhances AI responses through vector search capabilities  
- **Security**: Comprehensive file validation and safe processing
- **Performance**: Efficient handling of large files with progress feedback
- **Integration**: Minimal disruption to existing Ghostman architecture and user workflows

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ghostman File Retrieval System                │
├─────────────────────────────────────────────────────────────────┤
│  UI Layer (PyQt6)                                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │ FineTuningToolbar│ │FileManagementDlg│ │ FileDropZone        │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
│             │                   │                    │            │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer                                                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │FileProcessingSvc│ │ FileUploadSvc   │ │ FineTuningSvc       │  │
│  │- Extract content│ │- OpenAI upload  │ │- Vector stores      │  │
│  │- Validate files │ │- File management│ │- Enhanced responses │  │
│  │- JSONL convert  │ │- Progress track │ │- Context integration│  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
│             │                   │                    │            │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer                                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │  Enhanced       │ │  Extended       │ │  File Database      │  │
│  │  AIService      │ │  APIClient      │ │  Management         │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
│             │                   │                    │            │
├─────────────────────────────────────────────────────────────────┤
│  External APIs & Storage                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │ OpenAI Files    │ │ OpenAI Vector   │ │ Local File          │  │
│  │ API             │ │ Stores API      │ │ Storage             │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

```
┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   User   │───▶│File Sources │───▶│ Validation & │───▶│   OpenAI    │
│          │    │- Drag/Drop  │    │  Processing  │    │   Upload    │
│          │    │- Send To    │    │              │    │             │
│          │    │- Browse     │    │              │    │             │
└──────────┘    └─────────────┘    └──────────────┘    └─────────────┘
                                          │                    │
                                          ▼                    ▼
┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│Enhanced  │◀───│ AI Service  │◀───│Vector Store  │◀───│File Storage │
│Responses │    │Integration  │    │ Management   │    │& Indexing  │
└──────────┘    └─────────────┘    └──────────────┘    └─────────────┘
```

## Component Design Specifications

### 1. FileProcessingService

**Location**: `ghostman/src/infrastructure/files/file_processing_service.py`

```python
class FileProcessingService:
    """Core file processing and validation service"""
    
    # Supported file types and extraction methods
    SUPPORTED_FORMATS = {
        '.pdf': PDFExtractor,
        '.docx': DOCXExtractor, 
        '.pptx': PPTXExtractor,
        '.txt': TextExtractor,
        '.md': MarkdownExtractor,
        '.json': JSONExtractor,
        '.log': LogExtractor
    }
    
    # Security validation
    MAX_FILE_SIZE = 512 * 1024 * 1024  # 512MB
    ALLOWED_MIME_TYPES = {...}
    
    def __init__(self):
        self.validator = FileValidator()
        self.cache = DocumentCache()
        self.logger = logging.getLogger("ghostman.file_processing")
    
    async def process_file(self, file_path: str) -> ProcessingResult:
        """Main file processing entry point"""
        
    async def validate_file(self, file_path: str) -> ValidationResult:
        """Comprehensive file validation"""
        
    async def extract_content(self, file_path: str) -> ContentResult:
        """Extract text content from file"""
        
    async def create_training_data(self, content: str, metadata: dict) -> JSONLData:
        """Convert content to JSONL training format"""
```

### 2. FileUploadService

**Location**: `ghostman/src/infrastructure/files/file_upload_service.py`

```python
class FileUploadService:
    """OpenAI API integration for file uploads"""
    
    def __init__(self, api_client: OpenAICompatibleClient):
        self.api_client = api_client
        self.upload_queue = AsyncQueue()
        self.progress_callbacks = {}
    
    async def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        """Upload file to OpenAI with progress tracking"""
        
    async def create_vector_store(self, name: str, file_ids: List[str]) -> VectorStoreResult:
        """Create vector store from uploaded files"""
        
    async def delete_file(self, file_id: str) -> bool:
        """Remove file from OpenAI storage"""
        
    async def list_files(self, purpose: str = None) -> List[FileInfo]:
        """List uploaded files"""
        
    def set_progress_callback(self, file_path: str, callback: Callable):
        """Set progress callback for file upload"""
```

### 3. FineTuningService

**Location**: `ghostman/src/infrastructure/files/fine_tuning_service.py`

```python
class FineTuningService:
    """AI enhancement through file context integration"""
    
    def __init__(self, ai_service: AIService, upload_service: FileUploadService):
        self.ai_service = ai_service
        self.upload_service = upload_service
        self.active_vector_stores = {}
    
    async def integrate_files(self, file_paths: List[str]) -> IntegrationResult:
        """Process and integrate files for AI enhancement"""
        
    async def enhance_chat_completion(self, 
                                    messages: List[dict],
                                    model: str,
                                    **kwargs) -> EnhancedResponse:
        """Chat completion with file context"""
        
    async def remove_file_integration(self, file_path: str) -> bool:
        """Remove file from AI context"""
        
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current file integration status"""
```

### 4. UI Components

#### FineTuningToolbar Widget

**Location**: `ghostman/src/presentation/widgets/fine_tuning_toolbar.py`

```python
class FineTuningToolbar(QWidget):
    """Expandable toolbar for file management"""
    
    files_changed = pyqtSignal(list)  # Emitted when files change
    processing_complete = pyqtSignal(dict)  # Processing results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.expanded = False
        self.setup_ui()
        self.setup_themes()
    
    def setup_ui(self):
        """Setup toolbar UI components"""
        # Collapsible header with file count
        # File cards grid
        # Add files button
        # Clear all button
        
    def add_files(self, file_paths: List[str]):
        """Add files to toolbar"""
        
    def remove_file(self, file_path: str):
        """Remove file from toolbar"""
        
    def expand(self):
        """Expand toolbar to show files"""
        
    def collapse(self):
        """Collapse toolbar to header only"""
```

#### FileCard Component

```python
class FileCard(QWidget):
    """Individual file representation with status and controls"""
    
    remove_requested = pyqtSignal(str)  # File path to remove
    
    def __init__(self, file_info: FileInfo, parent=None):
        self.file_info = file_info
        self.status = "pending"
        self.setup_ui()
    
    def update_status(self, status: str, message: str = ""):
        """Update file processing status"""
        
    def set_progress(self, progress: float):
        """Update progress bar"""
```

#### FileManagementDialog

**Location**: `ghostman/src/presentation/dialogs/file_management_dialog.py`

```python
class FileManagementDialog(QDialog):
    """Advanced file management interface"""
    
    def __init__(self, file_service: FineTuningService, parent=None):
        self.file_service = file_service
        self.setup_ui()
        self.load_files()
    
    def setup_ui(self):
        """Setup dialog UI with file list, filters, and actions"""
        
    def load_files(self):
        """Load current files from service"""
        
    def bulk_remove_files(self, file_paths: List[str]):
        """Remove multiple files"""
```

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Deliverables**:
- FileProcessingService with content extraction
- File validation and security framework
- Document cache implementation
- Basic unit tests

**Sprint 1.1**: Core Services Setup
- [ ] Create file processing service structure
- [ ] Implement PDF, DOCX, PPTX extractors using pypdf, python-docx, python-pptx
- [ ] Add TXT, MD, JSON, LOG extractors
- [ ] Create comprehensive file validator using python-magic

**Sprint 1.2**: Security & Performance
- [ ] Implement content-based file validation
- [ ] Add malicious content detection
- [ ] Create document caching system
- [ ] Add async processing support

### Phase 2: API Integration (Weeks 3-4)
**Deliverables**:
- Enhanced OpenAI API client with file endpoints
- FileUploadService with progress tracking
- Vector store management
- API integration tests

**Sprint 2.1**: OpenAI API Extensions
- [ ] Extend `api_client.py` with file upload methods
- [ ] Add vector store creation and management
- [ ] Implement file listing and deletion
- [ ] Add comprehensive error handling

**Sprint 2.2**: Upload Service
- [ ] Create FileUploadService with async upload
- [ ] Add progress tracking and callbacks
- [ ] Implement retry logic and error recovery
- [ ] Add upload queue management

### Phase 3: UI Integration (Weeks 5-6)
**Deliverables**:
- FineTuningToolbar widget
- FileCard components with status indicators
- Drag-and-drop integration
- Theme-aware styling

**Sprint 3.1**: Core UI Components
- [ ] Create FineTuningToolbar with expand/collapse
- [ ] Implement FileCard with status and progress
- [ ] Add file grid layout and management
- [ ] Create add/remove file actions

**Sprint 3.2**: Integration & Interactions
- [ ] Integrate toolbar with main application
- [ ] Add drag-and-drop support to avatar/REPL
- [ ] Implement file management dialog
- [ ] Add theme-aware styling for all components

### Phase 4: AI Service Enhancement (Weeks 7-8)
**Deliverables**:
- Enhanced AIService with file context
- FineTuningService for document integration
- Chat completion enhancement
- Context management

**Sprint 4.1**: AI Integration
- [ ] Create FineTuningService
- [ ] Enhance AIService for file context
- [ ] Implement vector store chat completion
- [ ] Add context management

**Sprint 4.2**: User Experience
- [ ] Add file integration to conversation flow
- [ ] Implement status notifications in REPL
- [ ] Add file context indicators
- [ ] Create help and documentation

### Phase 5: Testing & Polish (Weeks 9-10)
**Deliverables**:
- Comprehensive testing suite
- Performance optimization
- Cross-platform compatibility
- Production deployment

**Sprint 5.1**: Testing & Quality
- [ ] Unit tests for all services (>90% coverage)
- [ ] Integration tests for API functionality
- [ ] UI tests for all components
- [ ] Performance and load testing

**Sprint 5.2**: Deployment Preparation
- [ ] Cross-platform testing (Windows/Mac/Linux)
- [ ] Installation and setup procedures
- [ ] User documentation and help system
- [ ] Monitoring and diagnostics

## API Integration Details

### OpenAI Files API Integration

#### Extended API Client Methods

```python
# Add to existing OpenAICompatibleClient class in api_client.py

def upload_file(self, file_path: str, purpose: str = "assistants") -> APIResponse:
    """Upload a file to OpenAI for processing."""
    url = f"{self.base_url}/files"
    
    with open(file_path, 'rb') as file:
        files = {
            'file': (os.path.basename(file_path), file, 'application/octet-stream'),
            'purpose': (None, purpose)
        }
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = session_manager.make_request(
                method="POST",
                url=url,
                files=files,
                headers=headers,
                timeout=self.timeout * 3  # Extended timeout for uploads
            )
            
            if response.status_code < 400:
                return APIResponse(
                    success=True,
                    data=response.json(),
                    status_code=response.status_code
                )
            else:
                error = self._handle_error_response(response)
                return APIResponse(
                    success=False,
                    error=str(error),
                    status_code=response.status_code
                )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Upload failed: {str(e)}",
                status_code=None
            )

def list_files(self, purpose: Optional[str] = None) -> APIResponse:
    """List all uploaded files."""
    params = {"purpose": purpose} if purpose else {}
    return self._make_request("GET", "files", params=params)

def delete_file(self, file_id: str) -> APIResponse:
    """Delete an uploaded file."""
    return self._make_request("DELETE", f"files/{file_id}")

def create_vector_store(self, name: str, file_ids: List[str], expires_days: int = 7) -> APIResponse:
    """Create a vector store with uploaded files."""
    data = {
        "name": name,
        "file_ids": file_ids,
        "expires_after": {
            "anchor": "last_active_at",
            "days": expires_days
        }
    }
    return self._make_request("POST", "vector_stores", data)

def list_vector_stores(self, limit: int = 20) -> APIResponse:
    """List vector stores."""
    params = {"limit": limit}
    return self._make_request("GET", "vector_stores", params=params)

def delete_vector_store(self, vector_store_id: str) -> APIResponse:
    """Delete a vector store."""
    return self._make_request("DELETE", f"vector_stores/{vector_store_id}")
```

#### Enhanced Chat Completion with Files

```python
# Add to existing AIService class in ai_service.py

def __init__(self, config: Dict[str, Any]):
    # ... existing initialization ...
    self.active_vector_stores = {}
    self.file_context_enabled = False

async def send_message_with_files(self, 
                                message: str, 
                                vector_store_id: str = None,
                                stream: bool = False) -> Dict[str, Any]:
    """Send message with file context enhancement."""
    
    if not self._initialized:
        logger.error("AI service not initialized")
        return {'success': False, 'error': 'AI service not initialized'}
    
    try:
        # Add user message to conversation
        self.conversation.add_message('user', message)
        
        # Prepare API messages
        api_messages = self.conversation.to_api_format()
        
        # Prepare parameters
        model_name = self._config['model_name']
        api_params = {
            'messages': api_messages,
            'model': model_name,
            'temperature': self._config['temperature'],
            'max_tokens': self._config.get('max_tokens'),
            'stream': stream
        }
        
        # Add file search if vector store available
        if vector_store_id or self.active_vector_stores:
            api_params['tools'] = [{"type": "file_search"}]
            
            # Use provided vector store or default active one
            store_id = vector_store_id or list(self.active_vector_stores.keys())[0]
            api_params['tool_resources'] = {
                "file_search": {
                    "vector_store_ids": [store_id]
                }
            }
            
            logger.info(f"Enhanced chat with vector store: {store_id}")
        
        # Make API request
        response = self.client.chat_completion(**api_params)
        
        if response.success:
            # Extract response content
            assistant_message = self._extract_response_content(response.data)
            
            # Log file search usage
            if 'usage' in response.data and 'file_search' in str(response.data.get('usage', {})):
                logger.info("File search was utilized in response generation")
            
            # Add assistant response to conversation
            self.conversation.add_message('assistant', assistant_message)
            
            logger.info("✓ Enhanced AI response with file context")
            return {
                'success': True,
                'response': assistant_message,
                'usage': response.data.get('usage', {}),
                'file_context_used': bool(vector_store_id or self.active_vector_stores)
            }
        else:
            logger.error(f"✗ Enhanced AI API request failed: {response.error}")
            return {'success': False, 'error': response.error}
            
    except Exception as e:
        logger.error(f"✗ Error in enhanced message processing: {e}")
        return {'success': False, 'error': str(e)}

def set_active_vector_store(self, vector_store_id: str, name: str):
    """Set active vector store for file enhancement."""
    self.active_vector_stores[vector_store_id] = name
    self.file_context_enabled = True
    logger.info(f"Activated vector store: {name} ({vector_store_id})")

def remove_vector_store(self, vector_store_id: str):
    """Remove vector store from active context."""
    if vector_store_id in self.active_vector_stores:
        name = self.active_vector_stores[vector_store_id]
        del self.active_vector_stores[vector_store_id]
        logger.info(f"Deactivated vector store: {name}")
        
        if not self.active_vector_stores:
            self.file_context_enabled = False
```

## Security & Validation Framework

### File Validation Pipeline

```python
class ComprehensiveFileValidator:
    """Multi-layer file validation system"""
    
    # Security Configuration
    MAX_FILE_SIZES = {
        'pdf': 100 * 1024 * 1024,    # 100MB
        'docx': 50 * 1024 * 1024,    # 50MB  
        'pptx': 100 * 1024 * 1024,   # 100MB
        'txt': 10 * 1024 * 1024,     # 10MB
        'md': 10 * 1024 * 1024,      # 10MB
        'json': 10 * 1024 * 1024,    # 10MB
        'log': 50 * 1024 * 1024      # 50MB
    }
    
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/markdown', 
        'application/json',
        'text/x-log'
    }
    
    # Malicious pattern detection
    SUSPICIOUS_PATTERNS = [
        rb'<script[^>]*>',      # JavaScript
        rb'eval\s*\(',          # Code evaluation
        rb'exec\s*\(',          # Code execution
        rb'__import__',         # Python imports
        rb'os\.system',         # System calls
        rb'subprocess',         # Process execution
        rb'powershell',         # PowerShell
        rb'cmd\.exe'            # Command prompt
    ]
    
    def __init__(self):
        self.file_magic = magic.Magic(mime=True)
        self.logger = logging.getLogger("ghostman.file_validator")
    
    async def validate_file(self, file_path: str) -> ValidationResult:
        """Comprehensive file validation pipeline."""
        path = Path(file_path)
        
        try:
            # 1. Basic file checks
            if not path.exists():
                return ValidationResult(False, "File does not exist", "FILE_NOT_FOUND")
            
            if not path.is_file():
                return ValidationResult(False, "Path is not a file", "INVALID_PATH")
            
            # 2. File size validation
            file_size = path.stat().st_size
            extension = path.suffix[1:].lower()
            
            if extension not in self.MAX_FILE_SIZES:
                return ValidationResult(False, f"Unsupported file type: {extension}", "UNSUPPORTED_TYPE")
            
            if file_size > self.MAX_FILE_SIZES[extension]:
                max_mb = self.MAX_FILE_SIZES[extension] / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                return ValidationResult(
                    False, 
                    f"File too large: {actual_mb:.1f}MB (max: {max_mb:.0f}MB)", 
                    "FILE_TOO_LARGE"
                )
            
            # 3. MIME type validation
            mime_type = self.file_magic.from_file(str(path))
            if mime_type not in self.ALLOWED_MIME_TYPES:
                return ValidationResult(False, f"Invalid MIME type: {mime_type}", "INVALID_MIME_TYPE")
            
            # 4. Content structure validation
            structure_valid = await self._validate_file_structure(path, mime_type)
            if not structure_valid:
                return ValidationResult(False, "File structure validation failed", "INVALID_STRUCTURE")
            
            # 5. Security scanning
            security_result = await self._scan_for_malicious_content(path)
            if not security_result.is_safe:
                return ValidationResult(False, security_result.reason, "SECURITY_THREAT")
            
            # 6. Content readability test
            content_result = await self._test_content_extraction(path, mime_type)
            if not content_result.readable:
                return ValidationResult(False, "Content extraction failed", "UNREADABLE_CONTENT")
            
            self.logger.info(f"✓ File validation passed: {path.name}")
            return ValidationResult(
                True, 
                "File validation successful", 
                "VALID", 
                {
                    'size': file_size,
                    'mime_type': mime_type,
                    'extension': extension,
                    'preview': content_result.preview[:200] if content_result.preview else None
                }
            )
            
        except Exception as e:
            self.logger.error(f"✗ File validation error for {path.name}: {e}")
            return ValidationResult(False, f"Validation error: {str(e)}", "VALIDATION_ERROR")
```

### Content Sanitization

```python
class ContentSanitizer:
    """Clean and sanitize extracted content"""
    
    def __init__(self):
        # Initialize bleach for HTML/markup cleaning
        self.allowed_tags = []  # No HTML tags allowed
        self.allowed_attributes = {}
        
    def sanitize_content(self, content: str, source_type: str) -> str:
        """Sanitize extracted content based on source type."""
        
        if not content:
            return ""
        
        # 1. Remove null bytes and control characters
        content = content.replace('\x00', '').replace('\r', '\n')
        
        # 2. Clean HTML/markup if present
        content = bleach.clean(content, tags=self.allowed_tags, attributes=self.allowed_attributes)
        
        # 3. Normalize whitespace
        content = ' '.join(content.split())
        
        # 4. Type-specific cleaning
        if source_type in ['json']:
            content = self._sanitize_json_content(content)
        elif source_type in ['log']:
            content = self._sanitize_log_content(content)
        
        # 5. Remove potentially dangerous patterns
        content = self._remove_suspicious_patterns(content)
        
        return content
    
    def _remove_suspicious_patterns(self, content: str) -> str:
        """Remove potentially dangerous code patterns."""
        import re
        
        # Remove script tags and their content
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove eval/exec patterns
        content = re.sub(r'\beval\s*\([^)]*\)', '[REMOVED:EVAL]', content)
        content = re.sub(r'\bexec\s*\([^)]*\)', '[REMOVED:EXEC]', content)
        
        return content
```

## UI/UX Implementation Guide

### Theme Integration

```python
class FineTuningToolbarStyleProvider:
    """Theme-aware styling for file components"""
    
    def __init__(self, theme_manager):
        self.theme_manager = theme_manager
    
    def get_toolbar_stylesheet(self) -> str:
        """Get theme-aware toolbar stylesheet."""
        colors = self.theme_manager.current_theme
        
        return f"""
        FineTuningToolbar {{
            background-color: {colors.background_secondary};
            border: 1px solid {colors.border_secondary};
            border-radius: 8px;
            margin: 4px;
        }}
        
        FineTuningToolbar[expanded="true"] {{
            min-height: 200px;
            max-height: 400px;
        }}
        
        FineTuningToolbar[expanded="false"] {{
            height: 40px;
        }}
        
        .toolbar-header {{
            background-color: {colors.background_tertiary};
            color: {colors.text_primary};
            padding: 8px 12px;
            font-weight: bold;
        }}
        
        .file-count-badge {{
            background-color: {colors.primary};
            color: {colors.text_primary};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
        }}
        """
    
    def get_file_card_stylesheet(self) -> str:
        """Get theme-aware file card stylesheet."""
        colors = self.theme_manager.current_theme
        
        return f"""
        FileCard {{
            background-color: {colors.background_primary};
            border: 1px solid {colors.border_primary};
            border-radius: 6px;
            margin: 4px;
            padding: 8px;
        }}
        
        FileCard:hover {{
            border-color: {colors.primary};
            background-color: {colors.background_secondary};
        }}
        
        .file-name {{
            color: {colors.text_primary};
            font-weight: 500;
        }}
        
        .file-size {{
            color: {colors.text_secondary};
            font-size: 11px;
        }}
        
        .status-processing {{
            color: {colors.status_info};
        }}
        
        .status-success {{
            color: {colors.status_success};
        }}
        
        .status-error {{
            color: {colors.status_error};
        }}
        
        QProgressBar {{
            border: 1px solid {colors.border_secondary};
            border-radius: 3px;
            background-color: {colors.background_tertiary};
            height: 8px;
        }}
        
        QProgressBar::chunk {{
            background-color: {colors.primary};
            border-radius: 2px;
        }}
        """
```

### Accessibility Implementation

```python
class AccessibleFileCard(QWidget):
    """File card with full accessibility support"""
    
    def __init__(self, file_info: FileInfo, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.setup_accessibility()
        self.setup_ui()
        self.setup_keyboard_navigation()
    
    def setup_accessibility(self):
        """Setup accessibility attributes and ARIA properties."""
        # Set accessible name and description
        self.setAccessibleName(f"File: {self.file_info.name}")
        self.setAccessibleDescription(
            f"File {self.file_info.name}, size {self.file_info.size_mb:.1f}MB, "
            f"type {self.file_info.type}, status {self.file_info.status}"
        )
        
        # Enable focus and tab navigation
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        
        # Set role for screen readers
        self.setAccessibleRole(QAccessible.Role.ListItem)
    
    def setup_keyboard_navigation(self):
        """Setup keyboard shortcuts and navigation."""
        # Delete key to remove file
        delete_action = QAction("Remove file", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.request_removal)
        self.addAction(delete_action)
        
        # Space/Enter to show file details
        details_action = QAction("Show details", self)
        details_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        details_action.triggered.connect(self.show_details)
        self.addAction(details_action)
    
    def focusInEvent(self, event):
        """Handle focus events for accessibility."""
        super().focusInEvent(event)
        # Announce status change to screen readers
        self.setAccessibleDescription(
            f"File {self.file_info.name}, currently focused, "
            f"status {self.file_info.status}. Press Delete to remove, Space for details."
        )
    
    def update_status(self, new_status: str, message: str = ""):
        """Update status with accessibility announcements."""
        old_status = self.file_info.status
        self.file_info.status = new_status
        
        # Update UI
        self._update_status_ui(new_status, message)
        
        # Announce to screen readers if focused
        if self.hasFocus():
            announcement = f"File {self.file_info.name} status changed from {old_status} to {new_status}"
            if message:
                announcement += f". {message}"
            
            # Use QAccessible to announce status change
            QAccessible.updateAccessibility(
                QAccessibleEvent(QAccessible.Event.Alert, self, 0)
            )
```

## Testing Strategy

### Unit Testing Framework

```python
# tests/test_file_processing_service.py
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from ghostman.src.infrastructure.files.file_processing_service import FileProcessingService

class TestFileProcessingService:
    
    @pytest.fixture
    def service(self):
        return FileProcessingService()
    
    @pytest.fixture
    def sample_pdf(self):
        """Create a sample PDF file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            # Write minimal PDF content
            f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n')
            f.write(b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n')
            f.write(b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj\n')
            f.write(b'4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\n')
            f.write(b'xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n')
            f.write(b'0000000074 00000 n\n0000000120 00000 n\n0000000179 00000 n\n')
            f.write(b'trailer<</Size 5/Root 1 0 R>>\nstartxref\n271\n%%EOF')
            return f.name
    
    @pytest.mark.asyncio
    async def test_process_valid_pdf(self, service, sample_pdf):
        """Test processing a valid PDF file."""
        result = await service.process_file(sample_pdf)
        
        assert result.success is True
        assert result.content is not None
        assert result.metadata['file_type'] == 'pdf'
        assert result.metadata['file_size'] > 0
    
    @pytest.mark.asyncio
    async def test_process_invalid_file(self, service):
        """Test processing a non-existent file."""
        result = await service.process_file("/nonexistent/file.pdf")
        
        assert result.success is False
        assert "does not exist" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_file_size_validation(self, service):
        """Test file size validation."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            # Write content exceeding text file limit
            large_content = 'x' * (11 * 1024 * 1024)  # 11MB > 10MB limit
            f.write(large_content.encode())
            f.flush()
            
            result = await service.validate_file(f.name)
            assert result.success is False
            assert "too large" in result.error.lower()
    
    @patch('magic.Magic')
    def test_mime_type_validation(self, mock_magic, service):
        """Test MIME type validation."""
        # Mock magic to return invalid MIME type
        mock_magic_instance = Mock()
        mock_magic_instance.from_file.return_value = 'application/x-executable'
        mock_magic.return_value = mock_magic_instance
        
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(b'fake pdf content')
            f.flush()
            
            result = service.validate_file(f.name)
            assert result.success is False
            assert "Invalid MIME type" in result.error
```

### Integration Testing

```python
# tests/integration/test_openai_integration.py
import pytest
from unittest.mock import Mock, patch
import responses

from ghostman.src.infrastructure.ai.api_client import OpenAICompatibleClient
from ghostman.src.infrastructure.files.file_upload_service import FileUploadService

class TestOpenAIIntegration:
    
    @pytest.fixture
    def api_client(self):
        return OpenAICompatibleClient(
            base_url="https://api.openai.com/v1",
            api_key="test-key"
        )
    
    @pytest.fixture
    def upload_service(self, api_client):
        return FileUploadService(api_client)
    
    @responses.activate
    def test_file_upload(self, api_client):
        """Test file upload to OpenAI API."""
        # Mock successful upload response
        responses.add(
            responses.POST,
            "https://api.openai.com/v1/files",
            json={
                "id": "file-abc123",
                "object": "file",
                "bytes": 1024,
                "created_at": 1677649963,
                "filename": "test.pdf",
                "purpose": "assistants"
            },
            status=200
        )
        
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(b'test content')
            f.flush()
            
            result = api_client.upload_file(f.name)
            
            assert result.success is True
            assert result.data['id'] == 'file-abc123'
            assert result.data['filename'] == 'test.pdf'
    
    @responses.activate
    def test_vector_store_creation(self, api_client):
        """Test vector store creation."""
        responses.add(
            responses.POST,
            "https://api.openai.com/v1/vector_stores",
            json={
                "id": "vs-abc123",
                "object": "vector_store",
                "name": "Test Store",
                "file_counts": {"completed": 1, "failed": 0}
            },
            status=200
        )
        
        result = api_client.create_vector_store("Test Store", ["file-abc123"])
        
        assert result.success is True
        assert result.data['id'] == 'vs-abc123'
        assert result.data['name'] == 'Test Store'
```

### UI Testing

```python
# tests/ui/test_fine_tuning_toolbar.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from ghostman.src.presentation.widgets.fine_tuning_toolbar import FineTuningToolbar

class TestFineTuningToolbar:
    
    @pytest.fixture
    def app(self):
        return QApplication.instance() or QApplication([])
    
    @pytest.fixture
    def toolbar(self, app):
        return FineTuningToolbar()
    
    def test_initial_state(self, toolbar):
        """Test toolbar initial state."""
        assert toolbar.expanded is False
        assert len(toolbar.files) == 0
        assert toolbar.isVisible() is False
    
    def test_add_files(self, toolbar):
        """Test adding files to toolbar."""
        test_files = ['/path/to/test1.pdf', '/path/to/test2.docx']
        
        toolbar.add_files(test_files)
        
        assert len(toolbar.files) == 2
        assert toolbar.expanded is True
        assert toolbar.isVisible() is True
    
    def test_remove_file(self, toolbar):
        """Test removing a file."""
        toolbar.add_files(['/path/to/test.pdf'])
        assert len(toolbar.files) == 1
        
        toolbar.remove_file('/path/to/test.pdf')
        
        assert len(toolbar.files) == 0
        assert toolbar.expanded is False
    
    def test_expand_collapse(self, toolbar):
        """Test toolbar expansion and collapse."""
        toolbar.add_files(['/path/to/test.pdf'])
        
        # Should be expanded after adding files
        assert toolbar.expanded is True
        
        # Test collapse
        toolbar.collapse()
        assert toolbar.expanded is False
        
        # Test expand
        toolbar.expand()
        assert toolbar.expanded is True
    
    def test_keyboard_navigation(self, toolbar, qtbot):
        """Test keyboard navigation."""
        toolbar.add_files(['/path/to/test.pdf'])
        toolbar.show()
        
        # Focus on toolbar
        toolbar.setFocus()
        qtbot.keyPress(toolbar, Qt.Key.Key_Tab)
        
        # Should navigate to first file card
        file_cards = toolbar.findChildren(FileCard)
        assert len(file_cards) == 1
        assert file_cards[0].hasFocus()
```

## Performance Optimization

### Asynchronous Processing

```python
class PerformanceOptimizedProcessor:
    """Optimized file processing with async/await and concurrency."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.processing_semaphore = asyncio.Semaphore(max_workers)
        self.upload_queue = asyncio.Queue(maxsize=50)
        
    async def process_files_batch(self, file_paths: List[str]) -> List[ProcessingResult]:
        """Process multiple files concurrently with controlled concurrency."""
        
        async def process_single_file_limited(file_path: str) -> ProcessingResult:
            async with self.processing_semaphore:
                return await self._process_single_file(file_path)
        
        # Create tasks for all files
        tasks = [process_single_file_limited(fp) for fp in file_paths]
        
        # Process with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            results.append(result)
            
            # Emit progress
            progress = (i / len(tasks)) * 100
            await self._emit_progress(f"Processing files: {i}/{len(tasks)}", progress)
        
        return results
    
    async def _process_single_file(self, file_path: str) -> ProcessingResult:
        """Process single file with memory optimization."""
        try:
            # Use streaming for large files
            if Path(file_path).stat().st_size > 50 * 1024 * 1024:  # >50MB
                return await self._process_large_file_streaming(file_path)
            else:
                return await self._process_regular_file(file_path)
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return ProcessingResult(success=False, error=str(e), file_path=file_path)
    
    async def _process_large_file_streaming(self, file_path: str) -> ProcessingResult:
        """Process large files using streaming to manage memory."""
        chunk_size = 1024 * 1024  # 1MB chunks
        content_parts = []
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(chunk_size):
                # Process chunk and add to content
                processed_chunk = await self._process_chunk(chunk)
                content_parts.append(processed_chunk)
                
                # Allow other tasks to run
                await asyncio.sleep(0)
        
        return ProcessingResult(
            success=True,
            content=''.join(content_parts),
            file_path=file_path
        )
```

### Caching Strategy

```python
class IntelligentCache:
    """Multi-layer caching for file processing results."""
    
    def __init__(self, cache_dir: Path, max_size_gb: float = 1.0):
        self.cache_dir = cache_dir
        self.max_size_bytes = int(max_size_gb * 1024**3)
        self.memory_cache = {}
        self.memory_cache_max_items = 100
        
    async def get(self, file_path: str) -> Optional[ProcessingResult]:
        """Get cached result with LRU eviction."""
        cache_key = self._get_cache_key(file_path)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            # Move to end (most recently used)
            result = self.memory_cache.pop(cache_key)
            self.memory_cache[cache_key] = result
            return result
        
        # Check disk cache
        disk_result = await self._get_from_disk(cache_key)
        if disk_result:
            # Store in memory cache
            await self._store_in_memory(cache_key, disk_result)
            return disk_result
        
        return None
    
    async def set(self, file_path: str, result: ProcessingResult):
        """Store result in cache with size management."""
        cache_key = self._get_cache_key(file_path)
        
        # Store in memory cache
        await self._store_in_memory(cache_key, result)
        
        # Store in disk cache
        await self._store_on_disk(cache_key, result)
        
        # Manage cache size
        await self._cleanup_if_needed()
    
    async def _store_in_memory(self, key: str, result: ProcessingResult):
        """Store in memory with LRU eviction."""
        # Remove oldest if at capacity
        if len(self.memory_cache) >= self.memory_cache_max_items:
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
        
        self.memory_cache[key] = result
    
    async def _cleanup_if_needed(self):
        """Clean up cache if it exceeds size limit."""
        total_size = sum(
            Path(f).stat().st_size 
            for f in self.cache_dir.glob('*.cache')
            if f.exists()
        )
        
        if total_size > self.max_size_bytes:
            # Remove oldest cache files
            cache_files = [
                (f, f.stat().st_mtime) 
                for f in self.cache_dir.glob('*.cache')
            ]
            cache_files.sort(key=lambda x: x[1])  # Sort by modification time
            
            removed_size = 0
            target_size = total_size - self.max_size_bytes
            
            for cache_file, _ in cache_files:
                if removed_size >= target_size:
                    break
                
                file_size = cache_file.stat().st_size
                cache_file.unlink()
                removed_size += file_size
                
                logger.info(f"Removed cache file: {cache_file.name}")
```

## Deployment & Installation

### Installation Requirements

```python
# requirements_file_retrieval.txt (additions to existing requirements.txt)

# File processing libraries
pypdf==4.2.0                    # PDF extraction
python-docx==1.1.0             # Word document processing  
python-pptx==0.6.23            # PowerPoint processing
python-magic==0.4.27           # MIME type detection
python-magic-bin==0.4.14       # Windows binary for python-magic

# Content sanitization
bleach==6.1.0                  # HTML/content sanitization

# Async file operations
aiofiles==23.2.1               # Async file I/O

# Character encoding detection
chardet==5.2.0                 # Encoding detection

# Windows shell integration
pywin32==306; sys_platform=="win32"  # Windows API access

# Cross-platform file watching
watchdog==4.0.0                # File system monitoring

# Performance monitoring
psutil==5.9.5                  # System resource monitoring
```

### Database Schema Changes

```sql
-- Add file management tables to existing Ghostman database

-- File registry table
CREATE TABLE IF NOT EXISTS file_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_type TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    openai_file_id TEXT,
    vector_store_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Vector store registry
CREATE TABLE IF NOT EXISTS vector_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vector_store_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    file_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File-vector store relationships
CREATE TABLE IF NOT EXISTS file_vector_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_registry_id INTEGER NOT NULL,
    vector_store_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_registry_id) REFERENCES file_registry(id) ON DELETE CASCADE,
    FOREIGN KEY (vector_store_id) REFERENCES vector_stores(id) ON DELETE CASCADE,
    UNIQUE(file_registry_id, vector_store_id)
);

-- Processing logs
CREATE TABLE IF NOT EXISTS file_processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_registry_id INTEGER NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_registry_id) REFERENCES file_registry(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_file_registry_hash ON file_registry(file_hash);
CREATE INDEX IF NOT EXISTS idx_file_registry_openai_id ON file_registry(openai_file_id);
CREATE INDEX IF NOT EXISTS idx_vector_stores_status ON vector_stores(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_file_id ON file_processing_logs(file_registry_id);
```

### Configuration Management

```python
# ghostman/src/infrastructure/files/config.py

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

@dataclass
class FileRetrievalConfig:
    """Configuration for file retrieval system."""
    
    # File processing
    max_file_size_mb: Dict[str, int] = None
    supported_extensions: List[str] = None
    cache_dir: Path = None
    cache_ttl_hours: int = 24
    cache_max_size_gb: float = 1.0
    
    # Upload settings
    upload_timeout_seconds: int = 300
    max_concurrent_uploads: int = 3
    chunk_size_mb: int = 10
    
    # Vector store settings
    default_vector_store_name: str = "Ghostman Documents"
    vector_store_expires_days: int = 30
    max_vector_stores: int = 5
    
    # Security settings
    enable_content_scanning: bool = True
    quarantine_suspicious_files: bool = True
    allow_executable_content: bool = False
    
    # UI settings
    show_toolbar_by_default: bool = False
    max_files_in_toolbar: int = 20
    enable_drag_drop: bool = True
    enable_send_to_integration: bool = True
    
    def __post_init__(self):
        if self.max_file_size_mb is None:
            self.max_file_size_mb = {
                'pdf': 100,
                'docx': 50,
                'pptx': 100,
                'txt': 10,
                'md': 10,
                'json': 10,
                'log': 50
            }
        
        if self.supported_extensions is None:
            self.supported_extensions = [
                '.pdf', '.docx', '.pptx', '.txt', '.md', '.json', '.log'
            ]
        
        if self.cache_dir is None:
            self.cache_dir = Path.home() / '.ghostman' / 'file_cache'

class FileRetrievalSettings:
    """Manage file retrieval settings integration."""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self._config = None
    
    @property
    def config(self) -> FileRetrievalConfig:
        """Get current configuration."""
        if self._config is None:
            self._load_config()
        return self._config
    
    def _load_config(self):
        """Load configuration from settings manager."""
        file_settings = self.settings_manager.get_category('file_retrieval', {})
        self._config = FileRetrievalConfig(**file_settings)
    
    def save_config(self):
        """Save current configuration."""
        config_dict = {
            k: v for k, v in self._config.__dict__.items()
            if not k.startswith('_')
        }
        self.settings_manager.set_category('file_retrieval', config_dict)
        self.settings_manager.save()
```

## Operations & Maintenance

### Monitoring & Diagnostics

```python
class FileRetrievalMonitor:
    """Monitor file retrieval system health and performance."""
    
    def __init__(self):
        self.metrics = {
            'files_processed': 0,
            'files_failed': 0,
            'total_processing_time': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'upload_successes': 0,
            'upload_failures': 0,
            'vector_stores_created': 0,
            'api_errors': 0
        }
        
        self.logger = logging.getLogger("ghostman.file_retrieval.monitor")
    
    def record_file_processed(self, processing_time_ms: int):
        """Record successful file processing."""
        self.metrics['files_processed'] += 1
        self.metrics['total_processing_time'] += processing_time_ms
    
    def record_file_failed(self, error: str):
        """Record file processing failure."""
        self.metrics['files_failed'] += 1
        self.logger.warning(f"File processing failed: {error}")
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.metrics['cache_misses'] += 1
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        total_files = self.metrics['files_processed'] + self.metrics['files_failed']
        
        if total_files > 0:
            success_rate = (self.metrics['files_processed'] / total_files) * 100
            avg_processing_time = self.metrics['total_processing_time'] / self.metrics['files_processed']
        else:
            success_rate = 100.0
            avg_processing_time = 0
        
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (self.metrics['cache_hits'] / cache_total * 100) if cache_total > 0 else 0
        
        return {
            'status': 'healthy' if success_rate > 90 else 'warning' if success_rate > 70 else 'critical',
            'files_processed': self.metrics['files_processed'],
            'files_failed': self.metrics['files_failed'],
            'success_rate_percent': round(success_rate, 2),
            'average_processing_time_ms': round(avg_processing_time, 2),
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'upload_success_rate': self._calculate_upload_success_rate(),
            'api_error_count': self.metrics['api_errors']
        }
    
    def _calculate_upload_success_rate(self) -> float:
        """Calculate upload success rate."""
        total_uploads = self.metrics['upload_successes'] + self.metrics['upload_failures']
        if total_uploads == 0:
            return 100.0
        return (self.metrics['upload_successes'] / total_uploads) * 100
```

### Maintenance Scripts

```python
# scripts/maintenance/cleanup_file_cache.py

async def cleanup_file_cache(cache_dir: Path, max_age_days: int = 7):
    """Clean up old cache files."""
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    
    removed_count = 0
    removed_size = 0
    
    for cache_file in cache_dir.glob('*.cache'):
        if cache_file.stat().st_mtime < cutoff_time.timestamp():
            file_size = cache_file.stat().st_size
            cache_file.unlink()
            removed_count += 1
            removed_size += file_size
    
    print(f"Removed {removed_count} cache files, freed {removed_size / 1024**2:.1f}MB")

# scripts/maintenance/sync_openai_files.py

async def sync_openai_files(api_client: OpenAICompatibleClient, db_manager):
    """Synchronize local file registry with OpenAI files."""
    
    # Get files from OpenAI
    response = api_client.list_files(purpose="assistants")
    if not response.success:
        print(f"Failed to list files: {response.error}")
        return
    
    openai_files = {f['id']: f for f in response.data.get('data', [])}
    
    # Get local file registry
    local_files = db_manager.get_all_files()
    local_openai_ids = {f.openai_file_id for f in local_files if f.openai_file_id}
    
    # Find orphaned files (in local registry but not on OpenAI)
    orphaned_ids = local_openai_ids - set(openai_files.keys())
    if orphaned_ids:
        print(f"Found {len(orphaned_ids)} orphaned files in local registry")
        for file_id in orphaned_ids:
            # Mark as removed in local registry
            db_manager.mark_file_removed(file_id)
    
    # Find untracked files (on OpenAI but not in local registry)
    untracked_ids = set(openai_files.keys()) - local_openai_ids
    if untracked_ids:
        print(f"Found {len(untracked_ids)} untracked files on OpenAI")
        # Could add option to import or clean up these files

if __name__ == "__main__":
    import asyncio
    asyncio.run(cleanup_file_cache(Path.home() / '.ghostman' / 'file_cache'))
```

---

## Conclusion

This comprehensive implementation plan provides a roadmap for building a robust, secure, and user-friendly file retrieval system for Ghostman. The plan addresses all technical requirements while maintaining integration with the existing architecture and user experience patterns.

**Key Success Factors:**
1. **Incremental Development**: 5-phase approach allows for continuous testing and user feedback
2. **Security First**: Comprehensive validation and sanitization prevent security issues
3. **Performance Optimized**: Async processing and intelligent caching ensure responsiveness
4. **User-Centric Design**: Seamless integration with existing workflows and accessibility compliance
5. **Maintainable Architecture**: Clear separation of concerns and comprehensive testing

The system will enhance Ghostman's AI capabilities while maintaining the elegant, desktop-first experience that users expect.