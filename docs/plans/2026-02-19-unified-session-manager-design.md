# Unified Session Manager Refactor

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make SessionManager the single source of truth for all HTTP security configuration (PKI + SSL), with automatic reconfiguration on settings changes.

**Architecture:** SessionManager reads PKI and SSL settings directly from SettingsManager via a single `reconfigure_security()` method. SettingsManager gains an observer pattern to notify SessionManager of changes. PKIService and SSLService stop manipulating the session directly and delegate to SessionManager.

**Tech Stack:** Python 3, requests, PyQt6 (signals not used in infrastructure — plain callbacks)

---

## Before/After Architecture

**Before (fragmented):**
```
SSLService → owns verify state → manipulates session.verify
PKIService → owns cert state  → manipulates session.cert
SessionManager → applies both in wrong order, has ordering bug
SettingsManager → no change notification
api_test_service → breaks encapsulation to work around session recreation
```

**After (unified):**
```
SettingsManager (source of truth, with change callbacks)
       │ on_change()
       ▼
SessionManager.reconfigure_security()  ← THE SINGLE METHOD
       │ reads settings directly
       │ validates cert files
       │ computes verify + cert atomically
       │ dirty-checks before applying
       ▼
All HTTP requests use correct config
```

---

### Task 1: Add Settings Change Observer to SettingsManager

**Files:**
- Modify: `specter/src/infrastructure/storage/settings_manager.py`

Add `_change_callbacks` list, `on_change(callback)`, and `_notify_change(key)`. Call `_notify_change` from `set()` and `delete()`.

### Task 2: Add `reconfigure_security()` to SessionManager

**Files:**
- Modify: `specter/src/infrastructure/ai/session_manager.py`

Single method that:
1. Reads `advanced.ignore_ssl_verification` from SettingsManager
2. Reads `pki.enabled`, `pki.client_cert_path`, `pki.client_key_path`, `pki.ca_chain_path`
3. Validates cert file existence
4. Computes final `verify` and `cert` values
5. Dirty-checks against current session state
6. Applies atomically with proper locking and logging

### Task 3: Refactor `configure_session()` to Use Unified Flow

**Files:**
- Modify: `specter/src/infrastructure/ai/session_manager.py`

- Remove inline `_apply_pki_config()` call (line 133-134)
- Remove inline SSL block (lines 136-161)
- Call `reconfigure_security()` at the end instead
- Remove deprecated `disable_ssl_verification` parameter
- Keep `configure_pki()` and `disable_pki()` as thin wrappers that call `reconfigure_security()`

### Task 4: Update PKIService to Use `reconfigure_security()`

**Files:**
- Modify: `specter/src/infrastructure/pki/pki_service.py`

- `_apply_pki_to_session()`: Call `session_manager.reconfigure_security()` instead of `session_manager.configure_pki()`
- `disable_pki_authentication()`: Call `session_manager.reconfigure_security()` instead of `session_manager.disable_pki()`
- Remove `ssl_service.configure_from_pki_service()` calls — SessionManager now reads settings directly

### Task 5: Simplify SSLService

**Files:**
- Modify: `specter/src/infrastructure/ssl/ssl_service.py`

- `configure_session_manager()`: Call `session_manager.reconfigure_security()` instead of `session_manager.configure_session()`
- `configure_from_pki_service()`: Call `session_manager.reconfigure_security()` instead of full session recreation
- Keep `get_verify_parameter()` and `get_status()` for backward compat (read-only queries are fine)

### Task 6: Fix api_test_service.py Encapsulation

**Files:**
- Modify: `specter/src/infrastructure/ai/api_test_service.py`

Replace direct `_session.verify` access (line 309-310) with `session_manager.reconfigure_security()`. Remove the PKI-detection workaround since `reconfigure_security()` uses dirty-checking.

### Task 7: Fix web_loader.py Fallback

**Files:**
- Modify: `specter/src/infrastructure/rag_pipeline/document_loaders/web_loader.py`

Remove the `requests.get()` fallback. Make session_manager import non-optional (it's a core dependency). If import truly fails, raise an error.

### Task 8: Clean Up app_coordinator.py

**Files:**
- Modify: `specter/src/application/app_coordinator.py`

- Remove the deprecated fallback in `_apply_advanced_settings()` (lines 1069-1081)
- Simplify `_reinitialize_ssl_pki_services()` to call `session_manager.reconfigure_security()`
- Wire up `settings.on_change()` callback at startup

---

## Key Design Decisions

1. **No PyQt signals in infrastructure** — SettingsManager uses plain callbacks to stay framework-agnostic
2. **Dirty-checking** — `reconfigure_security()` compares current vs. computed state, skips if unchanged
3. **Atomic application** — verify + cert are set together under the session lock
4. **Backward compat** — `configure_pki()` / `disable_pki()` / `get_verify_parameter()` still work but delegate internally
5. **Fail-fast cert validation** — cert/key files validated at config time, not at first request
