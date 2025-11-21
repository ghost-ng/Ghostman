"""
PKI Certificate Manager for Ghostman.

Handles P12 certificate files, conversion to PEM/CRT formats,
certificate validation, and secure storage management.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509

logger = logging.getLogger("ghostman.pki.certificate_manager")


@dataclass
class CertificateInfo:
    """Information about a certificate."""
    subject: str
    issuer: str
    serial_number: str
    not_valid_before: datetime
    not_valid_after: datetime
    fingerprint: str
    key_usage: List[str]
    is_valid: bool
    days_until_expiry: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['not_valid_before'] = self.not_valid_before.isoformat()
        data['not_valid_after'] = self.not_valid_after.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CertificateInfo':
        """Create from dictionary."""
        data['not_valid_before'] = datetime.fromisoformat(data['not_valid_before'])
        data['not_valid_after'] = datetime.fromisoformat(data['not_valid_after'])
        return cls(**data)


@dataclass
class PKIConfig:
    """PKI configuration settings."""
    enabled: bool = False
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    ca_chain_path: Optional[str] = None
    p12_file_hash: Optional[str] = None
    last_validation: Optional[datetime] = None
    certificate_info: Optional[CertificateInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_validation:
            data['last_validation'] = self.last_validation.isoformat()
        if self.certificate_info:
            data['certificate_info'] = self.certificate_info.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PKIConfig':
        """Create from dictionary."""
        if 'last_validation' in data and data['last_validation']:
            data['last_validation'] = datetime.fromisoformat(data['last_validation'])
        if 'certificate_info' in data and data['certificate_info']:
            data['certificate_info'] = CertificateInfo.from_dict(data['certificate_info'])
        return cls(**data)


class PKIError(Exception):
    """Base PKI exception."""
    pass


class CertificateValidationError(PKIError):
    """Certificate validation failed."""
    pass


class P12ImportError(PKIError):
    """P12 file import failed."""
    pass


class CertificateManager:
    """
    Manages PKI certificates for API client authentication.
    
    Handles:
    - P12 file import and conversion
    - Certificate validation and chain verification
    - Secure storage in user AppData
    - Certificate expiration monitoring
    """
    
    def __init__(self):
        """Initialize certificate manager."""
        self.pki_dir = self._get_pki_directory()
        # NOTE: config_file is DEPRECATED - now using main settings
        self.config_file = self.pki_dir / "pki_config.json"
        self._config: Optional[PKIConfig] = None

        # Ensure PKI directory exists
        self.pki_dir.mkdir(parents=True, exist_ok=True)

        # Load existing configuration from main settings
        self.load_config()

        logger.info(f"PKI Certificate Manager initialized: {self.pki_dir}")
    
    def _get_pki_directory(self) -> Path:
        """Get PKI directory in user AppData."""
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA', '')
            if not appdata:
                raise PKIError("APPDATA environment variable not found")
            return Path(appdata) / "Ghostman" / "pki"
        else:  # Linux/Mac
            home = os.path.expanduser("~")
            return Path(home) / ".Ghostman" / "pki"
    
    def load_config(self) -> PKIConfig:
        """Load PKI configuration from main settings."""
        try:
            from ..storage.settings_manager import settings
            pki_data = settings.get('pki', {})

            if pki_data and isinstance(pki_data, dict):
                # Use from_dict to properly convert certificate_info dict to CertificateInfo object
                self._config = PKIConfig.from_dict(pki_data)
                logger.debug("PKI configuration loaded from main settings")
            else:
                self._config = PKIConfig()
                logger.debug("No PKI configuration found, using defaults")

        except Exception as e:
            logger.error(f"Failed to load PKI config from settings: {e}")
            self._config = PKIConfig()

        return self._config
    
    def save_config(self) -> bool:
        """Save PKI configuration to main settings."""
        try:
            if self._config:
                from ..storage.settings_manager import settings

                # Convert config to dict
                pki_data = self._config.to_dict()

                # CRITICAL FIX: Update the entire PKI object at once
                # This prevents partial saves if any individual set() fails
                # and reduces 7 file writes to 1
                current_settings = settings.get_all()
                current_settings['pki'] = pki_data

                # Save directly to settings file
                settings._settings['pki'] = pki_data
                settings.save()

                logger.info(f"✓ PKI configuration saved: enabled={pki_data.get('enabled')}, cert_path={pki_data.get('client_cert_path')}")
                logger.debug(f"PKI data saved: {pki_data}")
                return True
        except Exception as e:
            logger.error(f"Failed to save PKI config to settings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    def import_p12_file(self, p12_path: str, password: str) -> bool:
        """
        Import P12 certificate file and extract certificates.
        
        Args:
            p12_path: Path to P12 file
            password: P12 file password
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Importing P12 file: {p12_path}")
            
            # Read P12 file
            with open(p12_path, 'rb') as f:
                p12_data = f.read()
            
            # Parse P12 file
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    p12_data, 
                    password.encode() if password else None
                )
            except Exception as e:
                raise P12ImportError(f"Failed to parse P12 file: {e}")
            
            if not private_key or not certificate:
                raise P12ImportError("P12 file does not contain required private key and certificate")
            
            # Calculate file hash for tracking changes (without copying the file)
            file_hash = hashlib.sha256(p12_data).hexdigest()
            
            # Store the original P12 file path for reference (do not copy the file)
            original_p12_path = p12_path
            
            # Extract and save private key
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            key_path = self.pki_dir / "client.pem"
            with open(key_path, 'wb') as f:
                f.write(key_pem)
            
            # Extract and save certificate
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
            cert_path = self.pki_dir / "client.crt"
            with open(cert_path, 'wb') as f:
                f.write(cert_pem)
            
            # Save certificate chain if available
            chain_path = None
            if additional_certificates:
                chain_pem = b""
                for cert in additional_certificates:
                    chain_pem += cert.public_bytes(serialization.Encoding.PEM)
                chain_path = self.pki_dir / "ca_chain.pem"
                with open(chain_path, 'wb') as f:
                    f.write(chain_pem)
            
            # Extract certificate information
            cert_info = self._extract_certificate_info(certificate)
            
            # Update configuration
            self._config = PKIConfig(
                enabled=True,
                client_cert_path=str(cert_path),
                client_key_path=str(key_path),
                ca_chain_path=str(chain_path) if chain_path else None,
                p12_file_hash=file_hash,
                last_validation=datetime.now(timezone.utc),
                certificate_info=cert_info
            )
            
            # Save configuration
            if self.save_config():
                logger.info("✓ P12 certificate imported successfully")
                return True
            else:
                raise PKIError("Failed to save PKI configuration")
                
        except Exception as e:
            logger.error(f"✗ P12 import failed: {e}")
            # Clean up any partial files
            self._cleanup_certificate_files()
            raise P12ImportError(f"Failed to import P12 file: {e}")
    
    def _extract_certificate_info(self, certificate: x509.Certificate) -> CertificateInfo:
        """Extract information from a certificate."""
        try:
            # Basic certificate info
            subject = certificate.subject.rfc4514_string()
            issuer = certificate.issuer.rfc4514_string()
            serial_number = str(certificate.serial_number)
            not_valid_before = certificate.not_valid_before
            not_valid_after = certificate.not_valid_after
            
            # Calculate fingerprint
            fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
            
            # Extract key usage
            key_usage = []
            try:
                key_usage_ext = certificate.extensions.get_extension_for_oid(
                    x509.ExtensionOID.KEY_USAGE
                ).value
                if key_usage_ext.digital_signature:
                    key_usage.append("Digital Signature")
                if key_usage_ext.key_encipherment:
                    key_usage.append("Key Encipherment")
                if key_usage_ext.key_agreement:
                    key_usage.append("Key Agreement")
            except x509.ExtensionNotFound:
                pass
            
            # Check validity - ensure we handle timezone-aware comparisons properly
            now = datetime.now(timezone.utc)
            
            # Certificate times are typically UTC but might be naive
            # Convert certificate times to UTC if they're naive
            if not_valid_before.tzinfo is None:
                not_valid_before = not_valid_before.replace(tzinfo=timezone.utc)
            if not_valid_after.tzinfo is None:
                not_valid_after = not_valid_after.replace(tzinfo=timezone.utc)
            
            is_valid = not_valid_before <= now <= not_valid_after
            days_until_expiry = (not_valid_after - now).days
            
            return CertificateInfo(
                subject=subject,
                issuer=issuer,
                serial_number=serial_number,
                not_valid_before=not_valid_before,
                not_valid_after=not_valid_after,
                fingerprint=fingerprint,
                key_usage=key_usage,
                is_valid=is_valid,
                days_until_expiry=days_until_expiry
            )
            
        except Exception as e:
            logger.error(f"Failed to extract certificate info: {e}")
            raise CertificateValidationError(f"Failed to extract certificate information: {e}")
    
    def _parse_ca_chain_file(self, ca_data: bytes) -> bytes:
        """
        Parse CA chain file in various formats and return as PEM.
        
        Supports:
        - Single or multiple PEM certificates
        - Single or multiple DER certificates (common in .crt/.cer files)
        - Mixed format chains
        
        Args:
            ca_data: Raw certificate data
            
        Returns:
            bytes: PEM formatted certificate chain
        """
        try:
            # Check if it's already PEM format (most common)
            if b'-----BEGIN CERTIFICATE-----' in ca_data:
                # Handle PEM format - could contain multiple certificates
                logger.debug("Processing PEM format CA chain")
                return ca_data
            
            # Try to parse as DER format (binary certificate files)
            logger.debug("Attempting to parse as DER format")
            
            # For DER format, try to parse as a single certificate first
            try:
                certificate = x509.load_der_x509_certificate(ca_data)
                pem_data = certificate.public_bytes(serialization.Encoding.PEM)
                logger.debug("Successfully converted single DER certificate to PEM")
                return pem_data
            except Exception:
                # If single certificate fails, the file might contain multiple DER certificates
                # or be in an unsupported format
                logger.debug("Single DER certificate parsing failed, trying alternative approaches")
            
            # Try to split the data and parse multiple potential DER certificates
            # This handles the case where multiple DER certificates are concatenated
            certificates_pem = b""
            offset = 0
            cert_count = 0
            
            while offset < len(ca_data):
                # DER certificates typically start with 0x30 (SEQUENCE tag)
                # followed by length encoding
                if offset + 2 >= len(ca_data):
                    break
                    
                if ca_data[offset] != 0x30:
                    # Not a DER certificate start, skip this byte
                    offset += 1
                    continue
                
                # Try to parse certificate starting at this offset
                remaining_data = ca_data[offset:]
                try:
                    certificate = x509.load_der_x509_certificate(remaining_data)
                    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
                    certificates_pem += cert_pem
                    cert_count += 1
                    
                    # Calculate the actual certificate size to move offset correctly
                    # For simplicity, we'll try to encode it back and measure
                    der_bytes = certificate.public_bytes(serialization.Encoding.DER)
                    offset += len(der_bytes)
                    logger.debug(f"Successfully parsed DER certificate {cert_count}")
                    
                except Exception:
                    # Couldn't parse at this position, move to next byte
                    offset += 1
                    continue
            
            if cert_count > 0:
                logger.debug(f"Successfully converted {cert_count} DER certificate(s) to PEM")
                return certificates_pem
            
            # If we get here, we couldn't parse the data
            # Try one more approach: check if it might be base64 encoded
            try:
                import base64
                decoded_data = base64.b64decode(ca_data)
                # Recursively try to parse the decoded data
                return self._parse_ca_chain_file(decoded_data)
            except Exception:
                pass
            
            raise PKIError("Unable to parse certificate data in any known format (PEM, DER, or Base64)")
            
        except PKIError:
            # Re-raise PKI errors as-is
            raise
        except Exception as e:
            raise PKIError(f"Unexpected error parsing CA chain file: {e}")
    
    def validate_certificates(self) -> bool:
        """
        Validate current certificates and chain.
        
        Returns:
            True if certificates are valid
        """
        try:
            if not self._config or not self._config.enabled:
                return False
            
            if not self._config.client_cert_path or not self._config.client_key_path:
                return False
            
            cert_path = Path(self._config.client_cert_path)
            key_path = Path(self._config.client_key_path)
            
            if not cert_path.exists() or not key_path.exists():
                logger.warning("Certificate files not found")
                return False
            
            # Load certificate
            with open(cert_path, 'rb') as f:
                cert_pem = f.read()
            certificate = x509.load_pem_x509_certificate(cert_pem)
            
            # Check expiration - use timezone-aware datetime
            now = datetime.now(timezone.utc)
            
            # Certificate times are typically UTC but might be naive
            not_valid_before = certificate.not_valid_before
            not_valid_after = certificate.not_valid_after
            
            if not_valid_before.tzinfo is None:
                not_valid_before = not_valid_before.replace(tzinfo=timezone.utc)
            if not_valid_after.tzinfo is None:
                not_valid_after = not_valid_after.replace(tzinfo=timezone.utc)
            
            if not_valid_after <= now:
                logger.error("Certificate has expired")
                return False
            
            if not_valid_before > now:
                logger.error("Certificate is not yet valid")
                return False
            
            # Update certificate info
            self._config.certificate_info = self._extract_certificate_info(certificate)
            self._config.last_validation = datetime.now(timezone.utc)
            self.save_config()
            
            # Check if expiring soon (30 days)
            days_until_expiry = (not_valid_after - now).days
            if days_until_expiry <= 30:
                logger.warning(f"Certificate expires in {days_until_expiry} days")
            
            logger.info("✓ Certificate validation successful")
            return True
            
        except Exception as e:
            logger.error(f"✗ Certificate validation failed: {e}")
            return False
    
    def get_client_cert_files(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get client certificate and key file paths.
        
        Returns:
            Tuple of (cert_path, key_path) or (None, None) if not available
        """
        if (self._config and self._config.enabled and 
            self._config.client_cert_path and self._config.client_key_path):
            
            cert_path = Path(self._config.client_cert_path)
            key_path = Path(self._config.client_key_path)
            
            if cert_path.exists() and key_path.exists():
                return str(cert_path), str(key_path)
        
        return None, None
    
    def get_ca_chain_file(self) -> Optional[str]:
        """
        Get CA chain file path.
        
        Returns:
            CA chain file path or None if not available
        """
        if (self._config and self._config.enabled and self._config.ca_chain_path):
            chain_path = Path(self._config.ca_chain_path)
            if chain_path.exists():
                return str(chain_path)
        return None
    
    def is_pki_enabled(self) -> bool:
        """Check if PKI is enabled and configured."""
        return bool(self._config and self._config.enabled)
    
    def get_certificate_info(self) -> Optional[CertificateInfo]:
        """Get current certificate information."""
        return self._config.certificate_info if self._config else None
    
    def import_ca_chain_file(self, ca_chain_path: str) -> bool:
        """
        Import CA certificate chain file (supports PEM, CRT, CER formats).
        
        Args:
            ca_chain_path: Path to CA chain file
            
        Returns:
            True if successful
        """
        try:
            if not self._config or not self._config.enabled:
                raise PKIError("PKI must be configured before importing CA chain")
            
            logger.info(f"Importing CA chain file: {ca_chain_path}")
            
            # Read CA chain file
            with open(ca_chain_path, 'rb') as f:
                ca_data = f.read()
            
            # Parse and validate the CA chain file
            try:
                chain_pem = self._parse_ca_chain_file(ca_data)

                # Count how many certificates are in the PEM data
                cert_count = chain_pem.count(b'-----BEGIN CERTIFICATE-----')
                logger.info(f"Found {cert_count} certificate(s) in PEM data")

                # Validate certificates individually to identify problematic ones
                certificates = []
                valid_chain_pem = b""

                # Split the PEM data into individual certificates
                cert_blocks = chain_pem.split(b'-----BEGIN CERTIFICATE-----')
                for i, block in enumerate(cert_blocks):
                    if not block.strip():
                        continue

                    # Reconstruct the full PEM certificate
                    cert_pem = b'-----BEGIN CERTIFICATE-----' + block

                    try:
                        # Try to parse this individual certificate
                        cert = x509.load_pem_x509_certificate(cert_pem)
                        certificates.append(cert)
                        valid_chain_pem += cert_pem

                        # Log certificate details
                        subject = cert.subject.rfc4514_string()
                        issuer = cert.issuer.rfc4514_string()
                        logger.info(f"Certificate {len(certificates)}:")
                        logger.info(f"  Subject: {subject}")
                        logger.info(f"  Issuer: {issuer}")

                    except Exception as e:
                        logger.warning(f"Skipping certificate {i} - parsing failed: {e}")
                        continue

                if not certificates:
                    raise PKIError("No valid certificates found in CA chain file")

                logger.info(f"Successfully loaded {len(certificates)} valid certificate(s) from CA chain")

                if len(certificates) != cert_count:
                    logger.warning(f"Certificate count mismatch: found {cert_count} in PEM, but loaded {len(certificates)} valid")

                # Use the validated chain PEM (only valid certificates)
                chain_pem = valid_chain_pem
                # Update cert_count to reflect only valid certificates
                cert_count = len(certificates)

            except Exception as e:
                raise PKIError(f"Failed to parse CA chain file: {e}")

            # Save CA chain to PKI directory
            chain_dest = self.pki_dir / "ca_chain.pem"
            logger.info(f"Writing CA chain to {chain_dest}")
            logger.info(f"Chain PEM size: {len(chain_pem)} bytes")
            logger.info(f"Valid certificates to write: {cert_count}")

            with open(chain_dest, 'wb') as f:
                bytes_written = f.write(chain_pem)
                logger.info(f"Bytes written to file: {bytes_written}")

            # Verify what was actually written
            with open(chain_dest, 'rb') as f:
                written_data = f.read()
                certs_in_file = written_data.count(b'-----BEGIN CERTIFICATE-----')
                logger.info(f"Verification: {certs_in_file} certificate(s) found in written file")
                if certs_in_file != cert_count:
                    logger.error(f"MISMATCH: Expected {cert_count} certs, but file contains {certs_in_file} certs!")
                else:
                    logger.info(f"✓ All {cert_count} valid certificates written successfully")
            
            # Update configuration
            self._config.ca_chain_path = str(chain_dest)
            
            # Save configuration
            if self.save_config():
                logger.info("✓ CA chain imported successfully")
                return True
            else:
                raise PKIError("Failed to save PKI configuration")
                
        except Exception as e:
            logger.error(f"✗ CA chain import failed: {e}")
            return False
    
    def disable_pki(self) -> bool:
        """Disable PKI authentication."""
        try:
            if self._config:
                self._config.enabled = False
                self.save_config()
                logger.info("PKI authentication disabled")
                return True
        except Exception as e:
            logger.error(f"Failed to disable PKI: {e}")
        return False
    
    def _cleanup_certificate_files(self):
        """Clean up certificate files on error."""
        try:
            files_to_remove = ["client.p12", "client.pem", "client.crt", "ca_chain.pem"]
            for filename in files_to_remove:
                file_path = self.pki_dir / filename
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Removed file: {filename}")
        except Exception as e:
            logger.warning(f"Failed to cleanup certificate files: {e}")
    
    def get_pki_status(self) -> Dict[str, Any]:
        """
        Get comprehensive PKI status information.
        
        Returns:
            Dictionary with PKI status details
        """
        status = {
            'enabled': False,
            'configured': False,
            'valid': False,
            'certificate_info': None,
            'last_validation': None,
            'warnings': [],
            'errors': []
        }
        
        if not self._config:
            status['errors'].append("PKI not configured")
            return status
        
        status['enabled'] = self._config.enabled
        status['configured'] = bool(self._config.client_cert_path and self._config.client_key_path)
        status['last_validation'] = self._config.last_validation
        
        if self._config.certificate_info:
            # Handle both CertificateInfo object and dict (for backwards compatibility)
            if isinstance(self._config.certificate_info, dict):
                status['certificate_info'] = self._config.certificate_info
                cert_info = self._config.certificate_info
                days_until_expiry = cert_info.get('days_until_expiry', 999)
                is_valid = cert_info.get('is_valid', False)
            else:
                status['certificate_info'] = self._config.certificate_info.to_dict()
                days_until_expiry = self._config.certificate_info.days_until_expiry
                is_valid = self._config.certificate_info.is_valid

            # Check for warnings
            if days_until_expiry <= 30:
                status['warnings'].append(
                    f"Certificate expires in {days_until_expiry} days"
                )

            if not is_valid:
                status['errors'].append("Certificate is not valid")
            else:
                status['valid'] = True
        
        return status
    
    def shutdown(self):
        """Shutdown certificate manager."""
        try:
            if self._config:
                self.save_config()
            logger.info("Certificate manager shut down")
        except Exception as e:
            logger.warning(f"Error during certificate manager shutdown: {e}")