"""Tests for the Tempest (WeatherFlow Cloud) sensor platform."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion
from weatherflow4py.models.rest.observation import ObservationStationREST

from homeassistant.components.tempest.const import DOMAIN
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    load_fixture,
    snapshot_platform,
)


async def test_all_cloud_sensors(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    mock_api,
    mock_get_stations,
) -> None:
    """Verify every cloud sensor is registered and matches the snapshot."""
    # Only load the sensor platform
    with patch("homeassistant.components.tempest.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_lightning_last_epoch_clears_on_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    mock_api,
    mock_get_stations,
    freezer: FrozenDateTimeFactory,
) -> None:
    """If the REST observation payload signals an error, the last‐strike goes to UNKNOWN."""
    # Prepare our “error” fixture
    error_obs = ObservationStationREST.from_json(
        load_fixture("station_observation_error.json", DOMAIN)
    )

    with patch("homeassistant.components.tempest.PLATFORMS", [Platform.SENSOR]):
        # Initial integration load
        await setup_integration(hass, mock_config_entry)

        # Confirm the good timestamp from station_observation.json
        state = hass.states.get("sensor.my_home_station_lightning_last_strike")
        assert state is not None
        assert state.state == "2024-02-07T23:01:15+00:00"

        # Now swap in the “error” observation
        all_data = await mock_api.get_all_data()
        all_data[24432].observation = error_obs
        mock_api.get_all_data.return_value = all_data

        # Move the clock forward so the coordinator refreshes
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        # The last‐strike sensor should now read UNKNOWN
        state = hass.states.get("sensor.my_home_station_lightning_last_strike")
        assert state is not None
        assert state.state == STATE_UNKNOWN
