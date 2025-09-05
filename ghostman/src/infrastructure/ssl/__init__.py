"""
SSL Infrastructure Module.

Provides unified SSL/TLS certificate verification management.
"""

from .ssl_service import ssl_service, SSLVerificationService, make_ssl_aware_request

__all__ = ['ssl_service', 'SSLVerificationService', 'make_ssl_aware_request']