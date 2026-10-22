"""Isolated compatibility context for DGPA's legacy certificate chain."""

import ssl

from homeassistant.util.ssl import get_default_context


def dgpa_compatibility_context() -> ssl.SSLContext:
    """Keep HA's CA trust, hostname verification and TLS defaults.

    Called in the executor because loading certificates performs blocking work.
    Never mutate Home Assistant's shared SSL context.
    """
    shared = get_default_context()
    certificates = "".join(
        ssl.DER_cert_to_PEM_cert(cert) for cert in shared.get_ca_certs(binary_form=True)
    )
    context = ssl.create_default_context(cadata=certificates)
    context.verify_flags = shared.verify_flags & ~ssl.VERIFY_X509_STRICT
    context.minimum_version = shared.minimum_version
    context.maximum_version = shared.maximum_version
    return context
