"""TLS compatibility is isolated and retains server authentication."""

import ssl
from types import SimpleNamespace
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.ssl import get_default_context
from test_runtime import response_session

from custom_components.taiwan_work_school.const import DEFAULTS
from custom_components.taiwan_work_school.coordinator import WorkSchoolCoordinator
from custom_components.taiwan_work_school.tls import dgpa_compatibility_context


def test_context_keeps_verification_and_shared_context():
    shared = get_default_context()
    original_flags = shared.verify_flags
    context = dgpa_compatibility_context()
    assert context is not shared
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT
    assert context.verify_flags == original_flags & ~ssl.VERIFY_X509_STRICT
    assert shared.verify_flags == original_flags
    assert context.get_ca_certs(binary_form=True) == shared.get_ca_certs(binary_form=True)
    assert context.minimum_version == shared.minimum_version


def certificate_error(code, host="www.dgpa.gov.tw"):
    error = ssl.SSLCertVerificationError(1, "certificate verify failed")
    error.verify_code = code
    return aiohttp.ClientConnectorCertificateError(
        SimpleNamespace(host=host, port=443, is_ssl=True), error
    )


@pytest.mark.parametrize(
    "code,host,should_retry",
    [
        (86, "www.dgpa.gov.tw", True),
        (10, "www.dgpa.gov.tw", False),  # Expired certificate
        (20, "www.dgpa.gov.tw", False),  # Unknown issuer
        (62, "www.dgpa.gov.tw", False),  # Hostname mismatch
        (86, "other.example", False),
    ],
)
async def test_certificate_retry_policy(tmp_path, code, host, should_retry):
    hass = HomeAssistant(str(tmp_path))
    coordinator = WorkSchoolCoordinator(hass, None, DEFAULTS)
    session, _ = response_session()
    response_context = session.get.return_value
    session.get.side_effect = [certificate_error(code, host), response_context]
    try:
        with patch(
            "custom_components.taiwan_work_school.coordinator.async_get_clientsession",
            return_value=session,
        ):
            if should_retry:
                report = await coordinator._async_update_data()
                assert len(report.announcements) == 22
                assert session.get.call_count == 2
                kwargs = session.get.call_args.kwargs
                assert isinstance(kwargs["ssl"], ssl.SSLContext)
                assert kwargs["ssl"].check_hostname
                assert kwargs["ssl"].verify_mode == ssl.CERT_REQUIRED
                assert kwargs["allow_redirects"] is False
                session.get.side_effect = None
                await coordinator._async_update_data()
                assert session.get.call_count == 3
            else:
                with pytest.raises(UpdateFailed):
                    await coordinator._async_update_data()
                assert session.get.call_count == 1
                assert coordinator._dgpa_ssl_context is None
    finally:
        await coordinator.async_shutdown()
        await hass.async_stop(force=True)


async def test_retry_still_rejects_invalid_certificate(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    coordinator = WorkSchoolCoordinator(hass, None, DEFAULTS)
    session, _ = response_session()
    session.get.side_effect = [certificate_error(86), certificate_error(10)]
    try:
        with patch(
            "custom_components.taiwan_work_school.coordinator.async_get_clientsession",
            return_value=session,
        ):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
        assert session.get.call_count == 2
    finally:
        await coordinator.async_shutdown()
        await hass.async_stop(force=True)
