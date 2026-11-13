"""Use Windows' native certificate validation for the app's HTTPS requests."""
import ssl
import sys
from urllib.request import urlopen


def open_download(request, *, timeout):
    if sys.platform == 'win32':
        import truststore

        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return urlopen(request, timeout=timeout, context=context)
    return urlopen(request, timeout=timeout)
