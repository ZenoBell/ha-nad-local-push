"""YAML-configured local-push NAD C388 media player."""
import asyncio
from contextlib import suppress
import voluptuous as vol
from homeassistant.components.media_player import MediaPlayerEntity, PLATFORM_SCHEMA
from homeassistant.components.media_player.const import MediaPlayerEntityFeature, MediaPlayerState, MediaPlayerDeviceClass
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from .protocol import NadConnection, QUERIES

SOURCES = {i: f'Source {i}' for i in range(1, 10)}

def validate_sources(value):
    mapping = vol.Schema({vol.All(vol.Coerce(int), vol.Range(min=1, max=9)): vol.All(cv.string, vol.Length(min=1))})(value)
    if not mapping or len(set(mapping.values())) != len(mapping):
        raise vol.Invalid('Provide at least one source with unique names')
    return mapping
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=23): cv.port,
    vol.Optional(CONF_NAME, default='NAD C388 Direct'): cv.string,
    vol.Optional('sources', default=lambda: dict(SOURCES)): validate_sources,
    vol.Optional('min_volume', default=-80): vol.Coerce(float),
    vol.Optional('max_volume', default=-10): vol.Coerce(float),
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if not -80 <= config['min_volume'] < config['max_volume'] <= -10:
        raise HomeAssistantError('NAD volume range must be between -80 and -10 dB')
    async_add_entities([NadPlayer(config)])

class NadPlayer(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF |
        MediaPlayerEntityFeature.SELECT_SOURCE | MediaPlayerEntityFeature.VOLUME_SET |
        MediaPlayerEntityFeature.VOLUME_STEP | MediaPlayerEntityFeature.VOLUME_MUTE)

    def __init__(self, config):
        self.sources = config['sources']
        self._attr_source_list = list(self.sources.values())
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"nad_push_{config[CONF_HOST]}_{config[CONF_PORT]}"
        self.low, self.high = config['min_volume'], config['max_volume']
        self.conn = NadConnection(config[CONF_HOST], config[CONF_PORT], self.changed)
        self.task = None

    def changed(self):
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.task = self.hass.async_create_background_task(self.conn.run(), 'NAD push listener')

    async def async_will_remove_from_hass(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
        await super().async_will_remove_from_hass()

    @property
    def available(self):
        return self.conn.connected and 'power' in self.conn.values

    @property
    def state(self):
        power = self.conn.values.get('power', '').lower()
        return MediaPlayerState.ON if power == 'on' else MediaPlayerState.OFF if power == 'off' else None

    @property
    def source(self):
        return self.sources.get(int(self.conn.values.get('source', '0')))

    @property
    def is_volume_muted(self):
        value = self.conn.values.get('mute', '').lower()
        return value == 'on' if value in ('on', 'off') else None

    @property
    def db(self):
        value = self.conn.values.get('volume', '')
        return float(value) if value and not value.endswith('%') else None

    @property
    def volume_level(self):
        return max(0., min(1., (self.db-self.low)/(self.high-self.low))) if self.db is not None else None

    @property
    def extra_state_attributes(self):
        value = self.conn.values.get('volume', '')
        return {'volume_db': self.db, 'reported_volume_percent': float(value[:-1]) if value.endswith('%') else None,
                'nad_model': self.conn.values.get('model'), 'volume_min_db': self.low, 'volume_max_db': self.high}

    async def command(self, *commands):
        try:
            await self.conn.send(*commands)
        except (OSError, TimeoutError) as exc:
            raise HomeAssistantError(f'NAD command failed: {exc}') from exc

    async def async_update(self):
        await self.command(*QUERIES)

    async def async_turn_on(self):
        await self.command('Main.Power=On')

    async def async_turn_off(self):
        await self.command('Main.Power=Off')

    async def async_select_source(self, source):
        for number, name in self.sources.items():
            if source == name:
                await self.command(f'Main.Source={number}', 'Main.Source?')
                return
        raise HomeAssistantError(f'Unknown NAD source: {source}')

    async def async_mute_volume(self, mute):
        await self.command('Main.Mute=On' if mute else 'Main.Mute=Off')

    async def set_db(self, db):
        if self.state != MediaPlayerState.ON:
            raise HomeAssistantError('Turn on NAD before changing volume')
        db = max(self.low, min(self.high, round(db*2)/2))
        await self.command(f'Main.Volume={db:g}')

    async def async_set_volume_level(self, volume):
        await self.set_db(self.low + max(0., min(1., volume))*(self.high-self.low))

    async def async_volume_up(self):
        if self.db is None:
            await self.command('Main.Volume?')
            raise HomeAssistantError('Volume not yet known; retry after NAD reports dB')
        await self.set_db(self.db+1)

    async def async_volume_down(self):
        if self.db is None:
            await self.command('Main.Volume?')
            raise HomeAssistantError('Volume not yet known; retry after NAD reports dB')
        await self.set_db(self.db-1)
