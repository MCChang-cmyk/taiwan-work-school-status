"""Exercise HA's actual coordinator, flow schemas, sensors, and lifecycle."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.taiwan_work_school import async_setup_entry, async_unload_entry
from custom_components.taiwan_work_school.config_flow import (
    ConfigFlow,
    OptionsFlow,
    schema,
    validate,
)
from custom_components.taiwan_work_school.const import DEFAULTS, DOMAIN
from custom_components.taiwan_work_school.coordinator import WorkSchoolCoordinator
from custom_components.taiwan_work_school.parser import parse_html
from custom_components.taiwan_work_school.sensor import async_setup_entry as setup_sensors

HTML = (Path(__file__).parent / "fixtures/dgpa_20261022.html").read_text()
NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def settings():
    return {**DEFAULTS, "cities": ["taipei", "taitung"]}


@pytest.fixture
async def hass(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    yield hass
    await hass.async_stop(force=True)


def entry(settings):
    return SimpleNamespace(
        entry_id="test",
        data=settings,
        options={},
        async_on_unload=MagicMock(),
        add_update_listener=MagicMock(),
    )


def response_session(html=HTML):
    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value=html)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get.return_value = context
    return session, response


def test_form_validation(settings):
    assert schema(DEFAULTS)(settings) == settings
    assert not validate(settings)
    assert validate({**settings, "cities": []}) == {"cities": "select_city"}
    assert validate(
        {**settings, "update_mode": "evening", "evening_interval": 5, "evening_count": 5}
    )
    with pytest.raises(vol.Invalid):
        schema(DEFAULTS)({**settings, "update_mode": "unknown"})


async def test_config_and_options_flow(settings):
    flow = ConfigFlow()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value="created")
    assert await flow.async_step_user(settings) == "created"
    assert flow.async_create_entry.call_args.kwargs["data"] == settings
    flow.async_show_form = MagicMock(return_value="form")
    assert await flow.async_step_user({**settings, "cities": []}) == "form"
    assert flow.async_show_form.call_args.kwargs["errors"] == {"cities": "select_city"}
    options = OptionsFlow()
    options.async_create_entry = MagicMock(return_value="options_saved")
    assert await options.async_step_init(settings) == "options_saved"


async def test_fetch_and_errors(hass, settings):
    coordinator = WorkSchoolCoordinator(hass, None, settings)
    session, response = response_session()
    with patch(
        "custom_components.taiwan_work_school.coordinator.async_get_clientsession",
        return_value=session,
    ):
        report = await coordinator._async_update_data()
    assert len(report.announcements) == 22
    assert coordinator.fetched_at is not None
    session.get.assert_called_once()
    response.raise_for_status.assert_called_once()
    for error in (aiohttp.ClientError("offline"), TimeoutError(), UnicodeError()):
        session.get.side_effect = error
        with patch(
            "custom_components.taiwan_work_school.coordinator.async_get_clientsession",
            return_value=session,
        ):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
    session, _ = response_session("<html>error</html>")
    with patch(
        "custom_components.taiwan_work_school.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    await coordinator.async_shutdown()


async def test_sensors_and_midnight(hass, settings):
    coordinator = WorkSchoolCoordinator(hass, None, settings)
    coordinator.async_set_updated_data(parse_html(HTML))
    hass.data[DOMAIN] = {"test": coordinator}
    entities = []
    await setup_sensors(hass, entry(settings), entities.extend)
    assert len(entities) == 6
    assert len({sensor.unique_id for sensor in entities}) == 6
    by_id = {sensor.entity_id: sensor for sensor in entities}
    with patch("custom_components.taiwan_work_school.sensor.dt_util.utcnow", return_value=NOW):
        assert by_id["sensor.taiwan_work_school_taipei_tomorrow"].native_value == "suspended"
        assert by_id["sensor.taiwan_work_school_taitung_tomorrow"].native_value == "partial"
        assert by_id["sensor.taiwan_work_school_taipei_today"].native_value == "unannounced"
    tomorrow = NOW + timedelta(days=1)
    with patch("custom_components.taiwan_work_school.sensor.dt_util.utcnow", return_value=tomorrow):
        assert by_id["sensor.taiwan_work_school_taipei_today"].native_value == "suspended"
        assert by_id["sensor.taiwan_work_school_taipei_tomorrow"].native_value == "unannounced"
        assert (
            by_id["sensor.taiwan_work_school_taipei_today"].extra_state_attributes["target_date"]
            == "2026-10-23"
        )
    coordinator.async_set_update_error(UpdateFailed("offline"))
    assert not entities[0].available
    assert entities[0].extra_state_attributes["announcements"]
    await coordinator.async_shutdown()


async def test_timers_and_unload(hass, settings):
    settings = {**settings, "update_mode": "evening"}
    coordinator = WorkSchoolCoordinator(hass, None, settings)
    cancels = []

    def track(*args):
        cancel = MagicMock()
        cancels.append(cancel)
        return cancel

    with (
        patch("custom_components.taiwan_work_school.coordinator.dt_util.utcnow", return_value=NOW),
        patch(
            "custom_components.taiwan_work_school.coordinator.async_track_point_in_utc_time",
            side_effect=track,
        ),
    ):
        coordinator.start()
        assert coordinator.next_update.isoformat() == "2026-10-22T20:03:00+08:00"
        coordinator.async_refresh = AsyncMock()
        await coordinator._scheduled_update(NOW)
        coordinator.async_refresh.assert_awaited_once()
        coordinator.async_update_listeners = MagicMock()
        coordinator._midnight(NOW)
        coordinator.async_update_listeners.assert_called_once()
    coordinator.stop()
    cancels[-1].assert_called_once()
    cancels[-2].assert_called_once()
    await coordinator.async_shutdown()


async def test_entry_lifecycle(hass, settings):
    config_entry = entry(settings)
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    with (
        patch(
            "custom_components.taiwan_work_school.WorkSchoolCoordinator", return_value=coordinator
        ),
        patch("custom_components.taiwan_work_school.er.async_get") as registry,
        patch(
            "custom_components.taiwan_work_school.er.async_entries_for_config_entry",
            return_value=[
                SimpleNamespace(unique_id="kinmen:today:work", entity_id="sensor.old"),
                SimpleNamespace(unique_id="taipei:today:combined", entity_id="sensor.keep"),
            ],
        ),
    ):
        assert await async_setup_entry(hass, config_entry)
        registry.return_value.async_remove.assert_called_once_with("sensor.old")
        coordinator.start.assert_called_once()
        assert await async_unload_entry(hass, config_entry)
        coordinator.stop.assert_called_once()
        assert "test" not in hass.data[DOMAIN]
    hass.config_entries = None


async def test_full_ha_install_options_reload(hass, settings):
    """Discover the custom integration, save UI forms, and publish real HA states."""
    from homeassistant import config_entries, loader
    from homeassistant.bootstrap import async_load_base_functionality
    from homeassistant.helpers import entity_registry as er

    from custom_components.taiwan_work_school.sensor import StatusSensor

    loader.async_setup(hass)
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await async_load_base_functionality(hass)
    session, _ = response_session()
    with (
        patch(
            "custom_components.taiwan_work_school.coordinator.async_get_clientsession",
            return_value=session,
        ),
        patch.object(
            StatusSensor,
            "target_date",
            new=property(lambda self: date(2026, 10, 22) + timedelta(days=self.offset)),
        ),
    ):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert form["type"] == "form"
        result = await hass.config_entries.flow.async_configure(form["flow_id"], settings)
        assert result["type"] == "create_entry"
        config_entry = result["result"]
        await hass.async_block_till_done()
        assert config_entry.state == config_entries.ConfigEntryState.LOADED
        state = hass.states.get("sensor.taiwan_work_school_taipei_tomorrow")
        assert state is not None
        assert state.state == "suspended"
        assert state.attributes["target_date"] == "2026-10-23"
        assert state.attributes["next_update"] is not None
        assert (
            len(er.async_entries_for_config_entry(er.async_get(hass), config_entry.entry_id)) == 6
        )
        assert state.attributes["work_status"] == "suspended"
        assert state.attributes["school_status"] == "suspended"
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        for phrase, expected in (
            ("明天已達停止上班及上課標準。", "criteria_met"),
            ("明天未達停止上班及上課標準。", "criteria_not_met"),
        ):
            coordinator.async_set_updated_data(
                parse_html(HTML.replace("明天停止上班、停止上課。", phrase))
            )
            await hass.async_block_till_done()
            state = hass.states.get("sensor.taiwan_work_school_taipei_tomorrow")
            assert state.state == expected
            assert state.attributes["work_status"] == expected
            assert state.attributes["school_status"] == expected
        # Previously installed separate sensors are removed on upgrade/reload.
        registry = er.async_get(hass)
        for kind in ("work", "school"):
            registry.async_get_or_create(
                "sensor",
                DOMAIN,
                f"taipei:today:{kind}",
                config_entry=config_entry,
                suggested_object_id=f"old_taipei_{kind}",
            )
        assert await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done()
        registered = er.async_entries_for_config_entry(registry, config_entry.entry_id)
        assert len(registered) == 6
        assert not any(entity.unique_id.endswith((":work", ":school")) for entity in registered)
        # Singleton flows abort, and options run through HA's real options manager.
        duplicate = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert duplicate["reason"] == "already_configured"
        option_form = await hass.config_entries.options.async_init(config_entry.entry_id)
        options_result = await hass.config_entries.options.async_configure(
            option_form["flow_id"], {**settings, "cities": ["taipei"], "update_mode": "evening"}
        )
        assert options_result["type"] == "create_entry"
        await hass.async_block_till_done()
        assert (
            len(er.async_entries_for_config_entry(er.async_get(hass), config_entry.entry_id)) == 3
        )
        assert hass.states.get("sensor.taiwan_work_school_taitung_tomorrow") is None
        assert await hass.config_entries.async_unload(config_entry.entry_id)
