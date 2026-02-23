# PKI Integration

## 1. Overview

PKI (Public Key Infrastructure) in Specter enables **mutual TLS (mTLS) authentication** with enterprise APIs. In a mutual TLS handshake:

- The **server** presents its certificate to the client (standard TLS).
- The **client** presents its own certificate and private key to the server, proving its identity.
- Optionally, a **custom CA chain** is used to verify the server's certificate instead of the system CA bundle.

This is commonly required in corporate environments where API endpoints enforce client certificate authentication.

---

## 2. Configuration Storage

All PKI settings are stored in `%APPDATA%\Specter\configs\settings.json` under the `pki` key:

```json
{
  "pki": {
    "enabled": true,
    "client_cert_path": "C:\\Users\\...\\AppData\\Roaming\\Specter\\pki\\client.crt",
    "client_key_path": "C:\\Users\\...\\AppData\\Roaming\\Specter\\pki\\client.pem",
    "ca_chain_path": "C:\\Users\\...\\AppData\\Roaming\\Specter\\pki\\ca_chain.pem",
    "p12_file_hash": "a1b2c3...",
    "last_validation": "2025-10-15T14:30:00",
    "certificate_info": {
      "subject": "CN=user@example.com",
      "issuer": "CN=Enterprise CA",
      "serial_number": "...",
      "not_valid_before": "2025-01-01T00:00:00",
      "not_valid_after": "2026-01-01T00:00:00",
      "fingerprint": "AA:BB:CC:...",
      "key_usage": ["digitalSignature", "keyEncipherment"],
      "is_valid": true,
      "days_until_expiry": 180
    }
  }
}
```

Certificate files are stored in:

```
%APPDATA%\Specter\pki\
    client.crt       # Client certificate (PEM-encoded X.509)
    client.pem       # Client private key (PEM-encoded, unencrypted)
    ca_chain.pem     # CA certificate chain (optional)
```

### Historical note

PKI configuration was previously stored in a separate `pki/pki_config.json` file. The `SettingsManager` automatically migrates this old format into `settings.json` on first load (see `_migrate_pki_config()`). The old file is renamed to `.json.bak` after migration.

---

## 3. How PKI Flows Through the System

```
User configures PKI in Settings Dialog --> PKI Auth tab
    |
    v
PKIService.setup_pki_authentication(p12_path, password)
    |
    v
CertificateManager.import_p12_file(p12_path, password)
    |
    +-- Extracts private key, certificate, and CA chain from P12
    +-- Writes client.crt, client.pem, ca_chain.pem to %APPDATA%\Specter\pki\
    +-- Validates certificates (expiry, key usage, etc.)
    +-- Saves paths + metadata to settings.json under pki.*
    |
    v
SettingsManager.set('pki.enabled', True)
    |
    v
SettingsManager._notify_change('pki.enabled')
    |
    v
SessionManager._on_settings_changed('pki.enabled')
    |
    +-- key starts with 'pki.' --> triggers reconfigure
    |
    v
SessionManager.reconfigure_security()
    |
    v
_compute_security_config()
    |
    +-- Reads pki.enabled = True from SettingsManager
    +-- Reads pki.client_cert_path, pki.client_key_path
    +-- Validates both files exist on disk
    +-- Reads pki.ca_chain_path, validates file exists
    +-- Returns { verify: ca_chain_path, cert: (cert_path, key_path) }
    |
    v
session.cert = (cert_path, key_path)
session.verify = ca_chain_path   (or True if no custom CA)
    |
    v
All subsequent HTTP requests via make_request() use mTLS
```

---

## 4. Key Components

### CertificateManager (`infrastructure/pki/certificate_manager.py`)

Low-level certificate operations:

- **`import_p12_file(p12_path, password)`** -- Extracts private key, client certificate, and CA chain from a PKCS#12 (.p12/.pfx) file. Writes the extracted components as PEM files to `%APPDATA%\Specter\pki\`.
- **`validate_certificates()`** -- Checks certificate validity (expiry, file existence, key matching).
- **`get_client_cert_files()`** -- Returns `(cert_path, key_path)` tuple.
- **`get_ca_chain_file()`** -- Returns CA chain path or `None`.
- **`is_pki_enabled()`** -- Reads `pki.enabled` from SettingsManager.
- **`get_certificate_info()`** -- Returns a `CertificateInfo` dataclass with subject, issuer, expiry, fingerprint, key usage, and validity status.
- **`disable_pki()`** -- Sets `pki.enabled = False` in settings.

Uses the `cryptography` library for all certificate parsing and P12 extraction.

### PKIService (`infrastructure/pki/pki_service.py`)

High-level orchestrator that coordinates between CertificateManager and SessionManager:

- **`setup_pki_authentication(p12_path, password)`** -- Full setup flow: import P12, validate, apply to session. Returns `(success, error_message)`.
- **`disable_pki_authentication()`** -- Disables PKI in CertificateManager and calls `session_manager.reconfigure_security()`.
- **`test_pki_connection(test_url, max_attempts, ignore_ssl)`** -- Tests mTLS authentication against a URL with retry logic (default 3 attempts, 2-second delay between retries).
- **`get_certificate_status()`** -- Returns comprehensive status including both CertificateManager state and SessionManager PKI info.
- **`get_certificate_expiry_warning()`** -- Returns a warning string if the certificate expires within 30 days.
- **`is_pki_required(test_url)`** -- Heuristic: temporarily disables PKI, makes a request, checks if the server returns 400/401/403.

Global instance: `pki_service = PKIService()`

### SessionManager.reconfigure_security() (`infrastructure/ai/session_manager.py`)

Reads PKI config from SettingsManager, validates file existence, dirty-checks, and applies to the session. See the [Unified Session Manager](unified-session-manager.md) documentation for full details.

### PKI Settings Widget (`presentation/widgets/pki_settings_widget.py`)

UI component in the Settings dialog (PKI Auth tab):

- File picker for P12/PFX certificate import.
- Password input for P12 decryption.
- Enable/disable toggle.
- Certificate info display (subject, issuer, expiry).
- Connection test button.

### SSLService (`infrastructure/ssl/ssl_service.py`)

Manages SSL verification independently from PKI. Provides a runtime `_ignore_ssl` flag that `_compute_security_config()` checks as an override. Delegates to `session_manager.reconfigure_security()` for all changes.

---

## 5. Certificate Validation

### At configuration time (fail-fast)

`_compute_security_config()` validates that certificate and key files exist on disk **when the configuration is computed**, not when the first HTTP request is made:

```python
cert_exists = Path(cert_path).exists()
key_exists = Path(key_path).exists()
if cert_exists and key_exists:
    cert = (cert_path, key_path)
else:
    # Log warning with missing file details
    # cert = None  (PKI silently disabled)
```

This fail-fast approach surfaces configuration problems immediately rather than at the first API call.

### At import time

`CertificateManager.validate_certificates()` performs deeper validation:

- Certificate file existence and readability.
- Certificate expiry (not yet expired).
- Private key format validity.
- P12 file hash consistency (detects if the source file was replaced).

### Certificate info

The `CertificateInfo` dataclass captures:

| Field               | Type             | Description                          |
| ------------------- | ---------------- | ------------------------------------ |
| `subject`           | `str`            | Certificate subject DN               |
| `issuer`            | `str`            | Issuer DN                            |
| `serial_number`     | `str`            | Serial number (hex)                  |
| `not_valid_before`  | `datetime`       | Start of validity period             |
| `not_valid_after`   | `datetime`       | End of validity period               |
| `fingerprint`       | `str`            | SHA-256 fingerprint                  |
| `key_usage`         | `List[str]`      | Key usage extensions                 |
| `is_valid`          | `bool`           | Currently valid                      |
| `days_until_expiry` | `int`            | Days until certificate expires       |

---

## 6. Disabling PKI

### Via the Settings UI

1. User unchecks "Enable PKI" in Settings > PKI Auth tab.
2. The UI calls `pki_service.disable_pki_authentication()`.
3. `CertificateManager.disable_pki()` sets `pki.enabled = False` in `settings.json`.
4. `SettingsManager._notify_change('pki.enabled')` fires.
5. `SessionManager._on_settings_changed('pki.enabled')` triggers `reconfigure_security()`.
6. `_compute_security_config()` returns `cert = None` (PKI disabled).
7. Session reverts to: `verify = True` (system CA), `cert = None` (no client cert).

### Programmatically

```python
from specter.src.infrastructure.pki.pki_service import pki_service

pki_service.disable_pki_authentication()
# Internally calls:
#   cert_manager.disable_pki()           --> sets pki.enabled = False
#   session_manager.reconfigure_security() --> reads new state, applies
```

Certificate files on disk are **not deleted** when PKI is disabled. They remain in `%APPDATA%\Specter\pki\` and can be re-enabled without re-importing.

---

## 7. Interaction with SSL Verification

PKI and SSL verification are **independent concerns** that can interact. The decision logic lives in a single method (`_compute_security_config()`) to prevent ordering bugs.

### Interaction matrix

| PKI enabled | ignore_ssl_verification | CA chain exists | `session.verify`  | `session.cert`         |
| ----------- | ----------------------- | --------------- | ----------------- | ---------------------- |
| No          | No                      | N/A             | `True`            | `None`                 |
| No          | Yes                     | N/A             | `False`           | `None`                 |
| Yes         | No                      | No              | `True`            | `(cert, key)`          |
| Yes         | No                      | Yes             | `ca_chain_path`   | `(cert, key)`          |
| Yes         | Yes                     | Yes             | `False`           | `(cert, key)`          |
| Yes         | Yes                     | No              | `False`           | `(cert, key)`          |

Key observations:

- `ignore_ssl_verification = True` **always wins** for the `verify` parameter, even if a CA chain is configured. This is intentional: if the user has explicitly disabled SSL verification, the CA chain is irrelevant.
- PKI client certificates are applied regardless of the SSL verification setting. You can have mTLS with `verify = False` (useful for testing against servers with self-signed certificates).
- The CA chain only affects `verify` when PKI is enabled and SSL verification is not disabled.

### Runtime SSL override

`SSLService` has a `_ignore_ssl` flag that can be set at runtime (e.g., during API testing) without persisting to `settings.json`. `_compute_security_config()` checks this flag as a secondary source:

```python
if not ignore_ssl:
    try:
        from ..ssl.ssl_service import ssl_service
        if ssl_service._initialized and ssl_service._ignore_ssl:
            ignore_ssl = True
    except Exception:
        pass
```

---

## 8. Troubleshooting

### Check logs for security reconfiguration

Every call to `reconfigure_security()` that changes the configuration logs a message:

```
Security reconfigured: SSL verification DISABLED, PKI=Yes
Security reconfigured: custom CA=C:\...\ca_chain.pem, PKI=Yes
Security reconfigured: system CA bundle, PKI=No
```

If the configuration is unchanged, it logs:

```
Security config unchanged, skipping reconfiguration
```

Search for `"Security reconfigured:"` in the application log to trace configuration changes.

### Inspect current PKI state programmatically

```python
from specter.src.infrastructure.ai.session_manager import session_manager

info = session_manager.get_pki_info()
print(info)
# {
#     'pki_enabled': True,
#     'cert_path': 'C:\\...\\client.crt',
#     'key_path': 'C:\\...\\client.pem',
#     'ca_path': 'C:\\...\\ca_chain.pem'
# }
```

### Inspect certificate details

```python
from specter.src.infrastructure.pki.pki_service import pki_service

status = pki_service.get_certificate_status()
# Returns: enabled, configured, valid, session_pki_enabled, cert info, errors

warning = pki_service.get_certificate_expiry_warning()
# Returns: "Certificate expires in 15 days" or None
```

### Common issues

| Symptom | Likely cause | Resolution |
| ------- | ------------ | ---------- |
| `PKI enabled but cert files not found` in logs | Certificate files deleted or moved | Re-import the P12 file via Settings > PKI Auth |
| `SSL: CERTIFICATE_VERIFY_FAILED` | CA chain missing or wrong | Import the correct CA chain, or enable "Ignore SSL Verification" for testing |
| PKI changes not taking effect | Observer not registered | Check that `session_manager._on_settings_changed` is in `settings._change_callbacks` |
| `RuntimeError: Session not configured` | `configure_session()` not called | Ensure `APIClient` or `AppCoordinator` has initialized before making requests |
| mTLS works in test but not in production | `configure_session()` recreated the session | Ensure `_configure_pki_if_enabled()` runs **after** `configure_session()` |

### Verify file paths

Check that the paths in `settings.json` match actual files on disk:

```
%APPDATA%\Specter\configs\settings.json   --> pki.client_cert_path, pki.client_key_path, pki.ca_chain_path
%APPDATA%\Specter\pki\                    --> client.crt, client.pem, ca_chain.pem
```

File existence is validated at configuration time by `_compute_security_config()`. If either the certificate or key file is missing, PKI is silently disabled (with a warning log) rather than causing a hard failure.

### Log locations

Application logs are written to `%APPDATA%\Specter\logs\`. Look for log entries from these loggers:

- `specter.session_manager` -- Session and security configuration
- `specter.pki.service` -- PKI service operations
- `specter.pki.certificate_manager` -- Certificate import and validation
- `specter.ssl.service` -- SSL verification configuration

---

## 9. Adding PKI Support to New Components

If you are adding a new component that makes HTTP requests, follow this pattern:

```python
from specter.src.infrastructure.ai.session_manager import session_manager

class MyNewService:
    def fetch_data(self, url: str) -> dict:
        """Fetch data from an API endpoint.

        PKI certificates, SSL verification, connection pooling,
        and retry logic are all handled automatically by session_manager.
        """
        response = session_manager.make_request('GET', url, timeout=15)
        response.raise_for_status()
        return response.json()
```

Do **not** import `requests` directly. Do **not** create your own `requests.Session`. Do **not** manually set `verify` or `cert` parameters on requests. The `session_manager` handles all of this centrally.

If your component needs to react to PKI configuration changes (e.g., to refresh a cached token), register an observer:

```python
from specter.src.infrastructure.storage.settings_manager import settings

def _on_pki_changed(key_path: str):
    if key_path.startswith('pki.'):
        self._invalidate_cached_token()

settings.on_change(_on_pki_changed)
```
