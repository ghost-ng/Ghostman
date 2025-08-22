"""
File Validation Service for Ghostman.

Provides comprehensive file validation capabilities for the file retrieval system,
including file type validation, size limits, format checking, and security validation.
"""

import logging
import os
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger("ghostman.file_validation_service")


@dataclass
class ValidationResult:
    """Result of file validation operation."""
    is_valid: bool
    file_path: str
    file_size: int
    mime_type: Optional[str]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


@dataclass
class ValidationConfig:
    """Configuration for file validation rules."""
    max_file_size: int = 100 * 1024 * 1024  # 100MB default
    allowed_extensions: List[str] = None
    allowed_mime_types: List[str] = None
    blocked_extensions: List[str] = None
    blocked_mime_types: List[str] = None
    require_text_content: bool = False
    max_filename_length: int = 255
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json',
                '.xml', '.yaml', '.yml', '.csv', '.tsv', '.log', '.sql',
                '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore',
                '.pdf', '.doc', '.docx', '.rtf'
            ]
        
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                'text/plain', 'text/markdown', 'text/html', 'text/css',
                'text/javascript', 'text/csv', 'text/xml', 'text/yaml',
                'application/json', 'application/xml', 'application/yaml',
                'application/javascript', 'application/typescript',
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/rtf', 'application/sql'
            ]
        
        if self.blocked_extensions is None:
            self.blocked_extensions = [
                '.exe', '.dll', '.scr', '.bat', '.cmd', '.com', '.pif',
                '.vbs', '.vbe', '.js', '.jar', '.msi', '.hta', '.ws',
                '.wsf', '.wsc', '.wsh', '.ps1', '.ps1xml', '.ps2',
                '.ps2xml', '.psc1', '.psc2', '.msh', '.msh1', '.msh2',
                '.mshxml', '.msh1xml', '.msh2xml'
            ]
        
        if self.blocked_mime_types is None:
            self.blocked_mime_types = [
                'application/x-executable', 'application/x-msdownload',
                'application/x-msdos-program', 'application/x-winexe'
            ]


class FileValidationService:
    """
    Comprehensive file validation service for Ghostman.
    
    Provides validation for file uploads, including:
    - File existence and accessibility
    - File size limitations
    - File type and extension validation
    - MIME type validation
    - Security checks for malicious file types
    - Content validation for text files
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize the file validation service.
        
        Args:
            config: Optional validation configuration. Uses defaults if not provided.
        """
        self.config = config or ValidationConfig()
        logger.info("FileValidationService initialized")
        logger.debug(f"Max file size: {self.config.max_file_size} bytes")
        logger.debug(f"Allowed extensions: {len(self.config.allowed_extensions)}")
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate a single file against all configured rules.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        logger.debug(f"Validating file: {file_path}")
        
        errors = []
        warnings = []
        metadata = {}
        
        try:
            path = Path(file_path)
            
            # Check file existence
            if not path.exists():
                errors.append(f"File does not exist: {file_path}")
                return ValidationResult(
                    is_valid=False,
                    file_path=file_path,
                    file_size=0,
                    mime_type=None,
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )
            
            # Check if it's a file (not directory)
            if not path.is_file():
                errors.append(f"Path is not a file: {file_path}")
                return ValidationResult(
                    is_valid=False,
                    file_path=file_path,
                    file_size=0,
                    mime_type=None,
                    errors=errors,
                    warnings=warnings,
                    metadata=metadata
                )
            
            # Get file size
            file_size = path.stat().st_size
            metadata['file_size'] = file_size
            
            # Check file size
            if file_size > self.config.max_file_size:
                errors.append(
                    f"File size ({file_size} bytes) exceeds maximum "
                    f"allowed size ({self.config.max_file_size} bytes)"
                )
            
            if file_size == 0:
                warnings.append("File is empty")
            
            # Check filename length
            if len(path.name) > self.config.max_filename_length:
                errors.append(
                    f"Filename too long ({len(path.name)} chars). "
                    f"Maximum: {self.config.max_filename_length}"
                )
            
            # Get file extension and MIME type
            file_extension = path.suffix.lower()
            mime_type, _ = mimetypes.guess_type(file_path)
            
            metadata['file_extension'] = file_extension
            metadata['mime_type'] = mime_type
            metadata['filename'] = path.name
            
            # Check extension against blocked list
            if file_extension in self.config.blocked_extensions:
                errors.append(f"File extension '{file_extension}' is blocked for security reasons")
            
            # Check extension against allowed list
            elif self.config.allowed_extensions and file_extension not in self.config.allowed_extensions:
                errors.append(f"File extension '{file_extension}' is not allowed")
            
            # Check MIME type against blocked list
            if mime_type and mime_type in self.config.blocked_mime_types:
                errors.append(f"MIME type '{mime_type}' is blocked for security reasons")
            
            # Check MIME type against allowed list
            elif self.config.allowed_mime_types and mime_type not in self.config.allowed_mime_types:
                if mime_type:
                    warnings.append(f"MIME type '{mime_type}' is not in the allowed list")
                else:
                    warnings.append("Could not determine MIME type")
            
            # Additional security checks
            security_errors = self._perform_security_checks(path)
            errors.extend(security_errors)
            
            # Content validation for text files
            if self.config.require_text_content and self._is_text_file(mime_type, file_extension):
                content_errors = self._validate_text_content(path)
                errors.extend(content_errors)
            
            # Final validation
            is_valid = len(errors) == 0
            
            logger.debug(f"Validation result for {file_path}: {'VALID' if is_valid else 'INVALID'}")
            if errors:
                logger.debug(f"Validation errors: {errors}")
            if warnings:
                logger.debug(f"Validation warnings: {warnings}")
            
            return ValidationResult(
                is_valid=is_valid,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                file_path=file_path,
                file_size=0,
                mime_type=None,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
    
    def validate_files(self, file_paths: List[str]) -> Dict[str, ValidationResult]:
        """
        Validate multiple files.
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Dictionary mapping file paths to validation results
        """
        logger.info(f"Validating {len(file_paths)} files")
        
        results = {}
        for file_path in file_paths:
            results[file_path] = self.validate_file(file_path)
        
        # Log summary
        valid_count = sum(1 for r in results.values() if r.is_valid)
        logger.info(f"Validation complete: {valid_count}/{len(file_paths)} files valid")
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """
        Generate a summary of validation results.
        
        Args:
            results: Dictionary of validation results
            
        Returns:
            Summary dictionary with statistics and details
        """
        total_files = len(results)
        valid_files = [r for r in results.values() if r.is_valid]
        invalid_files = [r for r in results.values() if not r.is_valid]
        
        total_size = sum(r.file_size for r in results.values())
        valid_size = sum(r.file_size for r in valid_files)
        
        all_errors = []
        all_warnings = []
        
        for result in results.values():
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return {
            'total_files': total_files,
            'valid_files': len(valid_files),
            'invalid_files': len(invalid_files),
            'total_size_bytes': total_size,
            'valid_size_bytes': valid_size,
            'total_errors': len(all_errors),
            'total_warnings': len(all_warnings),
            'unique_errors': list(set(all_errors)),
            'unique_warnings': list(set(all_warnings)),
            'file_types': self._get_file_type_summary(results),
            'size_distribution': self._get_size_distribution(results)
        }
    
    def _perform_security_checks(self, path: Path) -> List[str]:
        """
        Perform additional security checks on the file.
        
        Args:
            path: Path object for the file
            
        Returns:
            List of security-related error messages
        """
        errors = []
        
        try:
            # Check for suspicious file characteristics
            if path.name.startswith('.') and len(path.name) > 1:
                # Hidden files might be suspicious
                logger.debug(f"Hidden file detected: {path.name}")
            
            # Check for double extensions (potentially suspicious)
            name_parts = path.name.split('.')
            if len(name_parts) > 2:
                # File has multiple extensions
                potential_execs = ['.exe', '.bat', '.cmd', '.scr', '.com']
                if any(f'.{part}' in potential_execs for part in name_parts[:-1]):
                    errors.append("File has suspicious double extension pattern")
            
            # Check file permissions (if accessible)
            try:
                stat = path.stat()
                # Check if file is executable
                if stat.st_mode & 0o111:  # Any execute bit set
                    logger.debug(f"Executable file detected: {path.name}")
            except:
                pass  # Ignore permission check errors
        
        except Exception as e:
            logger.debug(f"Security check error for {path}: {e}")
        
        return errors
    
    def _is_text_file(self, mime_type: Optional[str], extension: str) -> bool:
        """
        Determine if a file is likely a text file.
        
        Args:
            mime_type: MIME type of the file
            extension: File extension
            
        Returns:
            True if the file is likely a text file
        """
        if mime_type and mime_type.startswith('text/'):
            return True
        
        text_extensions = [
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json',
            '.xml', '.yaml', '.yml', '.csv', '.tsv', '.log', '.sql',
            '.sh', '.gitignore', '.dockerfile'
        ]
        
        return extension.lower() in text_extensions
    
    def _validate_text_content(self, path: Path) -> List[str]:
        """
        Validate text file content.
        
        Args:
            path: Path to the text file
            
        Returns:
            List of content-related error messages
        """
        errors = []
        
        try:
            # Try to read the file with common encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read(1024)  # Read first 1KB
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                errors.append("Cannot read file with common text encodings")
            else:
                # Check for binary content in text file
                if '\x00' in content:
                    errors.append("File contains null bytes (likely binary)")
                
                # Check for excessive control characters
                control_chars = sum(1 for c in content if ord(c) < 32 and c not in '\t\n\r')
                if control_chars > len(content) * 0.1:  # More than 10% control chars
                    errors.append("File contains excessive control characters")
        
        except Exception as e:
            errors.append(f"Error validating text content: {str(e)}")
        
        return errors
    
    def _get_file_type_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, int]:
        """Get summary of file types in the validation results."""
        type_counts = {}
        
        for result in results.values():
            extension = result.metadata.get('file_extension', 'unknown')
            type_counts[extension] = type_counts.get(extension, 0) + 1
        
        return type_counts
    
    def _get_size_distribution(self, results: Dict[str, ValidationResult]) -> Dict[str, int]:
        """Get summary of file size distribution."""
        size_ranges = {
            'tiny (< 1KB)': 0,
            'small (1KB - 100KB)': 0,
            'medium (100KB - 1MB)': 0,
            'large (1MB - 10MB)': 0,
            'very_large (> 10MB)': 0
        }
        
        for result in results.values():
            size = result.file_size
            if size < 1024:
                size_ranges['tiny (< 1KB)'] += 1
            elif size < 100 * 1024:
                size_ranges['small (1KB - 100KB)'] += 1
            elif size < 1024 * 1024:
                size_ranges['medium (100KB - 1MB)'] += 1
            elif size < 10 * 1024 * 1024:
                size_ranges['large (1MB - 10MB)'] += 1
            else:
                size_ranges['very_large (> 10MB)'] += 1
        
        return size_ranges
    
    def update_config(self, **kwargs):
        """
        Update validation configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated validation config: {key} = {value}")
            else:
                logger.warning(f"Unknown validation config parameter: {key}")