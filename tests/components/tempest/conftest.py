"""Common fixtures for the Tempest (WeatherFlow Cloud) integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientResponseError
import pytest
from weatherflow4py.models.rest.forecast import WeatherDataForecastREST
from weatherflow4py.models.rest.observation import ObservationStationREST
from weatherflow4py.models.rest.stations import StationsResponseREST
from weatherflow4py.models.rest.unified import WeatherFlowDataREST

from homeassistant.components.tempest.const import DOMAIN

from tests.common import MockConfigEntry, load_fixture

MOCK_API_TOKEN = "1234567890"


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Prevent the config flow from actually running—but still forward to the sensor platform."""
    with patch(
        "homeassistant.components.tempest.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_get_stations() -> Generator[AsyncMock]:
    """Stub out the station‐list fetch so it always succeeds once."""
    with patch(
        "weatherflow4py.api.WeatherFlowRestAPI.async_get_stations",
        side_effect=[True],
    ) as mock_get:
        yield mock_get


@pytest.fixture
def mock_get_stations_500_error() -> Generator[AsyncMock]:
    """First a 500, then success."""
    with patch(
        "weatherflow4py.api.WeatherFlowRestAPI.async_get_stations",
        side_effect=[ClientResponseError(Mock(), (), status=500), True],
    ) as mock_get:
        yield mock_get


@pytest.fixture
def mock_get_stations_401_error() -> Generator[AsyncMock]:
    """First a 401, then keep succeeding."""
    with patch(
        "weatherflow4py.api.WeatherFlowRestAPI.async_get_stations",
        side_effect=[ClientResponseError(Mock(), (), status=401), True, True, True],
    ) as mock_get:
        yield mock_get


@pytest.fixture
async def mock_config_entry() -> MockConfigEntry:
    """Create a ConfigEntry whose .data['token'] is a dict, not a bare string."""
    token_data = {
        "access_token": MOCK_API_TOKEN,
        "refresh_token": "dummy_refresh",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    return MockConfigEntry(
        domain=DOMAIN,
        data={"token": token_data},
        version=1,
    )


@pytest.fixture
def mock_api():
    """Patch out the real WeatherFlowRestAPI and return a stable mock for get_all_data()."""
    # Load the standard fixtures
    stations = StationsResponseREST.from_json(load_fixture("stations.json", DOMAIN))
    forecast = WeatherDataForecastREST.from_json(load_fixture("forecast.json", DOMAIN))
    observation = ObservationStationREST.from_json(
        load_fixture("station_observation.json", DOMAIN)
    )

    # Our integration always uses station 24432 in these fixtures
    data = {
        24432: WeatherFlowDataREST(
            weather=forecast,
            observation=observation,
            station=stations.stations[0],
            device_observations=None,
        )
    }

    with patch(
        "homeassistant.components.tempest.coordinator.WeatherFlowRestAPI",
        autospec=True,
    ) as mock_api_cls:
        mock_api = AsyncMock()
        mock_api.get_all_data.return_value = data
        mock_api_cls.return_value = mock_api
        yield mock_api
