# OpenAI Files API Integration for Ghostman

This document outlines the comprehensive implementation of OpenAI Files API integration for the Ghostman File Retrieval System.

## Overview

The integration provides full support for:
- **File Upload API**: Direct upload to OpenAI with progress tracking
- **Vector Store Management**: Create, manage, and query vector stores
- **Enhanced Chat Completion**: Chat with file_search tool integration
- **File Management**: List, delete, and synchronize files
- **Async Operations**: Non-blocking operations for UI responsiveness
- **Error Handling**: Robust error handling with retry logic

## Architecture

### Core Components

1. **`file_models.py`** - Data models and type definitions
2. **`api_client.py`** - Extended OpenAI-compatible client with Files API
3. **`file_service.py`** - High-level file management service
4. **`file_integration_example.py`** - Example integration with existing AI service

### Integration with Existing Infrastructure

The implementation seamlessly integrates with:
- ✅ **Existing `OpenAICompatibleClient`** - Extended with file operations
- ✅ **Session Manager** - Reuses connection pooling and PKI support
- ✅ **AI Service** - Compatible with existing conversation management
- ✅ **Settings System** - Uses existing configuration management
- ✅ **Logging System** - Consistent logging throughout

## Key Features Implemented

### 1. File Upload with Progress Tracking

```python
# Async file upload with progress callbacks
result = await client.upload_file_async(
    file_path="document.pdf",
    purpose="assistants",
    progress_callback=lambda progress: print(f"{progress.percentage:.1f}%")
)
```

**Features:**
- Real-time progress tracking
- Support for large files (up to 512MB)
- Automatic file validation
- Fallback when `requests-toolbelt` not available
- Error handling with cleanup

### 2. Vector Store Management

```python
# Create vector store with files
vector_store = await client.create_vector_store_async(
    name="Knowledge Base",
    file_ids=["file-123", "file-456"],
    metadata={"project": "ghostman"}
)

# List vector stores
stores = await client.list_vector_stores_async(limit=10)

# Add files to existing vector store
await client.add_file_to_vector_store_async(
    vector_store_id="vs-123",
    file_id="file-789"
)
```

**Features:**
- Full lifecycle management
- Metadata support
- File association management
- Status monitoring
- Expiration policies

### 3. Enhanced Chat Completion with File Search

```python
# Chat with file search
response = await client.chat_completion_with_file_search_async(
    messages=[{"role": "user", "content": "What does the document say about X?"}],
    model="gpt-4",
    vector_store_ids=["vs-123"],
    ranking_options={"score_threshold": 0.7}
)
```

**Features:**
- Automatic tool configuration
- File search result extraction
- Ranking options support
- Integration with existing chat flow

### 4. Comprehensive Error Handling

**OpenAI-Specific Error Types:**
- `FileUploadError` - File upload specific errors
- `VectorStoreError` - Vector store operation errors
- Enhanced rate limiting with retry-after headers
- Detailed error logging and reporting

**Retry Logic:**
- Exponential backoff for server errors
- Rate limit respect with proper delays
- Timeout handling for large uploads
- Network error recovery

### 5. Async Operations

All file operations have async versions:
- `upload_file_async()`
- `list_files_async()`
- `create_vector_store_async()`
- `chat_completion_with_file_search_async()`

**Benefits:**
- Non-blocking UI operations
- Concurrent file uploads
- Background processing
- Progress updates during operations

## Data Models

### File Models
- **`OpenAIFile`** - Represents uploaded files
- **`VectorStore`** - Vector store with metadata
- **`VectorStoreFile`** - Files within vector stores
- **`FileUploadProgress`** - Upload progress tracking
- **`FileOperationResult`** - Standardized operation results

### Tool Integration
- **`FileSearchTool`** - File search tool configuration
- **`ToolResources`** - Tool resources for chat completion
- **`FileSearchResult`** - Search result representation

## Usage Examples

### Basic File Upload

```python
from ghostman.src.infrastructure.ai.api_client import OpenAICompatibleClient
from ghostman.src.infrastructure.ai.file_models import FileUploadProgress

# Initialize client
client = OpenAICompatibleClient(
    base_url="https://api.openai.com/v1",
    api_key="your-api-key"
)

# Upload with progress tracking
def on_progress(progress: FileUploadProgress):
    print(f"Uploading {progress.file_path}: {progress.percentage:.1f}%")

result = await client.upload_file_async(
    file_path="document.pdf",
    purpose="assistants",
    progress_callback=on_progress
)

if result.success:
    print(f"File uploaded: {result.data.id}")
else:
    print(f"Upload failed: {result.error}")
```

### Knowledge Base Creation

```python
from ghostman.src.infrastructure.ai.file_service import FileService

# Initialize file service
file_service = FileService(client)

# Create knowledge base from documents
kb_result = await file_service.create_vector_store_with_files_async(
    name="Project Documentation",
    file_paths=["doc1.pdf", "doc2.md", "doc3.txt"],
    metadata={"project": "ghostman", "version": "1.0"}
)

if kb_result.success:
    vector_store_id = kb_result.data.id
    print(f"Knowledge base created: {vector_store_id}")
```

### Chat with Documents

```python
# Chat with file search enabled
messages = [
    {"role": "user", "content": "What are the main features described?"}
]

response = await client.chat_completion_with_file_search_async(
    messages=messages,
    model="gpt-4",
    vector_store_ids=[vector_store_id],
    temperature=0.7
)

if response.success:
    # Extract response and sources
    assistant_message = response.data["choices"][0]["message"]["content"]
    print(f"AI Response: {assistant_message}")
    
    # Check for file search results
    tool_calls = response.data["choices"][0]["message"].get("tool_calls", [])
    for tool_call in tool_calls:
        if tool_call["type"] == "file_search":
            print("Sources found in files:")
            # Process file search results
```

### Integration with Existing AI Service

```python
from ghostman.src.infrastructure.ai.file_integration_example import GhostmanFileIntegration

# Extend existing AI service with file capabilities
ai_service = AIService()  # Your existing AI service
ai_service.initialize()

# Create file integration
file_integration = GhostmanFileIntegration(ai_service)

# Upload documents and chat
upload_result = await file_integration.upload_documents_async([
    "document1.pdf", "document2.txt"
])

if upload_result["success"]:
    # Create knowledge base
    kb_result = await file_integration.create_knowledge_base_async(
        name="My Documents",
        document_paths=["document1.pdf", "document2.txt"]
    )
    
    # Chat with documents
    chat_result = await file_integration.chat_with_documents_async(
        message="Summarize the key points from these documents",
        vector_store_ids=[kb_result["vector_store_id"]]
    )
    
    print(f"AI Response: {chat_result['response']}")
    if "sources" in chat_result:
        print(f"Based on {len(chat_result['sources'])} sources")
```

## File Support

### Supported File Types
- **Text**: `.txt`, `.md`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Data**: `.csv`, `.json`, `.jsonl`, `.xml`
- **Web**: `.html`
- **Code**: `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c`, `.h`
- **Config**: `.sql`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`

### File Validation
- Maximum size: 512MB (configurable)
- Automatic extension validation
- File existence checks
- Size calculation for progress tracking

## Configuration

### Dependencies Added
```
requests-toolbelt>=1.0.0  # For file upload progress tracking
```

### Environment Variables
Uses existing Ghostman configuration:
- `ai_model.base_url` - OpenAI API base URL
- `ai_model.api_key` - OpenAI API key
- `ai_model.model_name` - Default model for chat

### PKI Integration
Automatically uses existing PKI configuration when available:
- Client certificate authentication
- CA certificate validation
- Secure file uploads

## Error Handling

### Custom Exception Types
- **`FileUploadError`** - File upload specific issues
- **`VectorStoreError`** - Vector store operation issues
- **Enhanced base exceptions** with OpenAI error type mapping

### Retry Strategies
- **Rate Limiting**: Respects `retry-after` headers
- **Server Errors**: Exponential backoff (1s, 2s, 4s)
- **Network Errors**: Connection retry with delay
- **File Operations**: Cleanup on failure

### Logging
Comprehensive logging at appropriate levels:
- **INFO**: Operation success/failure, progress milestones
- **DEBUG**: Detailed API request/response information
- **ERROR**: Failure details with context
- **WARNING**: Non-fatal issues and fallbacks

## Security Considerations

### File Upload Security
- File extension validation
- Size limit enforcement
- Temporary file cleanup
- Progress callback isolation

### API Security
- Secure credential handling
- PKI client authentication support
- TLS certificate validation
- Request signing (when applicable)

### Data Privacy
- No file content logging
- Secure progress tracking
- Metadata protection
- Clean error messages

## Performance Optimizations

### Connection Pooling
- Reuses existing session manager
- HTTP/2 support where available
- Connection keep-alive
- Request pipelining

### Memory Management
- Streaming file uploads
- Progress callback optimization
- Async operation isolation
- Resource cleanup

### Caching
- Vector store metadata caching
- File list caching
- Connection reuse
- DNS resolution caching

## Testing Recommendations

### Unit Tests
- File validation logic
- Progress callback functionality
- Error handling scenarios
- Data model serialization

### Integration Tests
- End-to-end file upload
- Vector store lifecycle
- Chat with file search
- Error recovery scenarios

### Performance Tests
- Large file upload (>100MB)
- Concurrent operations
- Memory usage monitoring
- Network failure simulation

## Migration Guide

### For Existing Ghostman Users

1. **Install Dependencies**:
   ```bash
   pip install requests-toolbelt>=1.0.0
   ```

2. **Update Imports** (no changes needed to existing code):
   ```python
   # Existing code continues to work unchanged
   from ghostman.src.infrastructure.ai.ai_service import AIService
   
   # New file capabilities available through integration
   from ghostman.src.infrastructure.ai.file_integration_example import GhostmanFileIntegration
   ```

3. **Optional Configuration**:
   ```python
   # Enable file operations (optional)
   ai_service = AIService()
   ai_service.initialize()
   
   # Add file capabilities
   file_integration = GhostmanFileIntegration(ai_service)
   ```

### Backward Compatibility
- ✅ All existing functionality preserved
- ✅ No breaking changes to existing APIs
- ✅ Optional file features
- ✅ Graceful degradation when files not available

## Conclusion

This implementation provides a comprehensive, production-ready integration of OpenAI's Files API with the Ghostman system. It maintains full compatibility with existing infrastructure while adding powerful document-based AI capabilities.

The implementation follows Ghostman's existing patterns for:
- Configuration management
- Error handling and logging
- Session management and PKI support
- Async operations for UI responsiveness

The modular design allows for gradual adoption - existing Ghostman installations continue to work unchanged, while new file capabilities can be enabled as needed.