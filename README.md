# NAD Local Push for Home Assistant

Experimental community integration for the NAD C388 with a network-accessible ASCII control interface (tested on one C388 with BluOS MDC using TCP port 23). Not affiliated with NAD or Home Assistant. Other models and firmware versions are unverified.

## Compatibility

The tested C388 has a BluOS MDC module with BluOS firmware 4.18.26. The module provides the network path to the amplifier control protocol on this setup. This is not the BluOS HTTP API and the native BluOS Home Assistant integration is not required. C388 units without the module, other NAD models and standalone Bluesound players are not verified.

## Features

- Persistent local TCP connection with unsolicited status updates.
- Power, mute, input selection, volume control and dB feedback.
- Configurable input labels and volume range.
- Reconnect with backoff and TCP keepalive.
- No scheduled application-level status polling. Initial sync, reconnect, wake, source confirmation and explicit refreshes use queries.

## Installation

1. Back up your Home Assistant configuration.
2. Copy `custom_components/nad_push` into your Home Assistant configuration directory under `custom_components/`.
3. Merge the example below into the existing `media_player:` list in `configuration.yaml`. Do not replace your whole configuration or create duplicate top-level keys.
4. Replace the example IP address with your amplifier address. Check that TCP port 23 is reachable from Home Assistant. Restart Home Assistant.
5. Find the new media player in Developer tools → States. Test at a low listening level.

```yaml
media_player:
  - platform: nad_push
    host: 192.0.2.10
    port: 23
    name: NAD C388 Direct
    min_volume: -80
    max_volume: -10
    sources:
      1: Optical 1
      2: Optical 2
      3: Source 3
      4: Source 4
      5: Phono
      6: Source 6
      7: Source 7
      8: Bluetooth
      9: BluOS
```

The names above are illustrative, not a guarantee of your hardware mapping. Verify source numbers on your own device and change labels as needed. If omitted, sources default to Source 1 through Source 9. Only listed sources are exposed. `min_volume` and `max_volume` must be within -80 to -10 dB, with minimum less than maximum.

## Operation and limitations

This is an amplifier controller, not a music playback integration. Use your existing Roon, BluOS or other player for artwork and streaming. Those integrations may poll independently.

Percentage-only volume reports do not produce a guessed dB value; the volume slider may be temporarily unavailable. Volume commands require the amplifier to be on and volume step commands require a known dB reading. The slider uses a linear dB mapping and its software maximum only applies to commands sent by this integration. It is not a hardware volume limit. Source feedback depends on the device emitting events; `homeassistant.update_entity` can request an explicit refresh. TCP is unencrypted and unauthenticated; keep it on a trusted local network and never forward the port to the internet.

## Troubleshooting

If configuration checking reports that the integration is not found, verify the folder layout and restart Home Assistant. A configuration-check warning was observed on the original installation even though the integration loaded at runtime; the cause remains unresolved. Verify actual entity state and logs. If the integration is unavailable, check network reachability. On connection loss, the entity should become unavailable and reconnect automatically; reconnection on physical hardware has not been independently verified.

## Status

The original 0.1.0 implementation was tested by its user for control and push updates on one C388. This 0.2.0 experimental preview adds configurable source labels and has not yet been retested in a live Home Assistant instance. No HACS listing or official support is claimed.

Report issues with model, firmware, Home Assistant version, and sanitized logs. Never post credentials, tokens, full configuration files or private network details.

## License

MIT. See [LICENSE](LICENSE).
