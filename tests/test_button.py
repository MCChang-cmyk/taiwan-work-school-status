"""The manual refresh control updates shared data and permits recovery."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.taiwan_work_school.button import RefreshButton


async def test_press_refreshes_all_counties():
    coordinator = SimpleNamespace(
        async_request_refresh=AsyncMock(), last_update_success=True, last_exception=None
    )
    button = RefreshButton(coordinator)
    assert button.available
    await button.async_press()
    coordinator.async_request_refresh.assert_awaited_once()


async def test_failed_fetch_is_reported_and_button_can_retry():
    coordinator = SimpleNamespace(
        async_request_refresh=AsyncMock(),
        last_update_success=False,
        last_exception=RuntimeError("offline"),
    )
    button = RefreshButton(coordinator)
    assert button.available
    with pytest.raises(HomeAssistantError, match="無法更新"):
        await button.async_press()
    assert button.available

    async def recover():
        coordinator.last_update_success = True
        coordinator.last_exception = None

    coordinator.async_request_refresh.side_effect = recover
    await button.async_press()
    assert coordinator.async_request_refresh.await_count == 2
