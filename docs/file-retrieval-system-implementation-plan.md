# Ghostman File Retrieval System - Implementation Plan (API-Only)

## Executive Summary

The Ghostman File Retrieval System will enable users to upload documents (PDF, DOCX, PPTX, TXT, MD, JSON, LOG) directly to OpenAI through the Files API to enhance AI responses through vector stores and assistants API. This document provides a comprehensive implementation plan for integrating direct file upload and AI enhancement capabilities into the existing Ghostman desktop application **without any local file storage or processing**.

### System Goals
- **User Experience**: Seamless file integration via drag-drop, right-click "Send To", and manual selection
- **AI Enhancement**: Document content processed entirely by OpenAI enhances AI responses through vector search
- **Security**: Basic file validation before direct upload to OpenAI
- **Performance**: Efficient direct uploads with progress feedback
- **Integration**: Minimal disruption to existing Ghostman architecture and user workflows
- **Simplicity**: No local file processing, caching, or content extraction - leveraging OpenAI's capabilities

## System Architecture Overview (API-Only)

```
┌─────────────────────────────────────────────────────────────────┐
│                 Ghostman File Retrieval System (API-Only)        │
├─────────────────────────────────────────────────────────────────┤
│  UI Layer (PyQt6)                                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │ FineTuningToolbar│ │FileManagementDlg│ │ FileDropZone        │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
│             │                   │                    │            │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer                                                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │FileValidationSvc│ │ FileUploadSvc   │ │ FineTuningSvc       │  │
│  │- Basic validation│ │- Direct upload  │ │- Vector stores      │  │
│  │- Size/type check │ │- Progress track │ │- Enhanced responses │  │
│  │- Security scan  │ │- OpenAI API     │ │- Context integration│  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
│             │                   │                    │            │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer                                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐  │
│  │  Enhanced       │ │  Extended       │ │ Minimal Metadata    │  │
│  │  AIService      │ │  APIClient      │ │ Database            │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘  │
│             │                   │                    │            │
├─────────────────────────────────────────────────────────────────┤
│  External APIs Only                                               │
│  ┌─────────────────┐ ┌─────────────────┐                         │
│  │ OpenAI Files    │ │ OpenAI Vector   │                         │
│  │ API             │ │ Stores API      │                         │
│  └─────────────────┘ └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture (API-Only)

```
┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   User   │───▶│File Sources │───▶│Basic         │───▶│   OpenAI    │
│          │    │- Drag/Drop  │    │Validation    │    │Direct Upload│
│          │    │- Send To    │    │& Security    │    │& Processing │
│          │    │- Browse     │    │              │    │             │
└──────────┘    └─────────────┘    └──────────────┘    └─────────────┘
                                          │                    │
                                          │                    ▼
┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│Enhanced  │◀───│ AI Service  │◀───│Vector Store  │◀───│ OpenAI File │
│Responses │    │Integration  │    │ Management   │    │Processing & │
└──────────┘    └─────────────┘    └──────────────┘    │  Indexing   │
                                          │            └─────────────┘
                                          ▼
                                  ┌──────────────┐ 
                                  │Store File ID │
                                  │& Metadata    │
                                  │(UI Display)  │
                                  └──────────────┘
```

## Key Design Principles (API-Only)

1. **No Local File Processing**: All content extraction, indexing, and processing happens on OpenAI's servers
2. **Direct Upload Flow**: Files go directly from user selection to OpenAI API
3. **Minimal Local Storage**: Only store OpenAI file IDs and basic metadata for UI display
4. **OpenAI-Native Integration**: Leverage OpenAI's vector stores and file_search tool natively
5. **Simplified Validation**: Basic security and format checks only before upload
6. **API-First Design**: All operations route through OpenAI's APIs

## Component Design Specifications

### 1. FileValidationService (API-Only)

**Location**: `ghostman/src/infrastructure/files/file_validation_service.py`

```python
class FileValidationService:
    """Lightweight file validation service for API-only processing"""
    
    # Supported file types (OpenAI Files API supported formats)
    SUPPORTED_FORMATS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.json': 'application/json',
        '.log': 'text/plain'
    }
    
    # Security validation (based on OpenAI limits)
    MAX_FILE_SIZE = 512 * 1024 * 1024  # 512MB (OpenAI limit)
    
    def __init__(self):
        self.logger = logging.getLogger("ghostman.file_validation")
    
    async def validate_for_upload(self, file_path: str) -> ValidationResult:
        """Validate file before OpenAI upload (no content processing)"""
        
    async def basic_security_scan(self, file_path: str) -> SecurityResult:
        """Basic file security checks before upload"""
        
    def get_file_info(self, file_path: str) -> FileInfo:
        """Get basic file metadata for UI display"""
        
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported by OpenAI"""
```

### 2. FileUploadService (Enhanced for API-Only)

**Location**: `ghostman/src/infrastructure/files/file_upload_service.py`

```python
class FileUploadService:
    """Direct OpenAI API integration for file uploads with no local processing"""
    
    def __init__(self, api_client: OpenAICompatibleClient, validation_service: FileValidationService):
        self.api_client = api_client
        self.validation_service = validation_service
        self.upload_queue = AsyncQueue()
        self.progress_callbacks = {}
        self.active_uploads = {}
    
    async def upload_file_direct(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        """Direct upload to OpenAI after basic validation only"""
        
    async def upload_multiple_files(self, file_paths: List[str]) -> List[UploadResult]:
        """Upload multiple files concurrently"""
        
    async def create_vector_store_from_files(self, name: str, file_paths: List[str]) -> VectorStoreResult:
        """Upload files and create vector store in one operation"""
        
    async def delete_file(self, file_id: str) -> bool:
        """Remove file from OpenAI storage"""
        
    async def list_openai_files(self, purpose: str = None) -> List[OpenAIFileInfo]:
        """List files stored on OpenAI"""
        
    def set_progress_callback(self, file_path: str, callback: Callable):
        """Set progress callback for file upload"""
        
    async def get_upload_status(self, file_path: str) -> UploadStatus:
        """Get current upload status for file"""
```

### 3. FineTuningService (API-Only Integration)

**Location**: `ghostman/src/infrastructure/files/fine_tuning_service.py`

```python
class FineTuningService:
    """AI enhancement through OpenAI file context integration (no local processing)"""
    
    def __init__(self, ai_service: AIService, upload_service: FileUploadService, metadata_db: FileMetadataDB):
        self.ai_service = ai_service
        self.upload_service = upload_service
        self.metadata_db = metadata_db
        self.active_vector_stores = {}
    
    async def integrate_files_direct(self, file_paths: List[str]) -> IntegrationResult:
        """Upload files directly to OpenAI and create vector store"""
        
    async def enhance_chat_completion(self, 
                                    messages: List[dict],
                                    model: str,
                                    **kwargs) -> EnhancedResponse:
        """Chat completion with OpenAI vector store file context"""
        
    async def remove_file_from_openai(self, openai_file_id: str) -> bool:
        """Remove file from OpenAI and update local metadata"""
        
    async def create_vector_store_from_uploaded_files(self, file_ids: List[str], name: str) -> VectorStoreResult:
        """Create vector store from already uploaded OpenAI files"""
        
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current file integration status from OpenAI"""
        
    async def sync_with_openai(self) -> SyncResult:
        """Synchronize local metadata with OpenAI file state"""
```

### 4. UI Components

#### FineTuningToolbar Widget

**Location**: `ghostman/src/presentation/widgets/fine_tuning_toolbar.py`

```python
class FineTuningToolbar(QWidget):
    """Expandable toolbar for file management with upload status"""
    
    files_changed = pyqtSignal(list)  # Emitted when files change
    upload_complete = pyqtSignal(dict)  # Upload results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.expanded = False
        self.upload_service = None
        self.setup_ui()
        self.setup_themes()
    
    def setup_ui(self):
        """Setup toolbar UI components"""
        # Collapsible header with file count
        # File cards grid with upload status
        # Add files button
        # Upload all button
        # Clear all button
        
    def add_files(self, file_paths: List[str]):
        """Add files to toolbar and validate"""
        
    def remove_file(self, file_path: str):
        """Remove file from toolbar"""
        
    async def upload_all_files(self):
        """Upload all files to OpenAI"""
        
    def update_upload_progress(self, file_path: str, progress: float):
        """Update upload progress for file"""
```

#### FileCard Component

```python
class FileCard(QWidget):
    """Individual file representation with upload status and controls"""
    
    remove_requested = pyqtSignal(str)  # File path to remove
    upload_requested = pyqtSignal(str)  # File path to upload
    
    def __init__(self, file_info: FileInfo, parent=None):
        self.file_info = file_info
        self.upload_status = "pending"  # pending, uploading, completed, error
        self.openai_file_id = None
        self.setup_ui()
    
    def update_upload_status(self, status: str, message: str = "", openai_file_id: str = None):
        """Update file upload status"""
        
    def set_upload_progress(self, progress: float):
        """Update upload progress bar"""
        
    def show_upload_error(self, error_message: str):
        """Show upload error state"""
```

## API Integration Details

### OpenAI Files API Integration

#### Extended API Client Methods

```python
# Add to existing OpenAICompatibleClient class in api_client.py

async def upload_file_async(self, file_path: str, purpose: str = "assistants") -> APIResponse:
    """Upload a file to OpenAI for processing with async support."""
    url = f"{self.base_url}/files"
    
    try:
        async with aiofiles.open(file_path, 'rb') as file:
            file_content = await file.read()
            
        files = {
            'file': (os.path.basename(file_path), file_content, 'application/octet-stream'),
            'purpose': (None, purpose)
        }
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Use async HTTP client for upload
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=files, headers=headers) as response:
                response_data = await response.json()
                
                if response.status < 400:
                    return APIResponse(
                        success=True,
                        data=response_data,
                        status_code=response.status
                    )
                else:
                    return APIResponse(
                        success=False,
                        error=response_data.get('error', 'Upload failed'),
                        status_code=response.status
                    )
                    
    except Exception as e:
        return APIResponse(
            success=False,
            error=f"Upload failed: {str(e)}",
            status_code=None
        )

def create_vector_store(self, name: str, file_ids: List[str], expires_days: int = 30) -> APIResponse:
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

def add_files_to_vector_store(self, vector_store_id: str, file_ids: List[str]) -> APIResponse:
    """Add files to existing vector store."""
    data = {"file_ids": file_ids}
    return self._make_request("POST", f"vector_stores/{vector_store_id}/files", data)
```

#### Enhanced Chat Completion with Files

```python
# Add to existing AIService class in ai_service.py

async def send_message_with_files(self, 
                                message: str, 
                                vector_store_id: str = None,
                                stream: bool = False) -> Dict[str, Any]:
    """Send message with OpenAI file context enhancement."""
    
    if not self._initialized:
        logger.error("AI service not initialized")
        return {'success': False, 'error': 'AI service not initialized'}
    
    try:
        # Add user message to conversation
        self.conversation.add_message('user', message)
        
        # Prepare API messages
        api_messages = self.conversation.to_api_format()
        
        # Prepare parameters with file_search tool
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
            
            # Check if file search was used
            usage_info = response.data.get('usage', {})
            file_search_used = 'file_search' in str(usage_info) or any(
                'file_search' in str(choice.get('message', {})) 
                for choice in response.data.get('choices', [])
            )
            
            if file_search_used:
                logger.info("File search was utilized in response generation")
            
            # Add assistant response to conversation
            self.conversation.add_message('assistant', assistant_message)
            
            return {
                'success': True,
                'response': assistant_message,
                'usage': usage_info,
                'file_context_used': bool(vector_store_id or self.active_vector_stores),
                'file_search_used': file_search_used
            }
        else:
            logger.error(f"Enhanced AI API request failed: {response.error}")
            return {'success': False, 'error': response.error}
            
    except Exception as e:
        logger.error(f"Error in enhanced message processing: {e}")
        return {'success': False, 'error': str(e)}
```

## Database Schema Changes (Minimal Metadata Only)

```sql
-- Add minimal file management tables to existing Ghostman database
-- NO local file content storage - only metadata for UI display

-- Minimal file metadata table (UI display only)
CREATE TABLE IF NOT EXISTS file_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_file_path TEXT,  -- For reference only, not used for processing
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_type TEXT NOT NULL,
    openai_file_id TEXT NOT NULL UNIQUE,  -- Primary key for OpenAI operations
    upload_status TEXT DEFAULT 'uploaded', -- 'uploaded', 'processing', 'ready', 'error'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector store registry (OpenAI vector stores)
CREATE TABLE IF NOT EXISTS vector_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openai_vector_store_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    file_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active', -- 'active', 'processing', 'completed', 'expired'
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File-vector store relationships (many-to-many)
CREATE TABLE IF NOT EXISTS file_vector_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_metadata_id INTEGER NOT NULL,
    vector_store_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_metadata_id) REFERENCES file_metadata(id) ON DELETE CASCADE,
    FOREIGN KEY (vector_store_id) REFERENCES vector_stores(id) ON DELETE CASCADE,
    UNIQUE(file_metadata_id, vector_store_id)
);

-- Upload operation logs (for troubleshooting)
CREATE TABLE IF NOT EXISTS upload_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_metadata_id INTEGER,
    operation TEXT NOT NULL, -- 'upload', 'vector_store_create', 'delete'
    status TEXT NOT NULL,    -- 'success', 'error', 'pending'
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_metadata_id) REFERENCES file_metadata(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_file_metadata_openai_id ON file_metadata(openai_file_id);
CREATE INDEX IF NOT EXISTS idx_vector_stores_openai_id ON vector_stores(openai_vector_store_id);
CREATE INDEX IF NOT EXISTS idx_vector_stores_status ON vector_stores(status);
CREATE INDEX IF NOT EXISTS idx_upload_logs_file_id ON upload_logs(file_metadata_id);
```

## Implementation Roadmap (API-Only Approach)

### Phase 1: Foundation & API Integration (Weeks 1-2)
**Deliverables**:
- FileValidationService with basic security checks
- Enhanced OpenAI API client with file endpoints
- Minimal metadata database structure
- Direct upload functionality

**Sprint 1.1**: Core Services Setup
- [ ] Create FileValidationService for pre-upload validation
- [ ] Extend `api_client.py` with OpenAI Files API methods
- [ ] Implement basic file type and size validation
- [ ] Create minimal file metadata database schema

**Sprint 1.2**: Direct Upload Implementation
- [ ] Create FileUploadService for direct OpenAI uploads
- [ ] Add progress tracking and callbacks for uploads
- [ ] Implement retry logic and error recovery
- [ ] Add vector store creation and management

### Phase 2: UI Integration (Weeks 3-4)
**Deliverables**:
- FineTuningToolbar widget
- FileCard components with upload status
- Drag-and-drop integration
- Theme-aware styling

**Sprint 2.1**: Core UI Components
- [ ] Create FineTuningToolbar with expand/collapse
- [ ] Implement FileCard with upload status and progress
- [ ] Add file grid layout and management
- [ ] Create add/remove file actions

**Sprint 2.2**: Integration & Interactions
- [ ] Integrate toolbar with main application
- [ ] Add drag-and-drop support to avatar/REPL
- [ ] Implement file management dialog
- [ ] Add theme-aware styling for all components

### Phase 3: AI Service Enhancement (Weeks 5-6)
**Deliverables**:
- Enhanced AIService with OpenAI file context
- FineTuningService for direct API integration
- Chat completion with vector store support
- Context management via OpenAI

**Sprint 3.1**: AI Integration
- [ ] Create FineTuningService for API-only integration
- [ ] Enhance AIService for OpenAI vector store context
- [ ] Implement chat completion with file_search tool
- [ ] Add vector store management

**Sprint 3.2**: User Experience
- [ ] Add file integration to conversation flow
- [ ] Implement upload status notifications in REPL
- [ ] Add file context indicators in chat
- [ ] Create help and documentation

### Phase 4: Testing & Polish (Weeks 7-8)
**Deliverables**:
- API integration testing suite
- Upload performance optimization
- Cross-platform compatibility
- Production deployment

**Sprint 4.1**: Testing & Quality
- [ ] Unit tests for validation and upload services (>90% coverage)
- [ ] Integration tests for OpenAI API functionality
- [ ] UI tests for all components
- [ ] Upload performance and reliability testing

**Sprint 4.2**: Deployment Preparation
- [ ] Cross-platform testing (Windows/Mac/Linux)
- [ ] Right-click "Send To" integration setup
- [ ] User documentation and help system
- [ ] Error handling and diagnostics

## Installation Requirements (API-Only)

```python
# requirements_file_retrieval.txt (additions to existing requirements.txt)
# Minimal dependencies - no local file processing libraries needed

# Basic file type detection (minimal)
python-magic==0.4.27           # MIME type detection for validation
python-magic-bin==0.4.14       # Windows binary for python-magic

# Async operations for uploads
aiofiles==23.2.1               # Async file reading for uploads
aiohttp==3.8.6                 # Enhanced HTTP client for large file uploads

# Windows shell integration (Send To functionality)
pywin32==306; sys_platform=="win32"  # Windows API access for right-click integration

# Performance monitoring
psutil==5.9.5                  # System resource monitoring for upload progress

# NOTE: Removed dependencies:
# - pypdf, python-docx, python-pptx (no local content extraction)
# - bleach (no content sanitization needed)
# - chardet (not processing content locally)
# - watchdog (no local file monitoring needed)
```

## Security & Validation Framework (API-Only)

### Lightweight File Validation

```python
class BasicFileValidator:
    """Lightweight file validation for API-only processing"""
    
    # OpenAI Files API limits
    MAX_FILE_SIZE = 512 * 1024 * 1024  # 512MB (OpenAI limit)
    
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.txt', '.md', '.json', '.log'}
    
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/markdown', 
        'application/json'
    }
    
    def __init__(self):
        self.file_magic = magic.Magic(mime=True)
        self.logger = logging.getLogger("ghostman.file_validator")
    
    async def validate_for_upload(self, file_path: str) -> ValidationResult:
        """Basic validation before OpenAI upload - no content processing."""
        path = Path(file_path)
        
        try:
            # 1. Basic file existence check
            if not path.exists():
                return ValidationResult(False, "File does not exist", "FILE_NOT_FOUND")
            
            if not path.is_file():
                return ValidationResult(False, "Path is not a file", "INVALID_PATH")
            
            # 2. File size validation (OpenAI limit)
            file_size = path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                return ValidationResult(
                    False, 
                    f"File too large: {actual_mb:.1f}MB (OpenAI limit: {max_mb:.0f}MB)", 
                    "FILE_TOO_LARGE"
                )
            
            # 3. Extension validation
            extension = path.suffix.lower()
            if extension not in self.ALLOWED_EXTENSIONS:
                return ValidationResult(False, f"Unsupported file type: {extension}", "UNSUPPORTED_TYPE")
            
            # 4. Basic MIME type check
            try:
                mime_type = self.file_magic.from_file(str(path))
                if mime_type not in self.ALLOWED_MIME_TYPES and not mime_type.startswith('text/'):
                    self.logger.warning(f"Unusual MIME type for {path.name}: {mime_type}")
                    # Continue - let OpenAI handle it
            except Exception as e:
                self.logger.warning(f"MIME type detection failed for {path.name}: {e}")
                # Continue - let OpenAI handle it
            
            # 5. Basic security check (file header validation)
            security_ok = await self._basic_security_scan(path)
            if not security_ok:
                return ValidationResult(False, "File failed security scan", "SECURITY_THREAT")
            
            self.logger.info(f"✓ File validation passed for upload: {path.name}")
            return ValidationResult(
                True, 
                "File ready for OpenAI upload", 
                "VALID", 
                {
                    'size': file_size,
                    'extension': extension,
                    'file_name': path.name
                }
            )
            
        except Exception as e:
            self.logger.error(f"✗ File validation error for {path.name}: {e}")
            return ValidationResult(False, f"Validation error: {str(e)}", "VALIDATION_ERROR")
    
    async def _basic_security_scan(self, file_path: Path) -> bool:
        """Basic security scan - check file headers and size."""
        try:
            # Read first 1KB for header analysis
            with open(file_path, 'rb') as f:
                header = f.read(1024)
            
            # Check for obvious executable headers
            executable_signatures = [
                b'MZ',          # Windows executable
                b'\\x7fELF',     # Linux executable
                b'\\xfe\\xed',    # Mach-O executable
                b'\\xca\\xfe',    # Java class file
            ]
            
            for sig in executable_signatures:
                if header.startswith(sig):
                    self.logger.warning(f"Executable signature detected: {file_path.name}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Security scan error for {file_path.name}: {e}")
            return False
```

## Testing Strategy (API-Only Focus)

### Unit Testing Framework

```python
# tests/test_file_validation_service.py
import pytest
import tempfile
from pathlib import Path

from ghostman.src.infrastructure.files.file_validation_service import FileValidationService

class TestFileValidationService:
    
    @pytest.fixture
    def service(self):
        return FileValidationService()
    
    @pytest.fixture
    def sample_text_file(self):
        """Create a sample text file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            f.write('This is a test file for upload validation.')
            return f.name
    
    @pytest.mark.asyncio
    async def test_validate_valid_file(self, service, sample_text_file):
        """Test validation of a valid file."""
        result = await service.validate_for_upload(sample_text_file)
        
        assert result.success is True
        assert result.data['file_name'] is not None
        assert result.data['size'] > 0
    
    @pytest.mark.asyncio
    async def test_validate_nonexistent_file(self, service):
        """Test validation of a non-existent file."""
        result = await service.validate_for_upload("/nonexistent/file.txt")
        
        assert result.success is False
        assert "does not exist" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_file_size_validation(self, service):
        """Test file size validation against OpenAI limits."""
        # Create a file that's too large
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            # Write content exceeding 512MB limit (simulate)
            large_content = 'x' * 1024  # Small test - we'll mock the size check
            f.write(large_content.encode())
            f.flush()
            
            # Mock the file size to exceed limit
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 600 * 1024 * 1024  # 600MB
                
                result = await service.validate_for_upload(f.name)
                assert result.success is False
                assert "too large" in result.error.lower()
                assert "openai limit" in result.error.lower()
```

### Integration Testing

```python
# tests/integration/test_openai_upload.py
import pytest
from unittest.mock import Mock, patch
import responses

from ghostman.src.infrastructure.files.file_upload_service import FileUploadService
from ghostman.src.infrastructure.ai.api_client import OpenAICompatibleClient

class TestOpenAIUploadIntegration:
    
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
    def test_direct_file_upload(self, upload_service):
        """Test direct file upload to OpenAI API."""
        # Mock successful upload response
        responses.add(
            responses.POST,
            "https://api.openai.com/v1/files",
            json={
                "id": "file-abc123",
                "object": "file",
                "bytes": 1024,
                "created_at": 1677649963,
                "filename": "test.txt",
                "purpose": "assistants"
            },
            status=200
        )
        
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w') as f:
            f.write('test content for upload')
            f.flush()
            
            result = upload_service.upload_file_direct(f.name)
            
            assert result.success is True
            assert result.openai_file_id == 'file-abc123'
    
    @responses.activate
    def test_vector_store_creation(self, api_client):
        """Test vector store creation with uploaded files."""
        responses.add(
            responses.POST,
            "https://api.openai.com/v1/vector_stores",
            json={
                "id": "vs-abc123",
                "object": "vector_store",
                "name": "Test Documents",
                "file_counts": {"completed": 1, "failed": 0}
            },
            status=200
        )
        
        result = api_client.create_vector_store("Test Documents", ["file-abc123"])
        
        assert result.success is True
        assert result.data['id'] == 'vs-abc123'
        assert result.data['name'] == 'Test Documents'
```

## Performance Optimization (Upload-Focused)

### Optimized Upload Manager

```python
class OptimizedUploadManager:
    """Optimized file upload manager for direct OpenAI API uploads."""
    
    def __init__(self, max_concurrent_uploads: int = 3):
        self.max_concurrent_uploads = max_concurrent_uploads
        self.upload_semaphore = asyncio.Semaphore(max_concurrent_uploads)
        self.upload_queue = asyncio.Queue(maxsize=50)
        self.active_uploads = {}
        
    async def upload_files_batch(self, file_paths: List[str]) -> List[UploadResult]:
        """Upload multiple files concurrently with controlled concurrency."""
        
        async def upload_single_file_limited(file_path: str) -> UploadResult:
            async with self.upload_semaphore:
                return await self._upload_single_file(file_path)
        
        # Create tasks for all files
        tasks = [upload_single_file_limited(fp) for fp in file_paths]
        
        # Upload with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            results.append(result)
            
            # Emit progress
            progress = (i / len(tasks)) * 100
            await self._emit_upload_progress(f"Uploading files: {i}/{len(tasks)}", progress)
        
        return results
    
    async def _upload_single_file(self, file_path: str) -> UploadResult:
        """Upload single file directly to OpenAI with retry logic."""
        max_retries = 3
        retry_delay = 1  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                # Track upload start
                self.active_uploads[file_path] = {
                    'status': 'uploading',
                    'attempt': attempt + 1,
                    'start_time': time.time()
                }
                
                # Perform upload
                result = await self._direct_upload_to_openai(file_path)
                
                if result.success:
                    # Update tracking
                    self.active_uploads[file_path]['status'] = 'completed'
                    return result
                else:
                    # Retry on failure
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        self.active_uploads[file_path]['status'] = 'failed'
                        return result
                        
            except Exception as e:
                logger.error(f"Upload attempt {attempt + 1} failed for {file_path}: {e}")
                if attempt == max_retries - 1:
                    self.active_uploads[file_path]['status'] = 'failed'
                    return UploadResult(success=False, error=str(e), file_path=file_path)
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
```

## Right-Click "Send To" Integration

### Windows Shell Integration

```python
# ghostman/src/platform/windows/shell_integration.py

import os
import winreg
from pathlib import Path

class WindowsShellIntegration:
    """Integrate Ghostman with Windows shell for Send To functionality."""
    
    def __init__(self, app_executable_path: str):
        self.app_path = app_executable_path
        self.send_to_path = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'SendTo'
    
    def install_send_to_shortcut(self) -> bool:
        """Install 'Send to Ghostman' shortcut."""
        try:
            shortcut_path = self.send_to_path / 'Ghostman Files.lnk'
            
            # Create shortcut using Windows COM interface
            import pythoncom
            from win32com.shell import shell, shellcon
            
            shortcut = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink, None,
                pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
            )
            
            shortcut.SetPath(self.app_path)
            shortcut.SetArguments('--files "%1"')  # %1 will be replaced with selected files
            shortcut.SetDescription('Upload files to Ghostman AI')
            shortcut.SetIconLocation(self.app_path, 0)
            
            # Save the shortcut
            persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
            persist_file.Save(str(shortcut_path), 0)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Send To shortcut: {e}")
            return False
    
    def uninstall_send_to_shortcut(self) -> bool:
        """Remove 'Send to Ghostman' shortcut."""
        try:
            shortcut_path = self.send_to_path / 'Ghostman Files.lnk'
            if shortcut_path.exists():
                shortcut_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall Send To shortcut: {e}")
            return False
```

## Error Handling & User Feedback

### Upload Status Management

```python
class UploadStatusManager:
    """Manage upload status and provide user feedback."""
    
    def __init__(self):
        self.upload_statuses = {}
        self.status_callbacks = {}
    
    def register_upload(self, file_path: str, callback: Callable = None):
        """Register a new file upload."""
        self.upload_statuses[file_path] = {
            'status': 'pending',
            'progress': 0.0,
            'error': None,
            'openai_file_id': None,
            'start_time': time.time()
        }
        
        if callback:
            self.status_callbacks[file_path] = callback
    
    def update_upload_progress(self, file_path: str, progress: float):
        """Update upload progress."""
        if file_path in self.upload_statuses:
            self.upload_statuses[file_path]['progress'] = progress
            self.upload_statuses[file_path]['status'] = 'uploading'
            
            if callback := self.status_callbacks.get(file_path):
                callback('progress', progress)
    
    def complete_upload(self, file_path: str, openai_file_id: str):
        """Mark upload as completed."""
        if file_path in self.upload_statuses:
            self.upload_statuses[file_path]['status'] = 'completed'
            self.upload_statuses[file_path]['progress'] = 100.0
            self.upload_statuses[file_path]['openai_file_id'] = openai_file_id
            
            if callback := self.status_callbacks.get(file_path):
                callback('completed', openai_file_id)
    
    def fail_upload(self, file_path: str, error: str):
        """Mark upload as failed."""
        if file_path in self.upload_statuses:
            self.upload_statuses[file_path]['status'] = 'error'
            self.upload_statuses[file_path]['error'] = error
            
            if callback := self.status_callbacks.get(file_path):
                callback('error', error)
```

---

## Conclusion

This revised implementation plan provides a streamlined, API-only approach for the Ghostman File Retrieval System. By leveraging OpenAI's native file processing capabilities, the system becomes:

**Simplified Architecture:**
- No local file processing or caching complexity
- Direct integration with OpenAI Files API
- Minimal local storage requirements

**Enhanced Security:**
- Files processed in OpenAI's secure environment  
- Reduced attack surface with no local content extraction
- Basic validation before upload

**Better Performance:**
- Leverages OpenAI's optimized file processing
- Concurrent upload capabilities
- No local resource constraints for file processing

**Easier Maintenance:**
- Fewer dependencies and libraries
- Simplified testing focused on API integration
- Reduced code complexity

**Key Success Factors:**
1. **API-First Design**: All processing handled by OpenAI
2. **Minimal Local Footprint**: Only UI metadata stored locally
3. **Direct Upload Flow**: Streamlined user experience
4. **Native Integration**: Uses OpenAI's file_search tool natively
5. **Simplified Validation**: Basic checks before trusted API processing

The system will provide powerful AI enhancement capabilities while maintaining the elegant, desktop-first experience that Ghostman users expect, with significantly reduced complexity compared to local processing approaches.