# PKI Authentication System Documentation

## Table of Contents
1. [PKI System Overview](#pki-system-overview)
2. [Architecture & Components](#architecture--components)
3. [Setup Workflow](#setup-workflow)
4. [API Methods](#api-methods)
5. [Configuration](#configuration)
6. [File Storage](#file-storage)
7. [Error Handling](#error-handling)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)

## PKI System Overview

### What is PKI Authentication?

Public Key Infrastructure (PKI) authentication in Ghostman provides enterprise-grade certificate-based authentication for secure communication with APIs and services that require client certificates.

### Why does it exist?

PKI authentication exists to support enterprise environments where:
- **Certificate-based authentication** is required by corporate security policies
- **Mutual TLS (mTLS)** authentication is mandated for API access
- **Internal certificate authorities** are used for identity verification
- **Enhanced security** beyond API keys is necessary

### When to use it?

Use PKI authentication when:
- Your organization requires client certificates for API access
- You're working with enterprise APIs that mandate certificate authentication
- You need to comply with security policies requiring mTLS
- Standard API key authentication is insufficient for your security requirements

**Note:** Most cloud services (OpenAI, Anthropic, etc.) use standard API key authentication. PKI is typically required only in enterprise environments.

## Architecture & Components

### Core Components

The PKI system consists of several interconnected components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  PKI Wizard     │    │  PKI Service     │    │ Certificate     │
│                 │────│                  │────│ Manager         │
│ • Setup UI      │    │ • Coordination   │    │ • P12 Import    │
│ • Validation    │    │ • Integration    │    │ • Validation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ PKI Settings    │    │ Session Manager  │    │ File Storage    │
│ Widget          │    │                  │    │                 │
│ • Status Display│    │ • HTTP Sessions  │    │ • Certificates  │
│ • Management UI │    │ • Client Certs   │    │ • Configuration │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 1. Certificate Manager (`certificate_manager.py`)

**Purpose:** Core PKI certificate management and validation

**Key Classes:**
- `CertificateManager`: Main certificate management class
- `CertificateInfo`: Certificate metadata container
- `PKIConfig`: Configuration settings container

**Responsibilities:**
- Import and parse P12 certificate files
- Extract certificates and private keys
- Validate certificate chains and expiration
- Secure storage management
- Certificate information extraction

### 2. PKI Service (`pki_service.py`)

**Purpose:** High-level PKI coordination service

**Key Classes:**
- `PKIService`: Main coordination service (singleton pattern)

**Responsibilities:**
- Coordinate between certificate management and HTTP sessions
- Provide simplified API for PKI operations
- Integrate with session manager for HTTP client configuration
- Handle PKI enable/disable operations

### 3. Session Manager (`session_manager.py`)

**Purpose:** HTTP session management with PKI integration

**Key Classes:**
- `SessionManager`: Thread-safe HTTP session manager (singleton pattern)

**Responsibilities:**
- Manage HTTP sessions with connection pooling
- Apply client certificates to requests sessions
- Handle PKI configuration for HTTPS connections
- Provide thread-safe access to configured sessions

### 4. PKI Wizard (`pki_wizard.py`)

**Purpose:** User-friendly PKI setup interface

**Key Classes:**
- `PKISetupWizard`: Main wizard dialog
- `WelcomePage`, `ModeSelectionPage`, `P12ImportPage`, etc.: Wizard pages

**Responsibilities:**
- Guide users through PKI setup process
- Validate certificates during import
- Test PKI connectivity
- Provide setup completion feedback

### 5. PKI Settings Widget (`pki_settings_widget.py`)

**Purpose:** PKI management interface for settings dialog

**Key Classes:**
- `PKISettingsWidget`: Integrated settings panel

**Responsibilities:**
- Display PKI status and certificate information
- Provide setup and management controls
- Show certificate expiration warnings
- Enable/disable PKI authentication

## Setup Workflow

### Step-by-Step Process

#### 1. Initial Setup Decision
```
User opens PKI wizard or settings
         ↓
   Choose authentication mode:
   • Enterprise PKI Authentication
   • Standard Authentication (Default)
```

#### 2. P12 Certificate Import
```
Select P12 file (.p12, .pfx, .pk12)
         ↓
Enter certificate password
         ↓
Validate file exists and format
         ↓
Proceed to certificate chain configuration
```

#### 3. Certificate Chain Configuration (Optional)
```
Option to import CA certificate chain
         ↓
Browse for CA chain file (.pem, .crt, .cer, .p7b)
         ↓
Validate chain file (if provided)
         ↓
Proceed to validation
```

#### 4. Certificate Import and Validation
```
Parse P12 file with password
         ↓
Extract private key and certificate
         ↓
Extract additional certificates (chain)
         ↓
Store files securely in user profile
         ↓
Validate certificate expiration and properties
         ↓
Update PKI configuration
```

#### 5. Session Configuration
```
Configure session manager with certificates
         ↓
Apply client certificate to HTTP sessions
         ↓
Test PKI connection (optional)
         ↓
Complete setup
```

### Files Created During Setup

When PKI is successfully configured, the following files are created in the user's profile:

**Windows:** `%APPDATA%\Ghostman\pki\`
**Linux/Mac:** `~/.ghostman/pki/`

```
pki/
├── client.p12          # Original P12 file (copied)
├── client.crt          # Extracted client certificate (PEM format)
├── client.pem          # Extracted private key (PEM format)
├── ca_chain.pem        # CA certificate chain (if provided)
└── pki_config.json     # PKI configuration metadata
```

## API Methods

### Certificate Manager Methods

#### `CertificateManager.__init__()`
Initializes the certificate manager and creates PKI directory structure.

```python
def __init__(self):
    """Initialize certificate manager."""
```

#### `import_p12_file(p12_path: str, password: str) -> bool`
Imports and processes a P12 certificate file.

**Parameters:**
- `p12_path`: Path to the P12 certificate file
- `password`: Password to decrypt the P12 file

**Returns:** `True` if import successful, `False` otherwise

**Raises:** `P12ImportError` if import fails

```python
# Example usage
cert_manager = CertificateManager()
success = cert_manager.import_p12_file("/path/to/cert.p12", "password123")
```

#### `validate_certificates() -> bool`
Validates current certificates for expiration and integrity.

**Returns:** `True` if certificates are valid

```python
is_valid = cert_manager.validate_certificates()
```

#### `get_client_cert_files() -> Tuple[Optional[str], Optional[str]]`
Returns paths to client certificate and private key files.

**Returns:** Tuple of `(cert_path, key_path)` or `(None, None)` if not available

#### `get_ca_chain_file() -> Optional[str]`
Returns path to CA certificate chain file.

**Returns:** Path to CA chain file or `None` if not configured

#### `get_certificate_info() -> Optional[CertificateInfo]`
Returns detailed certificate information.

**Returns:** `CertificateInfo` object with certificate details

#### `get_pki_status() -> Dict[str, Any]`
Returns comprehensive PKI status information.

**Returns:** Dictionary with status details:
```python
{
    'enabled': bool,
    'configured': bool,
    'valid': bool,
    'certificate_info': dict,
    'last_validation': datetime,
    'warnings': list,
    'errors': list
}
```

### PKI Service Methods

#### `PKIService.initialize() -> bool`
Initializes PKI service and applies configuration.

**Returns:** `True` if PKI is enabled and configured

#### `setup_pki_authentication(p12_path: str, password: str) -> Tuple[bool, Optional[str]]`
Complete PKI setup from P12 file.

**Parameters:**
- `p12_path`: Path to P12 certificate file
- `password`: P12 file password

**Returns:** Tuple of `(success, error_message)`

#### `disable_pki_authentication() -> bool`
Disables PKI authentication.

**Returns:** `True` if successful

#### `validate_current_certificates() -> bool`
Validates current certificates.

**Returns:** `True` if certificates are valid

#### `get_certificate_status() -> Dict[str, Any]`
Gets comprehensive certificate status.

**Returns:** Dictionary with certificate status information

#### `test_pki_connection(test_url: str) -> Tuple[bool, Optional[str]]`
Tests PKI authentication with a given URL.

**Parameters:**
- `test_url`: URL to test PKI authentication against

**Returns:** Tuple of `(success, error_message)`

### Session Manager Methods

#### `configure_pki(cert_path: str, key_path: str, ca_path: Optional[str] = None)`
Configures PKI client authentication for HTTP sessions.

**Parameters:**
- `cert_path`: Path to client certificate file
- `key_path`: Path to client private key file
- `ca_path`: Optional path to CA certificate chain file

#### `disable_pki()`
Disables PKI client authentication for sessions.

#### `get_pki_info() -> Dict[str, Any]`
Gets PKI configuration information.

**Returns:** Dictionary with PKI configuration details

## Configuration

### PKI Configuration Structure

PKI configuration is stored in `pki_config.json` with the following structure:

```json
{
  "enabled": true,
  "client_cert_path": "/path/to/client.crt",
  "client_key_path": "/path/to/client.pem",
  "ca_chain_path": "/path/to/ca_chain.pem",
  "p12_file_hash": "sha256_hash_of_original_p12",
  "last_validation": "2024-01-15T10:30:00.000000",
  "certificate_info": {
    "subject": "CN=User Name,O=Organization,C=US",
    "issuer": "CN=CA Name,O=Organization,C=US",
    "serial_number": "123456789",
    "not_valid_before": "2024-01-01T00:00:00.000000",
    "not_valid_after": "2025-01-01T00:00:00.000000",
    "fingerprint": "sha256_fingerprint",
    "key_usage": ["Digital Signature", "Key Encipherment"],
    "is_valid": true,
    "days_until_expiry": 350
  }
}
```

### Settings Integration

PKI integrates with Ghostman's settings system through the PKI Settings Widget in the Settings Dialog. Users can:

- View current PKI status and certificate information
- Enable/disable PKI authentication
- Launch the PKI setup wizard
- Test PKI connections
- View certificate expiration warnings

### Session Integration

When PKI is enabled, the Session Manager automatically:
- Applies client certificates to all HTTPS requests
- Configures CA certificate verification (if CA chain provided)
- Maintains thread-safe access to PKI-configured sessions
- Handles connection pooling with certificate authentication

## File Storage

### Storage Locations

**Windows:**
```
%APPDATA%\Ghostman\pki\
C:\Users\[username]\AppData\Roaming\Ghostman\pki\
```

**Linux:**
```
~/.ghostman/pki/
/home/[username]/.ghostman/pki/
```

**macOS:**
```
~/.ghostman/pki/
/Users/[username]/.ghostman/pki/
```

### File Organization

```
pki/
├── client.p12          # Original P12 certificate file
├── client.crt          # Client certificate (PEM format)
├── client.pem          # Private key (PEM format, unencrypted)
├── ca_chain.pem        # CA certificate chain (optional)
└── pki_config.json     # Configuration and metadata
```

### File Permissions

The PKI directory and files are created with restricted permissions:
- **Directory:** Read/write for owner only (700)
- **Certificate files:** Read/write for owner only (600)
- **Private key:** Read/write for owner only (600)

### File Formats

#### Client Certificate (`client.crt`)
PEM-encoded X.509 certificate:
```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKoK/OvD/+8zMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
...
-----END CERTIFICATE-----
```

#### Private Key (`client.pem`)
PEM-encoded PKCS#8 private key (unencrypted):
```
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKB
...
-----END PRIVATE KEY-----
```

#### CA Chain (`ca_chain.pem`)
Concatenated PEM-encoded CA certificates:
```
-----BEGIN CERTIFICATE-----
[Intermediate CA Certificate]
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[Root CA Certificate]
-----END CERTIFICATE-----
```

## Error Handling

### Exception Hierarchy

```
PKIError (Base exception)
├── CertificateValidationError
└── P12ImportError
```

### Common Error Scenarios

#### 1. P12 Import Failures

**Invalid password:**
```
P12ImportError: Failed to parse P12 file: Bad decrypt
```

**Corrupted file:**
```
P12ImportError: Failed to parse P12 file: Could not deserialize key data
```

**Missing private key:**
```
P12ImportError: P12 file does not contain required private key and certificate
```

#### 2. Certificate Validation Errors

**Expired certificate:**
```
Certificate has expired
```

**Certificate not yet valid:**
```
Certificate is not yet valid
```

**Missing certificate files:**
```
Certificate files not found
```

#### 3. Session Configuration Errors

**Missing certificate files:**
```
Client certificate files not available
```

**Invalid certificate format:**
```
Failed to apply PKI configuration: [SSL Error]
```

### Error Recovery

The PKI system includes automatic error recovery:

1. **File cleanup on import failure:** Partial certificate files are removed
2. **Configuration reset:** Invalid configurations are reset to disabled state
3. **Fallback to standard authentication:** PKI failures don't break basic functionality
4. **Validation retry:** Certificate validation is retried with exponential backoff

### Logging

PKI operations are extensively logged for troubleshooting:

```python
# Example log output
2024-01-15 10:30:00 INFO  [ghostman.pki.certificate_manager] PKI Certificate Manager initialized: C:\Users\user\AppData\Roaming\Ghostman\pki
2024-01-15 10:30:05 INFO  [ghostman.pki.certificate_manager] Importing P12 file: C:\Users\user\cert.p12
2024-01-15 10:30:06 INFO  [ghostman.pki.certificate_manager] ✅ P12 certificate imported successfully
2024-01-15 10:30:06 INFO  [ghostman.pki.service] ✅ PKI service initialized with authentication
```

## Security Considerations

### Password Handling

**P12 Passwords:**
- Passwords are only used during import process
- Not stored or cached anywhere in the system
- Immediately cleared from memory after use
- P12 files are copied to secure storage, passwords not needed thereafter

### Private Key Security

**Storage:**
- Private keys are extracted and stored unencrypted in PEM format
- Files have restrictive permissions (600 - owner read/write only)
- Stored in user-specific directories not accessible to other users

**Memory:**
- Private keys are loaded into memory only when needed for requests
- No persistent caching of private key material
- Python's cryptography library handles secure memory management

### Certificate Chain Validation

**Trust Store:**
- System uses provided CA chain for server certificate validation
- Falls back to system trust store if no custom CA provided
- Mutual TLS ensures both client and server authentication

### File System Security

**Directory Permissions:**
- PKI directory created with 700 permissions (owner only)
- All certificate files created with 600 permissions
- Windows ACLs restrict access to current user only

**File Integrity:**
- P12 file hash stored to detect tampering
- Certificate fingerprints logged for verification
- Configuration includes validation timestamps

### Network Security

**HTTP Session Configuration:**
- All PKI-enabled requests use HTTPS with client certificates
- SNI (Server Name Indication) properly configured
- Connection pooling maintains security context
- Proper SSL/TLS version negotiation

### Secure Cleanup

**File Removal:**
- `_cleanup_certificate_files()` removes partial imports on error
- Secure deletion attempts to overwrite file contents
- Configuration reset removes sensitive metadata

## Troubleshooting

### Common Issues and Solutions

#### 1. Certificate Import Failures

**Problem:** "Failed to parse P12 file: Bad decrypt"
**Solution:** 
- Verify the P12 password is correct
- Ensure the P12 file is not corrupted
- Try opening the P12 file with another tool to verify integrity

**Problem:** "P12 file does not contain required private key and certificate"
**Solution:**
- Verify the P12 file contains both certificate and private key
- Check if the P12 file was generated correctly
- Contact your certificate authority for a properly formatted P12 file

#### 2. Certificate Validation Issues

**Problem:** "Certificate has expired"
**Solution:**
- Obtain a new certificate from your certificate authority
- Update the certificate before the expiration date
- Check if system clock is correct

**Problem:** "Certificate is not yet valid"
**Solution:**
- Verify system clock is correct and synchronized
- Check certificate start date
- Wait until certificate becomes valid

#### 3. Connection Issues

**Problem:** "PKI connection test failed: SSL handshake failed"
**Solution:**
- Verify the server requires client certificates
- Check if the CA chain is correctly configured
- Ensure the certificate is trusted by the server

**Problem:** "Client certificate files not available"
**Solution:**
- Run the PKI setup wizard again
- Check file permissions in the PKI directory
- Verify certificate files exist and are readable

#### 4. Permission Issues

**Problem:** "Permission denied" when accessing certificate files
**Solution:**
- Check file permissions on PKI directory and files
- Ensure current user owns the PKI directory
- Run Ghostman with appropriate user permissions

### Diagnostic Information

#### PKI Status Check

Use the PKI Settings Widget to check:
- Current PKI status (enabled/disabled/invalid)
- Certificate information and expiration
- Last validation timestamp
- Current warnings and errors

#### Log Analysis

Check Ghostman logs for PKI-related entries:
- Certificate import progress
- Validation results
- HTTP session configuration
- Connection test results

#### Manual Verification

Verify certificate files manually:

```bash
# Check certificate details
openssl x509 -in client.crt -text -noout

# Verify private key
openssl rsa -in client.pem -check

# Test certificate and key match
openssl x509 -noout -modulus -in client.crt | openssl md5
openssl rsa -noout -modulus -in client.pem | openssl md5
```

### Recovery Procedures

#### Reset PKI Configuration

1. Stop Ghostman
2. Delete PKI directory: `%APPDATA%\Ghostman\pki\`
3. Restart Ghostman
4. Run PKI setup wizard again

#### Reconfigure Certificates

1. Open Settings → PKI Auth tab
2. Click "Fix PKI Configuration" or "Reconfigure PKI"
3. Follow the setup wizard with new certificates
4. Test connection to verify functionality

#### Disable PKI Fallback

If PKI causes issues:
1. Open Settings → PKI Auth tab
2. Click "Disable PKI"
3. Confirm disable operation
4. Ghostman falls back to standard authentication

### Support Information

For additional PKI support:
- Check Ghostman logs for detailed error messages
- Verify certificate files with OpenSSL tools
- Contact your IT administrator for enterprise certificate issues
- Review network connectivity and firewall settings
- Ensure proper certificate chain configuration

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-18  
**Compatibility:** Ghostman v1.0+