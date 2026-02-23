"""
Enhanced File Processing Error Handler

Provides detailed, context-aware error handling for file processing operations
to replace generic "Unknown error" messages with actionable diagnostics.
"""

import logging
import re
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import chardet

logger = logging.getLogger("specter.enhanced_error_handler")

class FileProcessingError:
    """Represents a detailed file processing error with context and suggestions."""
    
    def __init__(
        self,
        error_type: str,
        error_message: str,
        file_path: Optional[Path] = None,
        suggestions: Optional[List[str]] = None,
        technical_details: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        self.error_message = error_message
        self.file_path = file_path
        self.suggestions = suggestions or []
        self.technical_details = technical_details or {}
        
    def get_user_friendly_message(self) -> str:
        """Get a user-friendly error message with suggestions."""
        msg = f"{self.error_message}"
        
        if self.suggestions:
            msg += "\n\nSuggestions:"
            for suggestion in self.suggestions[:3]:  # Limit to 3 suggestions
                msg += f"\n• {suggestion}"
                
        return msg
    
    def get_technical_summary(self) -> str:
        """Get technical error details for logging."""
        details = []
        details.append(f"Error Type: {self.error_type}")
        details.append(f"File: {self.file_path}")
        details.append(f"Message: {self.error_message}")
        
        if self.technical_details:
            details.append("Technical Details:")
            for key, value in self.technical_details.items():
                details.append(f"  {key}: {value}")
                
        return "\n".join(details)

class EnhancedFileErrorHandler:
    """Enhanced error handler for file processing operations."""
    
    @staticmethod
    def analyze_result_error(result: Dict[str, Any], file_path: Optional[Path] = None) -> FileProcessingError:
        """
        Analyze a processing result and generate detailed error information.
        
        Args:
            result: Processing result dictionary
            file_path: Path to the file being processed
            
        Returns:
            FileProcessingError with detailed context
        """
        # Extract error information
        raw_error = result.get('error', 'No error details provided')
        error_type = result.get('error_type', 'unknown')
        processing_stage = result.get('processing_stage', 'unknown')
        debug_info = result.get('debug_info', {})
        
        # Analyze the error based on type and content
        if 'encoding' in raw_error.lower() or 'decode' in raw_error.lower():
            return EnhancedFileErrorHandler._handle_encoding_error(raw_error, file_path, debug_info)
        elif 'api' in raw_error.lower() or 'request' in raw_error.lower():
            return EnhancedFileErrorHandler._handle_api_error(raw_error, file_path, debug_info)
        elif 'embedding' in raw_error.lower():
            return EnhancedFileErrorHandler._handle_embedding_error(raw_error, file_path, debug_info)
        elif file_path and file_path.name.lower() == 'requirements.txt':
            return EnhancedFileErrorHandler._handle_requirements_error(raw_error, file_path, debug_info)
        elif 'permission' in raw_error.lower() or 'access' in raw_error.lower():
            return EnhancedFileErrorHandler._handle_permission_error(raw_error, file_path, debug_info)
        elif 'not found' in raw_error.lower() or 'missing' in raw_error.lower():
            return EnhancedFileErrorHandler._handle_file_not_found_error(raw_error, file_path, debug_info)
        else:
            return EnhancedFileErrorHandler._handle_generic_error(raw_error, file_path, debug_info, processing_stage)
    
    @staticmethod
    def _handle_encoding_error(raw_error: str, file_path: Optional[Path], debug_info: Dict) -> FileProcessingError:
        """Handle file encoding related errors."""
        suggestions = [
            "The file may contain non-UTF-8 characters",
            "Try saving the file with UTF-8 encoding",
            "Check if the file is corrupted or binary"
        ]
        
        # Try to detect encoding if file exists
        technical_details = {"raw_error": raw_error}
        if file_path and file_path.exists():
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read(1024)  # Read first 1KB for detection
                detection = chardet.detect(raw_data)
                technical_details["detected_encoding"] = detection.get('encoding')
                technical_details["detection_confidence"] = detection.get('confidence')
                
                if detection.get('encoding'):
                    suggestions.insert(0, f"Try converting file to UTF-8 (detected: {detection['encoding']})")
            except Exception as e:
                technical_details["detection_error"] = str(e)
        
        return FileProcessingError(
            error_type="encoding_error",
            error_message="File encoding issue preventing processing",
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )
    
    @staticmethod
    def _handle_api_error(raw_error: str, file_path: Optional[Path], debug_info: Dict) -> FileProcessingError:
        """Handle API related errors."""
        suggestions = []
        technical_details = {"raw_error": raw_error}
        
        if "401" in raw_error or "unauthorized" in raw_error.lower():
            suggestions = [
                "Check if your API key is valid and has the required permissions",
                "Verify the API key is configured correctly in settings",
                "Try refreshing your API key if it has expired"
            ]
            error_message = "API authentication failed - check your API key"
        elif "429" in raw_error or "rate limit" in raw_error.lower():
            suggestions = [
                "Wait a few minutes before trying again",
                "Consider reducing the number of files processed simultaneously",
                "Check your API usage limits"
            ]
            error_message = "API rate limit exceeded - too many requests"
        elif "timeout" in raw_error.lower():
            suggestions = [
                "Try processing a smaller file",
                "Check your internet connection",
                "The API service may be temporarily slow"
            ]
            error_message = "API request timed out"
        elif "500" in raw_error or "502" in raw_error or "503" in raw_error:
            suggestions = [
                "The API service is temporarily unavailable",
                "Try again in a few minutes",
                "Check the service status page"
            ]
            error_message = "API service temporarily unavailable"
        else:
            suggestions = [
                "Check your internet connection",
                "Verify your API configuration",
                "Try processing the file again"
            ]
            error_message = "API request failed"
            
        # Add client metrics if available
        if 'client_metrics' in debug_info:
            technical_details["client_metrics"] = debug_info['client_metrics']
        
        return FileProcessingError(
            error_type="api_error",
            error_message=error_message,
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )
    
    @staticmethod
    def _handle_embedding_error(raw_error: str, file_path: Optional[Path], debug_info: Dict) -> FileProcessingError:
        """Handle embedding generation errors."""
        suggestions = [
            "The file content may be too large for processing",
            "Try breaking the file into smaller sections",
            "Check if the file contains valid text content"
        ]
        
        technical_details = {"raw_error": raw_error}
        
        if 'content_length' in debug_info:
            content_length = debug_info['content_length']
            technical_details["content_length"] = content_length
            if content_length > 100000:  # 100KB
                suggestions.insert(0, f"File is large ({content_length} characters) - consider splitting it")
        
        if 'embedding_attempt_' in str(debug_info):
            attempt_count = len([k for k in debug_info.keys() if k.startswith('embedding_attempt_')])
            technical_details["retry_attempts"] = attempt_count
            suggestions.append(f"Failed after {attempt_count} attempts - there may be a persistent issue")
        
        return FileProcessingError(
            error_type="embedding_error", 
            error_message="Failed to generate embeddings for file content",
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )
    
    @staticmethod
    def _handle_requirements_error(raw_error: str, file_path: Optional[Path], debug_info: Dict) -> FileProcessingError:
        """Handle requirements.txt specific errors."""
        suggestions = [
            "Check for malformed package specifications",
            "Ensure version specifiers use valid syntax (==, >=, etc.)",
            "Remove or fix any invalid lines in the requirements file"
        ]
        
        technical_details = {"raw_error": raw_error}
        
        if 'parse_errors' in debug_info:
            parse_errors = debug_info['parse_errors']
            technical_details["parse_errors"] = parse_errors
            if parse_errors:
                suggestions.insert(0, f"Found {len(parse_errors)} parsing issues in requirements.txt")
                suggestions.append("Check the log for specific line numbers with issues")
        
        if 'valid_requirements' in debug_info:
            valid_count = debug_info['valid_requirements']
            technical_details["valid_requirements"] = valid_count
            if valid_count == 0:
                suggestions.insert(0, "No valid requirements found - check file format")
        
        return FileProcessingError(
            error_type="requirements_parsing_error",
            error_message="Requirements.txt file has formatting issues",
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )
    
    @staticmethod
    def _handle_permission_error(raw_error: str, file_path: Optional[Path], debug_info: Dict) -> FileProcessingError:
        """Handle file permission errors."""
        suggestions = [
            "Check if you have read permissions for the file",
            "Try running the application as administrator (if needed)",
            "Ensure the file is not locked by another application"
        ]
        
        technical_details = {"raw_error": raw_error}
        
        if file_path:
            try:
                technical_details["file_exists"] = file_path.exists()
                technical_details["file_readable"] = file_path.is_file()
                if file_path.exists():
                    stat = file_path.stat()
                    technical_details["file_size"] = stat.st_size
                    technical_details["file_permissions"] = oct(stat.st_mode)[-3:]
            except Exception as e:
                technical_details["permission_check_error"] = str(e)
        
        return FileProcessingError(
            error_type="permission_error",
            error_message="Insufficient permissions to access the file",
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )
    
    @staticmethod
    def _handle_file_not_found_error(raw_error: str, file_path: Optional[Path], debug_info: Dict) -> FileProcessingError:
        """Handle file not found errors."""
        suggestions = [
            "Verify the file path is correct",
            "Check if the file was moved or deleted",
            "Ensure you have permission to access the directory"
        ]
        
        technical_details = {"raw_error": raw_error}
        
        if file_path:
            technical_details["attempted_path"] = str(file_path)
            technical_details["parent_exists"] = file_path.parent.exists() if file_path.parent else False
            
            # Check for similar files in the directory
            if file_path.parent and file_path.parent.exists():
                try:
                    similar_files = [
                        f.name for f in file_path.parent.iterdir()
                        if f.name.lower().startswith(file_path.stem.lower()[:3])
                    ][:3]
                    if similar_files:
                        technical_details["similar_files"] = similar_files
                        suggestions.insert(0, f"Similar files found: {', '.join(similar_files)}")
                except Exception as e:
                    technical_details["directory_scan_error"] = str(e)
        
        return FileProcessingError(
            error_type="file_not_found",
            error_message="File could not be found at the specified location",
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )
    
    @staticmethod
    def _handle_generic_error(raw_error: str, file_path: Optional[Path], debug_info: Dict, processing_stage: str) -> FileProcessingError:
        """Handle generic/unknown errors with detailed context."""
        suggestions = [
            "Try processing the file again",
            "Check if the file is corrupted or in an unsupported format",
            "Review the log files for more detailed error information"
        ]
        
        technical_details = {
            "raw_error": raw_error,
            "processing_stage": processing_stage
        }
        
        # Add all debug info to technical details
        technical_details.update(debug_info)
        
        # Try to extract more context from the error message
        if "memory" in raw_error.lower() or "out of" in raw_error.lower():
            suggestions.insert(0, "The file may be too large - try processing a smaller file")
            technical_details["likely_cause"] = "memory_issue"
        elif "format" in raw_error.lower() or "invalid" in raw_error.lower():
            suggestions.insert(0, "The file format may not be supported")
            technical_details["likely_cause"] = "format_issue"
        elif "connection" in raw_error.lower() or "network" in raw_error.lower():
            suggestions.insert(0, "Check your internet connection and try again")
            technical_details["likely_cause"] = "network_issue"
        
        # Add file information if available
        if file_path and file_path.exists():
            try:
                technical_details["file_size"] = file_path.stat().st_size
                technical_details["file_suffix"] = file_path.suffix
            except Exception:
                pass
        
        error_message = f"File processing failed during {processing_stage} stage"
        if "No error details provided" not in raw_error:
            error_message += f": {raw_error[:100]}{'...' if len(raw_error) > 100 else ''}"
        
        return FileProcessingError(
            error_type="processing_error",
            error_message=error_message,
            file_path=file_path,
            suggestions=suggestions,
            technical_details=technical_details
        )

def get_enhanced_error_message(result: Dict[str, Any], file_path: Optional[Path] = None) -> str:
    """
    Get an enhanced error message to replace 'Unknown error'.
    
    Args:
        result: Processing result dictionary
        file_path: Optional path to the file being processed
        
    Returns:
        User-friendly error message with context
    """
    try:
        error_handler = EnhancedFileErrorHandler()
        file_error = error_handler.analyze_result_error(result, file_path)
        
        # Log technical details for debugging
        logger.error(f"File processing error analysis:\n{file_error.get_technical_summary()}")
        
        return file_error.get_user_friendly_message()
        
    except Exception as e:
        logger.error(f"Error in enhanced error handler: {e}")
        # Fallback to original behavior but with more context
        raw_error = result.get('error', 'Processing failed')
        return f"Processing failed: {raw_error[:200]}{'...' if len(raw_error) > 200 else ''}"