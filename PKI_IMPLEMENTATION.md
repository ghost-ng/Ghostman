# PKI Implementation in Ghostman

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Certificate Management](#certificate-management)
5. [Configuration and Settings](#configuration-and-settings)
6. [Integration Points](#integration-points)
7. [File Locations and Storage](#file-locations-and-storage)
8. [Security Considerations](#security-considerations)
9. [Usage Examples](#usage-examples)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is PKI in Ghostman?

The Public Key Infrastructure (PKI) implementation in Ghostman enables **enterprise-grade certificate-based authentication** for secure API communications. This is essential for organizations that require mutual TLS (mTLS) authentication using client certificates.

### Key Features

- **P12 Certificate Import**: Import PKCS#12 certificate files containing client certificates and private keys
- **Certificate Chain Support**: Optional CA certificate chain validation for internal/enterprise CAs
- **Automatic Certificate Validation**: Expiration checking and certificate health monitoring
- **Session Integration**: Seamless integration with all HTTP requests via centralized session manager
- **SSL/TLS Configuration**: Unified SSL verification management with PKI certificate awareness
- **User-Friendly Setup**: Step-by-step wizard for certificate configuration
- **Secure Storage**: Certificates stored in Windows AppData with appropriate security

### When to Use PKI

PKI authentication is required when:
- Your organization uses internal certificate authorities
- APIs require client certificate authentication (mTLS)
- Enterprise security policies mandate certificate-based authentication
- Connecting to services with custom SSL/TLS certificate requirements

For standard cloud services (OpenAI, Anthropic, etc.), PKI is **not required** - use standard API key authentication instead.

---

## Architecture

### Layered Design

Ghostman's PKI implementation follows a clean architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                        │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │ PKI Setup Wizard│         │PKI Settings Widget│          │
│  └────────┬────────┘         └────────┬─────────┘          │
└───────────┼──────────────────────────┼─────────────────────┘
            │                          │
┌───────────┼──────────────────────────┼─────────────────────┐
│           ▼        Infrastructure Layer        ▼            │
│  ┌─────────────────────────────────────────────────┐       │
│  │              PKI Service (Coordinator)          │       │
│  │  - Setup/Disable PKI                            │       │
│  │  - Certificate Validation                       │       │
│  │  - Connection Testing                           │       │
│  │  - Status Monitoring                            │       │
│  └──────────┬──────────────────────┬───────────────┘       │
│             │                      │                        │
│    ┌────────▼──────────┐  ┌───────▼────────┐              │
│    │Certificate Manager│  │  SSL Service   │              │
│    │ - P12 Import      │  │ - Verification │              │
│    │ - Cert Validation │  │ - CA Paths     │              │
│    │ - Storage Mgmt    │  │ - Config       │              │
│    └────────┬──────────┘  └───────┬────────┘              │
│             │                      │                        │
│             └──────────┬───────────┘                        │
│                        ▼                                    │
│              ┌─────────────────┐                           │
│              │ Session Manager │                           │
│              │ - HTTP Sessions │                           │
│              │ - PKI Config    │                           │
│              │ - SSL Settings  │                           │
│              └─────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Certificate Setup Flow:**
```
User → PKI Wizard → PKI Service → Certificate Manager → Storage
                         ↓
                   Session Manager (applies cert to all requests)
                         ↓
                   SSL Service (configures CA verification)
```

**API Request Flow with PKI:**
```
AI Service Request → Session Manager (with PKI cert) → HTTPS + mTLS → API Server
                              ↑
                         SSL Service (CA verification)
```

---

## Components

### 1. PKI Service (`pki_service.py`)

**Location**: `ghostman/src/infrastructure/pki/pki_service.py`

The main coordinator for PKI operations. Acts as a high-level interface for the entire PKI system.

**Key Responsibilities:**
- Initialize and manage PKI configuration
- Coordinate between certificate manager and session manager
- Validate and test PKI connections
- Monitor certificate health and expiration
- Enable/disable PKI authentication

**Main Methods:**

```python
# Initialize PKI (called at app startup)
pki_service.initialize() -> bool

# Setup PKI from P12 file
pki_service.setup_pki_authentication(p12_path: str, password: str)
    -> Tuple[bool, Optional[str]]

# Disable PKI
pki_service.disable_pki_authentication() -> bool

# Test connection with PKI
pki_service.test_pki_connection(test_url: str, max_attempts: int = 3)
    -> Tuple[bool, Optional[str]]

# Get status
pki_service.get_certificate_status() -> Dict[str, Any]
```

**Global Instance:**
```python
from ghostman.src.infrastructure.pki import pki_service
```

### 2. Certificate Manager (`certificate_manager.py`)

**Location**: `ghostman/src/infrastructure/pki/certificate_manager.py`

Handles low-level certificate operations including import, validation, and storage.

**Key Features:**
- P12 file parsing and extraction
- Certificate validation and expiration checking
- Multi-format CA chain support (PEM, DER, CRT, CER)
- Secure certificate storage
- Certificate information extraction

**Key Classes:**

```python
@dataclass
class CertificateInfo:
    subject: str
    issuer: str
    serial_number: str
    not_valid_before: datetime
    not_valid_after: datetime
    fingerprint: str
    key_usage: List[str]
    is_valid: bool
    days_until_expiry: int

@dataclass
class PKIConfig:
    enabled: bool
    client_cert_path: Optional[str]
    client_key_path: Optional[str]
    ca_chain_path: Optional[str]
    p12_file_hash: Optional[str]
    last_validation: Optional[datetime]
    certificate_info: Optional[CertificateInfo]
```

**Main Methods:**

```python
# Import P12 certificate
cert_manager.import_p12_file(p12_path: str, password: str) -> bool

# Import CA chain (supports PEM, DER, CRT, CER)
cert_manager.import_ca_chain_file(ca_chain_path: str) -> bool

# Validate certificates
cert_manager.validate_certificates() -> bool

# Get certificate files
cert_manager.get_client_cert_files() -> Tuple[Optional[str], Optional[str]]
cert_manager.get_ca_chain_file() -> Optional[str]
```

### 3. SSL Service (`ssl_service.py`)

**Location**: `ghostman/src/infrastructure/ssl/ssl_service.py`

Centralized SSL/TLS verification management that integrates with PKI.

**Key Responsibilities:**
- Manage SSL verification settings globally
- Coordinate with PKI for custom CA chains
- Provide verification parameters for all requests
- Handle ignore_ssl_verification setting

**Main Methods:**

```python
# Configure SSL verification
ssl_service.configure(ignore_ssl: bool, custom_ca_path: Optional[str])

# Get verify parameter for requests
ssl_service.get_verify_parameter() -> Union[bool, str]

# Configure from settings
ssl_service.configure_from_settings(settings: Dict) -> bool

# Update from PKI service
ssl_service.configure_from_pki_service() -> bool
```

**Global Instance:**
```python
from ghostman.src.infrastructure.ssl import ssl_service
```

### 4. Session Manager (`session_manager.py`)

**Location**: `ghostman/src/infrastructure/ai/session_manager.py`

Thread-safe HTTP session manager that applies PKI certificates to all requests.

**PKI Integration:**
- Stores PKI certificate configuration
- Applies client certificates to all HTTPS requests
- Coordinates with SSL service for verification
- Manages connection pooling with PKI

**PKI-Related Methods:**

```python
# Configure PKI for all requests
session_manager.configure_pki(
    cert_path: str,
    key_path: str,
    ca_path: Optional[str]
)

# Disable PKI
session_manager.disable_pki()

# Get PKI info
session_manager.get_pki_info() -> Dict[str, Any]
```

**Critical Design Rule:**
All HTTP requests MUST go through `session_manager`. Never create raw `requests.Session()` objects - this bypasses PKI configuration.

### 5. PKI Setup Wizard (`pki_wizard.py`)

**Location**: `ghostman/src/presentation/wizards/pki_wizard.py`

Interactive wizard for PKI configuration with 6 pages:

1. **Welcome Page**: Introduction and requirements
2. **Mode Selection**: Choose Enterprise PKI vs Standard authentication
3. **P12 Import**: Select and import P12 certificate file
4. **Certificate Chain**: Optional CA chain import
5. **Validation**: Automatic certificate validation and testing
6. **Summary**: Configuration results and next steps

**Usage:**
```python
from ghostman.src.presentation.wizards.pki_wizard import show_pki_wizard

result = show_pki_wizard(parent_widget)
# Returns: True (PKI enabled), False (standard auth), None (cancelled)
```

### 6. PKI Settings Widget (`pki_settings_widget.py`)

**Location**: `ghostman/src/presentation/widgets/pki_settings_widget.py`

Settings dialog tab for PKI management.

**Features:**
- Real-time PKI status display
- Certificate information viewer
- Enable/disable toggle
- Connection testing
- Wizard launcher for setup/reconfiguration

---

## Certificate Management

### Supported Certificate Formats

**P12/PKCS#12 Files** (Client Certificate + Private Key):
- Extensions: `.p12`, `.pfx`, `.pk12`
- Contains: Client certificate, private key, optional certificate chain
- Requires: Password for import
- Use: Primary client authentication

**CA Certificate Chains**:
- Formats: PEM, DER, CRT, CER, P7B
- Contains: Certificate Authority certificates
- Use: Server certificate validation

### Certificate Import Process

The certificate manager handles P12 import with these steps:

1. **Read and Parse P12**: Extract using cryptography library
2. **Extract Components**:
   - Private key → `client.pem` (PKCS#8, unencrypted)
   - Client certificate → `client.crt` (PEM format)
   - Certificate chain → `ca_chain.pem` (PEM format)
3. **Calculate Hash**: SHA256 hash of P12 file for change tracking
4. **Extract Certificate Info**: Subject, issuer, expiration, fingerprint
5. **Validate**: Check expiration, dates, key usage
6. **Store Configuration**: Save to settings.json
7. **Apply to Session**: Configure session manager with certificates

### Certificate Validation

Validation occurs at multiple points:

**During Import:**
- P12 file parsing
- Password verification
- Certificate expiration check
- Private key verification

**Runtime Validation:**
- Expiration monitoring (warns at 30 days)
- File existence checks
- Certificate chain validation
- Timezone-aware date comparisons

**Validation Code Example:**
```python
# Check if certificates are valid
is_valid = pki_service.validate_current_certificates()

# Get detailed status
status = pki_service.get_certificate_status()
# Returns:
# {
#     'enabled': bool,
#     'valid': bool,
#     'certificate_info': {...},
#     'last_validation': datetime,
#     'warnings': [],
#     'errors': []
# }
```

### Certificate Expiration Warnings

The system provides proactive expiration warnings:

- **30 days or less**: Warning displayed in status
- **Expired**: Authentication fails, error shown
- **Not yet valid**: Error if certificate future-dated

```python
# Check for expiration warnings
warning = pki_service.get_certificate_expiry_warning()
if warning:
    # Returns: "Certificate expires in X days"
```

### Multi-Format CA Chain Support

The certificate manager intelligently parses CA chains in various formats:

**Supported Formats:**
- Single or multiple PEM certificates
- DER-encoded certificates (binary)
- CRT/CER files (common in Windows)
- Base64-encoded certificates
- Mixed format chains

**Parser Logic:**
1. Check for PEM markers (`-----BEGIN CERTIFICATE-----`)
2. Try DER single certificate parsing
3. Try multiple DER certificate concatenation
4. Try base64 decoding
5. Convert all to unified PEM format

---

## Configuration and Settings

### Settings Structure

PKI configuration is stored in `%APPDATA%\Ghostman\configs\settings.json` under the `pki` key:

```json
{
  "pki": {
    "enabled": false,
    "client_cert_path": "C:\\Users\\user\\AppData\\Roaming\\Ghostman\\pki\\client.crt",
    "client_key_path": "C:\\Users\\user\\AppData\\Roaming\\Ghostman\\pki\\client.pem",
    "ca_chain_path": "C:\\Users\\user\\AppData\\Roaming\\Ghostman\\pki\\ca_chain.pem",
    "p12_file_hash": "abc123...",
    "last_validation": "2025-10-29T12:00:00+00:00",
    "certificate_info": {
      "subject": "CN=User Name,O=Organization",
      "issuer": "CN=Internal CA,O=Organization",
      "serial_number": "123456789",
      "not_valid_before": "2024-01-01T00:00:00+00:00",
      "not_valid_after": "2026-01-01T00:00:00+00:00",
      "fingerprint": "sha256:abc123...",
      "key_usage": ["Digital Signature", "Key Encipherment"],
      "is_valid": true,
      "days_until_expiry": 120
    }
  }
}
```

### Settings Migration

The system automatically migrates from the old separate PKI config file:

**Old Location** (deprecated): `%APPDATA%\Ghostman\pki\pki_config.json`
**New Location**: `%APPDATA%\Ghostman\configs\settings.json` (under `pki` key)

Migration happens automatically on first load via `certificate_manager.load_config()`.

### Accessing PKI Settings

```python
from ghostman.src.infrastructure.storage.settings_manager import settings

# Get PKI configuration
pki_enabled = settings.get('pki.enabled', False)
cert_path = settings.get('pki.client_cert_path')

# Set PKI configuration
settings.set('pki.enabled', True)
settings.set('pki.client_cert_path', '/path/to/cert.crt')
```

### SSL Verification Settings

PKI integrates with the global SSL verification setting:

```json
{
  "advanced": {
    "ignore_ssl_verification": false
  }
}
```

**Integration Logic:**
- If `ignore_ssl_verification = true`: SSL verification disabled (PKI certs still used for authentication)
- If `ignore_ssl_verification = false` AND PKI CA chain exists: Use PKI CA chain for verification
- If `ignore_ssl_verification = false` AND no PKI CA: Use system CA bundle

---

## Integration Points

### 1. Application Startup

PKI is initialized during app startup in `app_coordinator.py`:

```python
# Initialize PKI service
from ghostman.src.infrastructure.pki import pki_service
pki_service.initialize()
```

The `initialize()` method:
- Loads PKI configuration from settings
- Applies PKI to session manager if enabled
- Returns True if PKI is active and valid
- Uses cached initialization state to avoid repeated calls

### 2. AI Service Integration

AI services automatically use PKI for API requests:

```python
# In ai_service.py
def _configure_pki_if_enabled(self):
    """Configure PKI authentication if enabled."""
    from ..pki.pki_service import pki_service

    if pki_service.cert_manager.is_pki_enabled():
        cert_info = pki_service.cert_manager.get_client_cert_files()
        ca_bundle_path = pki_service.cert_manager.get_ca_chain_file()

        if cert_info:
            session_manager.configure_pki(
                cert_path=cert_info[0],
                key_path=cert_info[1],
                ca_path=ca_bundle_path
            )
```

This ensures all AI API requests (OpenAI, Anthropic, custom endpoints) use PKI if configured.

### 3. Session Manager Integration

The session manager maintains PKI configuration across all requests:

```python
class SessionManager:
    def __init__(self):
        self._pki_config = None  # (cert_path, key_path, ca_path)

    def configure_pki(self, cert_path, key_path, ca_path=None):
        """Store PKI config and apply to session."""
        self._pki_config = (cert_path, key_path, ca_path)
        if self._session:
            self._apply_pki_config()

    def _apply_pki_config(self):
        """Apply PKI to current session."""
        cert_path, key_path, ca_path = self._pki_config

        # Set client certificate
        self._session.cert = (cert_path, key_path)

        # Set CA verification
        verify_param = ssl_service.get_verify_parameter()
        if verify_param is not False and ca_path:
            self._session.verify = ca_path
        else:
            self._session.verify = verify_param
```

### 4. SSL Service Integration

SSL service coordinates with PKI for verification:

```python
def configure_from_pki_service(self) -> bool:
    """Update SSL config when PKI changes."""
    custom_ca_path = None
    if pki_service.cert_manager.is_pki_enabled():
        custom_ca_path = pki_service.cert_manager.get_ca_chain_file()

    self._custom_ca_path = custom_ca_path
    return self.configure_session_manager()
```

This ensures:
- PKI CA chains are used for verification
- SSL settings update when PKI is enabled/disabled
- Session manager always has current CA path

### 5. Settings Dialog Integration

Settings dialog includes PKI tab via `PKISettingsWidget`:

```python
# In settings_dialog.py
def _create_pki_tab(self):
    """Create PKI Authentication settings tab."""
    from ..widgets.pki_settings_widget import PKISettingsWidget

    self.pki_widget = PKISettingsWidget(self)
    self.pki_widget.pki_status_changed.connect(self._on_pki_status_changed)

    return self.pki_widget
```

The widget provides:
- Real-time status monitoring
- Certificate information display
- Setup wizard access
- Enable/disable controls
- Connection testing

---

## File Locations and Storage

### Directory Structure

All PKI files are stored in the Windows AppData directory:

```
%APPDATA%\Ghostman\
├── configs\
│   └── settings.json          # PKI configuration (under 'pki' key)
├── pki\                        # Certificate storage directory
│   ├── client.crt              # Client certificate (PEM format)
│   ├── client.pem              # Private key (PKCS#8, unencrypted)
│   └── ca_chain.pem            # CA certificate chain (optional, PEM format)
└── db\
    └── conversations.db        # Application database (not PKI-related)
```

### Platform-Specific Paths

**Windows:**
```
C:\Users\<username>\AppData\Roaming\Ghostman\pki\
```

**Linux/Mac (fallback):**
```
~/.Ghostman/pki/
```

### File Permissions

**Security Considerations:**
- Certificate files are stored with user-only read permissions
- Private key (`client.pem`) stored unencrypted but protected by OS file permissions
- P12 file is NOT copied - only the extracted certificates are stored
- File hash tracks P12 file changes for re-import detection

### Accessing PKI Directory

```python
from ghostman.src.infrastructure.pki import pki_service

# Get PKI directory path
pki_dir = pki_service.cert_manager.pki_dir
# Returns: WindowsPath('C:/Users/user/AppData/Roaming/Ghostman/pki')

# Get individual file paths
cert_path, key_path = pki_service.cert_manager.get_client_cert_files()
ca_path = pki_service.cert_manager.get_ca_chain_file()
```

### Storage Security

**What is stored:**
- Client certificate (public key) - `client.crt`
- Private key (PKCS#8 format, unencrypted) - `client.pem`
- CA chain (public certificates) - `ca_chain.pem`
- Configuration metadata - `settings.json`

**What is NOT stored:**
- Original P12 file
- P12 password
- Only a SHA256 hash of P12 for change detection

**Private Key Security:**
The private key is stored unencrypted because:
1. Protected by Windows user account file permissions
2. Required for automatic authentication (password-protecting would require manual password entry)
3. Equivalent to SSH private key storage model
4. Windows DPAPI could be added in future for additional protection

---

## Security Considerations

### Certificate Security Best Practices

**For Developers:**

1. **Never Hardcode Paths**: Always use `pki_service` to get certificate paths
2. **Use Session Manager**: Never create raw `requests.Session()` objects
3. **Check Expiration**: Monitor certificate expiration warnings
4. **Validate Before Use**: Always validate certificates before critical operations
5. **Log Security Events**: PKI operations are logged for audit trails

**For System Administrators:**

1. **Regular Renewal**: Renew certificates before 30-day expiration warning
2. **Secure Distribution**: Distribute P12 files securely (encrypted email, secure file share)
3. **Password Complexity**: Use strong P12 passwords during certificate creation
4. **Access Control**: Limit access to PKI directory via Windows ACLs
5. **Monitor Logs**: Review PKI logs for unauthorized access attempts

### Threat Model

**Protected Against:**
- Unauthorized API access (requires valid certificate)
- Man-in-the-middle attacks (mTLS verification)
- Certificate tampering (hash validation)
- Expired certificate usage (automatic validation)

**Not Protected Against:**
- Compromised user account (OS-level security issue)
- Malware with user permissions (OS-level security issue)
- Physical access to machine (full disk encryption recommended)

### SSL Verification

The system provides flexible SSL verification:

**Strict Mode (Recommended):**
```python
settings.set('advanced.ignore_ssl_verification', False)
```
- Full SSL/TLS verification
- Uses PKI CA chain if available
- Falls back to system CA bundle
- Prevents MITM attacks

**Permissive Mode (Development Only):**
```python
settings.set('advanced.ignore_ssl_verification', True)
```
- Disables SSL verification
- Still sends client certificates for authentication
- Use only in isolated development environments
- Never use in production

### Logging and Auditing

PKI operations are logged at multiple levels:

```python
# Info level - normal operations
logger.info("✓ PKI service initialized with authentication")
logger.info("✓ P12 certificate imported successfully")

# Warning level - potential issues
logger.warning("⚠ Certificate expires in 15 days")
logger.warning("PKI configured but invalid - showing wizard")

# Error level - failures
logger.error("✗ PKI service initialization failed: {error}")
logger.error("✗ Certificate validation failed: {error}")
```

**Log Location**: `%APPDATA%\Ghostman\logs\`

---

## Usage Examples

### Example 1: Initial PKI Setup via Wizard

```python
from ghostman.src.presentation.wizards.pki_wizard import show_pki_wizard

# Show wizard (returns True/False/None)
result = show_pki_wizard(parent_widget)

if result is True:
    print("PKI authentication enabled")
elif result is False:
    print("Standard authentication selected")
else:
    print("Setup cancelled")
```

### Example 2: Programmatic PKI Setup

```python
from ghostman.src.infrastructure.pki import pki_service

# Setup PKI from P12 file
p12_path = "C:/certificates/user.p12"
password = "secret_password"

success, error = pki_service.setup_pki_authentication(p12_path, password)

if success:
    print("PKI configured successfully")

    # Optionally import CA chain
    ca_path = "C:/certificates/ca_chain.pem"
    pki_service.cert_manager.import_ca_chain_file(ca_path)
else:
    print(f"PKI setup failed: {error}")
```

### Example 3: Check PKI Status

```python
from ghostman.src.infrastructure.pki import pki_service

# Initialize and check status
pki_service.initialize()

status = pki_service.get_certificate_status()

print(f"PKI Enabled: {status['enabled']}")
print(f"Valid: {status['valid']}")

if status['certificate_info']:
    cert = status['certificate_info']
    print(f"Subject: {cert['subject']}")
    print(f"Expires: {cert['not_valid_after']}")
    print(f"Days until expiry: {cert['days_until_expiry']}")

if status['warnings']:
    for warning in status['warnings']:
        print(f"Warning: {warning}")
```

### Example 4: Test PKI Connection

```python
from ghostman.src.infrastructure.pki import pki_service

# Test connection to an API endpoint
test_url = "https://api.example.com/health"
success, error = pki_service.test_pki_connection(
    test_url=test_url,
    max_attempts=3,
    ignore_ssl=False  # Use SSL verification
)

if success:
    print("PKI connection test passed")
else:
    print(f"Connection test failed: {error}")
```

### Example 5: Disable PKI

```python
from ghostman.src.infrastructure.pki import pki_service

# Disable PKI authentication
success = pki_service.disable_pki_authentication()

if success:
    print("PKI disabled, switched to standard authentication")
else:
    print("Failed to disable PKI")
```

### Example 6: Making API Requests with PKI

```python
from ghostman.src.infrastructure.ai.session_manager import session_manager

# PKI is automatically applied by session manager
# Just make requests normally:

response = session_manager.make_request(
    method="POST",
    url="https://api.example.com/v1/chat",
    json={"message": "Hello"},
    timeout=30
)

# Session manager automatically includes:
# - Client certificate (cert_path, key_path)
# - CA verification (ca_path or system bundle)
# - SSL verification settings
```

### Example 7: Custom Certificate Validation

```python
from ghostman.src.infrastructure.pki import pki_service

# Validate current certificates
is_valid = pki_service.validate_current_certificates()

if is_valid:
    print("Certificates are valid and not expired")
else:
    print("Certificate validation failed")

    # Get detailed status
    status = pki_service.get_certificate_status()

    for error in status.get('errors', []):
        print(f"Error: {error}")
```

### Example 8: Monitoring Certificate Expiration

```python
from ghostman.src.infrastructure.pki import pki_service

# Check for expiration warnings
warning = pki_service.get_certificate_expiry_warning()

if warning:
    print(f"Certificate Expiration Warning: {warning}")
    # Example output: "Certificate expires in 25 days"

    # Take action (e.g., notify user, send email)
    notify_admin(warning)
```

### Example 9: SSL Service Configuration

```python
from ghostman.src.infrastructure.ssl import ssl_service
from ghostman.src.infrastructure.pki import pki_service

# Configure SSL with PKI CA chain
ssl_service.configure_from_pki_service()

# Check verification status
status = ssl_service.get_status()

print(f"SSL Verification Enabled: {status['ssl_verification_enabled']}")
print(f"Custom CA Configured: {status['custom_ca_configured']}")
print(f"Verify Parameter: {status['verify_parameter']}")

# Test SSL configuration
test_result = ssl_service.test_ssl_configuration(
    test_url="https://www.google.com"
)

if test_result['success']:
    print("SSL configuration test passed")
```

### Example 10: Accessing Certificate Files

```python
from ghostman.src.infrastructure.pki import pki_service

# Get certificate file paths
cert_path, key_path = pki_service.cert_manager.get_client_cert_files()
ca_path = pki_service.cert_manager.get_ca_chain_file()

print(f"Client Certificate: {cert_path}")
print(f"Private Key: {key_path}")
print(f"CA Chain: {ca_path}")

# Use for custom operations (not recommended - use session_manager instead)
import requests
response = requests.get(
    "https://api.example.com",
    cert=(cert_path, key_path),
    verify=ca_path if ca_path else True
)
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: P12 Import Fails

**Symptoms:**
- Error: "Failed to parse P12 file"
- Import wizard shows failure

**Causes:**
- Incorrect password
- Corrupted P12 file
- Unsupported P12 format

**Solutions:**
```python
# 1. Verify P12 file integrity
import os
os.path.exists("path/to/file.p12")  # Should be True

# 2. Test password with OpenSSL
# openssl pkcs12 -info -in file.p12 -nodes

# 3. Convert P12 if needed
# openssl pkcs12 -in old.p12 -out new.p12 -export
```

#### Issue 2: Certificate Validation Fails

**Symptoms:**
- Error: "Certificate validation failed"
- PKI status shows "Invalid"

**Causes:**
- Expired certificate
- Clock skew (certificate not yet valid)
- Missing certificate files

**Solutions:**
```python
# Check certificate info
from ghostman.src.infrastructure.pki import pki_service

status = pki_service.get_certificate_status()
cert_info = status.get('certificate_info')

if cert_info:
    print(f"Valid from: {cert_info['not_valid_before']}")
    print(f"Valid until: {cert_info['not_valid_after']}")
    print(f"Days remaining: {cert_info['days_until_expiry']}")

# Check for errors
for error in status.get('errors', []):
    print(f"Error: {error}")
```

**Fix expired certificate:**
1. Obtain new certificate from CA
2. Run PKI wizard again
3. Import new P12 file

#### Issue 3: SSL Certificate Verification Errors

**Symptoms:**
- Error: "SSL: CERTIFICATE_VERIFY_FAILED"
- Connection tests fail

**Causes:**
- Missing CA chain
- Self-signed certificates
- Internal CA not trusted

**Solutions:**
```python
# Option 1: Import CA chain
from ghostman.src.infrastructure.pki import pki_service

ca_path = "C:/path/to/ca_chain.pem"
success = pki_service.cert_manager.import_ca_chain_file(ca_path)

if success:
    print("CA chain imported")
    # Re-test connection
    pki_service.test_pki_connection("https://api.example.com")

# Option 2: Temporarily disable SSL verification (development only)
from ghostman.src.infrastructure.storage.settings_manager import settings
settings.set('advanced.ignore_ssl_verification', True)

# Note: Re-enable for production!
settings.set('advanced.ignore_ssl_verification', False)
```

#### Issue 4: PKI Not Applied to Requests

**Symptoms:**
- Requests fail with authentication errors
- Server doesn't receive client certificate

**Causes:**
- PKI not initialized
- Session manager not configured
- Using raw requests instead of session_manager

**Solutions:**
```python
# 1. Initialize PKI
from ghostman.src.infrastructure.pki import pki_service
initialized = pki_service.initialize()
print(f"PKI Initialized: {initialized}")

# 2. Verify session manager has PKI
from ghostman.src.infrastructure.ai.session_manager import session_manager
pki_info = session_manager.get_pki_info()
print(f"Session Manager PKI: {pki_info}")

# 3. Use session_manager for requests (never raw requests)
# WRONG:
# import requests
# response = requests.get("https://api.example.com")

# CORRECT:
from ghostman.src.infrastructure.ai.session_manager import session_manager
response = session_manager.make_request(
    method="GET",
    url="https://api.example.com"
)
```

#### Issue 5: Certificate Files Not Found

**Symptoms:**
- Error: "Certificate files not found"
- FileNotFoundError

**Causes:**
- Certificate files deleted
- Incorrect file paths
- PKI directory permissions

**Solutions:**
```python
# Check PKI directory
from ghostman.src.infrastructure.pki import pki_service
import os

pki_dir = pki_service.cert_manager.pki_dir
print(f"PKI Directory: {pki_dir}")
print(f"Directory exists: {os.path.exists(pki_dir)}")

# List files
if os.path.exists(pki_dir):
    files = os.listdir(pki_dir)
    print(f"Files in PKI directory: {files}")

# Expected files:
# - client.crt
# - client.pem
# - ca_chain.pem (optional)

# If files missing, re-import P12
```

#### Issue 6: PKI Wizard Doesn't Show

**Symptoms:**
- PKI tab blank or shows placeholder
- Wizard import fails

**Causes:**
- Missing dependencies
- Theme system issues
- Import errors

**Solutions:**
```python
# Check imports
try:
    from ghostman.src.infrastructure.pki import pki_service
    print("PKI service import: OK")
except Exception as e:
    print(f"PKI service import failed: {e}")

try:
    from ghostman.src.presentation.wizards.pki_wizard import show_pki_wizard
    print("PKI wizard import: OK")
except Exception as e:
    print(f"PKI wizard import failed: {e}")

# Check logs for detailed error
# Location: %APPDATA%\Ghostman\logs\
```

#### Issue 7: Connection Timeout with PKI

**Symptoms:**
- Requests timeout
- Long delays before failure

**Causes:**
- Incorrect certificate
- Server rejecting client cert
- Network issues

**Solutions:**
```python
# Increase timeout
from ghostman.src.infrastructure.pki import pki_service

success, error = pki_service.test_pki_connection(
    test_url="https://api.example.com",
    max_attempts=3,
    ignore_ssl=False
)

# Check detailed error
if not success:
    print(f"Error details: {error}")

# Test without PKI to isolate issue
pki_service.disable_pki_authentication()
# Try request again
# If succeeds, problem is with PKI configuration
# If fails, problem is with network/server
```

#### Issue 8: Settings Not Persisting

**Symptoms:**
- PKI disabled after restart
- Configuration lost

**Causes:**
- Settings file write errors
- File permissions
- Settings manager issues

**Solutions:**
```python
# Check settings file
from ghostman.src.infrastructure.storage.settings_manager import settings
import os

settings_file = settings.settings_file
print(f"Settings file: {settings_file}")
print(f"File exists: {os.path.exists(settings_file)}")

# Manually verify PKI settings
pki_config = settings.get('pki')
print(f"PKI config: {pki_config}")

# Force save
settings.save()

# Check file permissions (Windows)
# Right-click settings.json → Properties → Security
# Ensure user has Write permission
```

### Diagnostic Commands

```python
# Complete PKI diagnostic
from ghostman.src.infrastructure.pki import pki_service
from ghostman.src.infrastructure.ssl import ssl_service
from ghostman.src.infrastructure.ai.session_manager import session_manager
import json

def diagnose_pki():
    """Run complete PKI diagnostics."""

    print("=== PKI Diagnostic Report ===\n")

    # 1. PKI Service Status
    print("1. PKI Service Status:")
    pki_service.initialize()
    status = pki_service.get_certificate_status()
    print(json.dumps(status, indent=2, default=str))

    # 2. SSL Service Status
    print("\n2. SSL Service Status:")
    ssl_status = ssl_service.get_status()
    print(json.dumps(ssl_status, indent=2, default=str))

    # 3. Session Manager PKI Info
    print("\n3. Session Manager PKI:")
    session_pki = session_manager.get_pki_info()
    print(json.dumps(session_pki, indent=2, default=str))

    # 4. Certificate Files
    print("\n4. Certificate Files:")
    cert_path, key_path = pki_service.cert_manager.get_client_cert_files()
    ca_path = pki_service.cert_manager.get_ca_chain_file()
    print(f"Client Cert: {cert_path}")
    print(f"Private Key: {key_path}")
    print(f"CA Chain: {ca_path}")

    # 5. File Existence
    print("\n5. File Existence:")
    import os
    if cert_path:
        print(f"Cert exists: {os.path.exists(cert_path)}")
    if key_path:
        print(f"Key exists: {os.path.exists(key_path)}")
    if ca_path:
        print(f"CA exists: {os.path.exists(ca_path)}")

    print("\n=== End Diagnostic Report ===")

# Run diagnostics
diagnose_pki()
```

### Getting Help

**Log Files:**
- Location: `%APPDATA%\Ghostman\logs\`
- PKI logs: Search for `ghostman.pki` logger
- Session logs: Search for `ghostman.session_manager`
- SSL logs: Search for `ghostman.ssl`

**Debug Mode:**
```bash
# Run Ghostman with debug logging
python -m ghostman --debug
```

**Community Support:**
- Check CLAUDE.md for architecture details
- Review source code in `ghostman/src/infrastructure/pki/`
- Check recent commits for PKI-related changes

---

## Appendix: Certificate File Format Details

### PEM Format
```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL0UG+0example...
(Base64-encoded certificate data)
...
-----END CERTIFICATE-----
```

### Certificate Chain Format
```
-----BEGIN CERTIFICATE-----
(Client Certificate)
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
(Intermediate CA)
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
(Root CA)
-----END CERTIFICATE-----
```

### Private Key Format (PKCS#8)
```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFexample...
(Base64-encoded key data)
...
-----END PRIVATE KEY-----
```

---

## Changelog

**October 2025 - Settings Consolidation:**
- Migrated PKI config from separate `pki_config.json` to main `settings.json`
- All PKI settings now under `pki` key in settings
- Automatic migration from old config file
- Single source of truth for all application settings

**September 2025 - SSL Service Integration:**
- Added centralized SSL verification service
- PKI CA chains integrated with SSL verification
- Unified SSL configuration across all requests
- Support for `ignore_ssl_verification` setting

**August 2025 - Initial PKI Implementation:**
- P12 certificate import
- Certificate validation
- PKI setup wizard
- Session manager integration
- Certificate expiration monitoring

---

## Summary

Ghostman's PKI implementation provides enterprise-grade certificate-based authentication with:

- **Easy Setup**: User-friendly wizard for certificate configuration
- **Automatic Management**: Certificate validation, expiration monitoring, and session integration
- **Flexible Configuration**: Support for various certificate formats and SSL verification modes
- **Secure Storage**: Certificates stored in user AppData with appropriate security
- **Comprehensive Integration**: Seamless integration with all HTTP requests via session manager
- **Robust Error Handling**: Detailed error messages and troubleshooting guidance

For most users, PKI is **optional** - standard API key authentication works for cloud services. Enable PKI only when your organization requires certificate-based authentication for internal APIs or enterprise services.
