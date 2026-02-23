# Unified Session Manager

## 1. Overview

`SessionManager` is a **thread-safe singleton** located at
`specter/src/infrastructure/ai/session_manager.py`.

It serves as the single source of truth for:

- **PKI client certificates** (mutual TLS)
- **SSL/TLS verification** (system CA, custom CA chain, or disabled)
- **Connection pooling** (via `requests.Session` + `HTTPAdapter`)
- **Retry logic** (exponential backoff on 429/5xx)

**All HTTP requests in the application MUST go through
`session_manager.make_request()`.**  Direct use of `requests.get()`,
`requests.post()`, or raw `requests.Session()` objects is prohibited
because it bypasses PKI certificates, SSL configuration, connection
pooling, and centralized error handling.

The global instance is created at module load time:

```python
# specter/src/infrastructure/ai/session_manager.py  (bottom of file)
session_manager = SessionManager()
```

---

## 2. Architecture

```
SettingsManager (settings.json) ──on_change()──> SessionManager._on_settings_changed()
                                                        |
                                                        v
                                                 reconfigure_security()
                                                        |
                                                        +-- Calls _compute_security_config()
                                                        |       |
                                                        |       +-- Reads pki.enabled
                                                        |       +-- Reads pki.client_cert_path
                                                        |       +-- Reads pki.client_key_path
                                                        |       +-- Reads pki.ca_chain_path
                                                        |       +-- Reads advanced.ignore_ssl_verification
                                                        |       +-- Reads ssl_service._ignore_ssl (runtime override)
                                                        |       +-- Validates cert file existence
                                                        |       +-- Returns {verify, cert}
                                                        |
                                                        +-- Dirty-checks vs current session state
                                                        +-- Applies session.verify + session.cert atomically under RLock
```

The design ensures there is **one decision tree** for security configuration, eliminating ordering bugs that arise when PKI and SSL are configured independently.

---

## 3. Key Methods

### `configure_session(timeout, max_retries, backoff_factor, pool_connections, pool_maxsize, pool_block)`

Creates (or recreates) the underlying `requests.Session` with connection pooling and retry adapters.

- Closes any existing session before creating a new one.
- Mounts `HTTPAdapter` instances on both `http://` and `https://` prefixes.
- Sets default headers: `User-Agent: Specter/1.0.0`, `Accept: application/json`, `Content-Type: application/json`.
- **Calls `reconfigure_security()` at the end**, inside the same lock acquisition. This is safe because the lock is reentrant (`RLock`), and it prevents a TOCTOU race where another thread could use the session before security settings are applied.

**Parameters:**

| Parameter          | Type    | Default | Description                                       |
| ------------------ | ------- | ------- | ------------------------------------------------- |
| `timeout`          | `int`   | `30`    | Default request timeout in seconds                |
| `max_retries`      | `int`   | `3`     | Max retries for failed requests                   |
| `backoff_factor`   | `float` | `0.3`   | Exponential backoff multiplier                    |
| `pool_connections` | `int`   | `10`    | Number of connection pools to cache               |
| `pool_maxsize`     | `int`   | `20`    | Maximum connections per pool                      |
| `pool_block`       | `bool`  | `False` | Block when pool is at max capacity                |

**Retry status codes:** 429, 500, 502, 503, 504. All HTTP methods are retried (including POST).

---

### `reconfigure_security()`

**THE single entry point for all security configuration changes.**

1. Calls `_compute_security_config()` to read the current state from SettingsManager.
2. Acquires the session lock.
3. If no session exists yet, stores the computed config for later (when `configure_session()` runs).
4. **Dirty-checks** against the current `session.verify` and `session.cert`. If nothing changed, returns immediately (no-op).
5. Applies `session.cert` and `session.verify` atomically.
6. Keeps `_pki_config` in sync for `get_pki_info()`.
7. Suppresses urllib3 `InsecureRequestWarning` when SSL verification is disabled.
8. Logs the resulting configuration.

Safe to call repeatedly -- it is designed to no-op when the configuration has not changed.

---

### `_compute_security_config()`

Internal method. Reads all PKI and SSL settings from SettingsManager and returns a dict with two keys:

```python
{
    'verify': bool | str,   # False, True, or path to CA chain
    'cert': tuple | None    # (cert_path, key_path) or None
}
```

This method also checks `ssl_service._ignore_ssl` as a runtime override (for cases like API testing where SSL is temporarily disabled without persisting to settings).

See Section 5 for the full decision tree.

---

### `_on_settings_changed(key_path)`

Callback registered with `SettingsManager.on_change()` during `__init__()`. Triggers `reconfigure_security()` when any of these key prefixes change:

- `pki.*`
- `advanced.ignore_ssl_verification`
- `advanced.custom_ca_path`

---

### `make_request(method, url, timeout=None, **kwargs)`

The **only way** to make HTTP requests in Specter.

- Acquires the session lock via the `get_session()` context manager.
- Uses the configured timeout if none is provided.
- Passes all `**kwargs` through to `session.request()`.
- Logs the request method, URL, and response status code.
- Raises `requests.RequestException` on failure, `RuntimeError` if the session has not been configured.

---

### `configure_pki(cert_path, key_path, ca_path=None)`

Convenience wrapper. Stores the PKI config tuple and delegates to `reconfigure_security()`. Callers should ensure `settings.json` is already updated before calling this, because `reconfigure_security()` reads the authoritative state from SettingsManager.

### `disable_pki()`

Clears `_pki_config` and delegates to `reconfigure_security()`. The session reverts to `verify=True`, `cert=None` (assuming SSL verification is not also disabled).

### `get_pki_info()`

Returns a dict with the current PKI state:

```python
{
    "pki_enabled": True,
    "cert_path": "C:\\...\\client.crt",
    "key_path": "C:\\...\\client.pem",
    "ca_path": "C:\\...\\ca_chain.pem"
}
```

### `get_session()`

Context manager that yields the configured `requests.Session` under the lock. Raises `RuntimeError` if the session has not been created via `configure_session()`.

### `update_headers(headers)` / `remove_headers(header_names)`

Thread-safe methods to add or remove default headers on the session.

### `get_connection_info()`

Returns a diagnostic dict with session status, adapter info, headers, and PKI info.

### `close()`

Closes the session and clears all adapters. Also called by `__del__()`.

---

## 4. Settings Keys That Affect Security

These keys in `%APPDATA%\Specter\configs\settings.json` drive the security configuration:

```
pki.enabled                        -> bool    Whether PKI mutual TLS is active
pki.client_cert_path               -> str     Path to client certificate (.crt)
pki.client_key_path                -> str     Path to client private key (.pem)
pki.ca_chain_path                  -> str     Path to CA chain bundle (.pem)
advanced.ignore_ssl_verification   -> bool    Disable all SSL certificate verification
advanced.custom_ca_path            -> str     Custom CA bundle path (not currently
                                              used by _compute_security_config directly;
                                              PKI ca_chain_path takes precedence)
```

All of these are watched by `_on_settings_changed()` and trigger automatic reconfiguration.

---

## 5. Decision Tree for `verify` and `cert`

`_compute_security_config()` uses the following logic:

### `verify` parameter

```
Is advanced.ignore_ssl_verification == True?
  OR ssl_service._ignore_ssl == True (runtime override)?
    YES --> verify = False
    NO  --> Is PKI enabled AND ca_chain_path file exists?
              YES --> verify = ca_chain_path   (custom CA bundle)
              NO  --> verify = True            (system CA bundle)
```

### `cert` parameter

```
Is PKI enabled AND cert_path AND key_path are set?
    YES --> Do both files exist on disk?
              YES --> cert = (cert_path, key_path)
              NO  --> cert = None  (log warning with missing file paths)
    NO  --> cert = None
```

File existence is validated at configuration time (fail-fast), not deferred to the first HTTP request. If either the certificate or key file is missing, PKI is silently disabled with a warning in the log.

---

## 6. Reactive Settings Changes

The system uses an observer pattern to propagate settings changes without requiring an application restart.

### How it works

1. **SettingsManager** maintains a list of callbacks registered via `on_change(callback)`.
2. **SessionManager** registers itself during `__init__()`:
   ```python
   settings.on_change(self._on_settings_changed)
   ```
3. When any setting is modified via `settings.set(key_path, value)`, SettingsManager calls `_notify_change(key_path)`, which invokes all registered callbacks.
4. `SessionManager._on_settings_changed()` checks whether the changed key starts with a security-relevant prefix (`pki.`, `advanced.ignore_ssl_verification`, `advanced.custom_ca_path`). If so, it calls `reconfigure_security()`.
5. The new security configuration takes **immediate effect** on all subsequent HTTP requests. No restart needed.

### Sequence diagram

```
User toggles PKI in Settings UI
    |
    v
settings.set('pki.enabled', True)
    |
    v
SettingsManager._notify_change('pki.enabled')
    |
    v
SessionManager._on_settings_changed('pki.enabled')
    |
    +-- key starts with 'pki.' --> YES
    |
    v
SessionManager.reconfigure_security()
    |
    v
_compute_security_config()  -->  reads fresh values from SettingsManager
    |
    v
Dirty-check  -->  config changed  -->  apply session.verify + session.cert
    |
    v
All subsequent make_request() calls use the new security config
```

---

## 7. Thread Safety

### Lock design

SessionManager uses `threading.RLock()` (reentrant lock) stored as `self._session_lock`.

**Why `RLock` instead of `Lock`?**
`configure_session()` calls `reconfigure_security()` internally. Both methods acquire `_session_lock`. A regular `Lock` would deadlock in this scenario. `RLock` allows the same thread to re-acquire the lock it already holds.

### Methods that acquire the lock

| Method                   | Lock acquisition                          |
| ------------------------ | ----------------------------------------- |
| `configure_session()`   | `with self._session_lock:` (entire body)  |
| `reconfigure_security()`| `with self._session_lock:` (apply phase)  |
| `make_request()`        | Via `get_session()` context manager        |
| `configure_pki()`       | `with self._session_lock:`                |
| `disable_pki()`         | `with self._session_lock:`                |
| `update_headers()`      | `with self._session_lock:`                |
| `remove_headers()`      | `with self._session_lock:`                |
| `get_pki_info()`        | `with self._session_lock:`                |
| `close()`               | `with self._session_lock:`                |
| `is_configured`         | `with self._session_lock:` (property)     |

### Singleton creation

The singleton uses a class-level `threading.Lock()` with double-checked locking in `__new__()`:

```python
if cls._instance is None:
    with cls._lock:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
```

---

## 8. Integration Points

### PKIService (`infrastructure/pki/pki_service.py`)

- `disable_pki_authentication()` calls `session_manager.reconfigure_security()` after clearing PKI settings.
- `_apply_pki_to_session()` calls `session_manager.reconfigure_security()` after cert import.
- `test_pki_connection()` uses `session_manager.make_request()` and `session_manager.configure_session()`.

### SSLService (`infrastructure/ssl/ssl_service.py`)

- `configure_session_manager()` calls `session_manager.reconfigure_security()`.
- `configure_from_settings()` calls `session_manager.reconfigure_security()`.
- `configure_from_pki_service()` calls `session_manager.reconfigure_security()`.
- `ssl_service._ignore_ssl` is read as a runtime override by `_compute_security_config()`.

### AIService (`infrastructure/ai/ai_service.py`)

- `initialize()` creates an `OpenAICompatibleClient` (which calls `configure_session()`), then calls `_configure_pki_if_enabled()`.
- `_configure_pki_if_enabled()` reads cert paths from `PKIService` and calls `session_manager.configure_pki()`.

### APIClient (`infrastructure/ai/api_client.py`)

- `OpenAICompatibleClient.__init__()` calls `session_manager.configure_session()` with the configured timeout and retry settings. This triggers `reconfigure_security()` internally.
- `_make_api_request()` calls `session_manager.make_request()`.

### APITestService (`infrastructure/ai/api_test_service.py`)

- `_configure_session_for_testing()` calls `session_manager.configure_session()` with test-specific parameters (lower timeouts, no retries).

### WebSearchSkill (`infrastructure/skills/skills_library/web_search_skill.py`)

- Uses `session_manager.make_request()` for all search HTTP requests. Inherits all PKI and SSL configuration automatically.

### RAG Pipeline (`infrastructure/rag_pipeline/`)

- `web_loader.py` uses `session_manager.make_request()` for loading web documents.
- `embedding_service.py` uses `session_manager.make_request()` for embedding API calls.
- `rag_pipeline.py` and `safe_rag_pipeline.py` use `session_manager.make_request()` for RAG API calls.

### AppCoordinator (`application/app_coordinator.py`)

- Calls `session_manager.reconfigure_security()` during application startup to ensure security configuration is applied.

---

## 9. Common Patterns

### Making HTTP requests (correct)

```python
from specter.src.infrastructure.ai.session_manager import session_manager

# Simple GET
response = session_manager.make_request('GET', url, headers={'X-Custom': 'value'}, timeout=15)

# POST with JSON body
response = session_manager.make_request('POST', url, json={'key': 'value'})

# The session automatically includes:
#   - PKI client certificate (if enabled)
#   - SSL verification (system CA, custom CA, or disabled)
#   - Connection pooling and retry logic
#   - Default headers (User-Agent, Accept, Content-Type)
```

### Making HTTP requests (WRONG -- never do this)

```python
import requests

# BAD: bypasses PKI, SSL config, connection pooling, retry logic
response = requests.get(url)

# BAD: creates a separate session outside the managed singleton
session = requests.Session()
response = session.get(url)
```

### Reacting to settings changes from other components

```python
from specter.src.infrastructure.storage.settings_manager import settings

def my_callback(key_path: str):
    if key_path.startswith('my_feature.'):
        # React to changes in my_feature.* settings
        reconfigure_my_feature()

settings.on_change(my_callback)
```

### Checking current security configuration

```python
from specter.src.infrastructure.ai.session_manager import session_manager

# Get PKI info
pki_info = session_manager.get_pki_info()
# {'pki_enabled': True, 'cert_path': '...', 'key_path': '...', 'ca_path': '...'}

# Get full connection info (includes headers, adapter config, PKI)
conn_info = session_manager.get_connection_info()
```

---

## 10. Startup Sequence

The security configuration is applied multiple times during startup to handle dependency ordering:

1. **Module load:** `session_manager = SessionManager()` is created. It attempts to register with SettingsManager via `on_change()`. If SettingsManager is not yet importable (circular dependency), registration is deferred.

2. **APIClient creation:** `OpenAICompatibleClient.__init__()` calls `configure_session()`, which creates the `requests.Session` and calls `reconfigure_security()`. At this point, PKI and SSL settings from `settings.json` are applied.

3. **AIService initialization:** After creating the APIClient, `_configure_pki_if_enabled()` is called. This is a belt-and-suspenders call that ensures PKI is applied even if the reactive path missed it.

4. **AppCoordinator startup:** Calls `session_manager.reconfigure_security()` as a final safety net.

After startup, all changes flow through the reactive observer pattern (Section 6).
