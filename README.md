# Viega Trio E for Home Assistant

Local-polling Home Assistant integration for the **Viega Multiplex Trio E**
electronic bath filler (via its WLAN module, e.g. model 708870).

No cloud, no account — talks HTTP directly to the module on your LAN.

## Entities

| Entity | What it does |
|---|---|
| `sensor.…_water_temperature` | Live mixed-water temperature |
| `sensor.…_fill_progress` | Progress (%) of a volume-based fill |
| `binary_sensor.…_running` | Water flowing / program active |
| `number.…_target_temperature` | Target temperature for tap & fills |
| `number.…_flow` | Tap flow (%) |
| `switch.…_tap` | Open/close the tap at target temp+flow |
| `valve.…_drain_popup` | Bathtub drain popup |
| `button.…_quick_program` | Run the on-device quick program |
| `button.…_stop` | Stop everything |

## Bundled custom card

The integration ships `custom:trio-e-card` — a bathtub card with manual
controls and three **hold-to-start** fill presets (press ~1 s; the ring fills;
release early to cancel). While water runs, presets swap for a progress
display and a big STOP. The bathtub graphic fills with animated,
temperature-tinted water; `compact: true` gives a graphics-free variant.

The card is served by the integration and auto-registered as a Lovelace
resource on storage-mode setups (YAML mode: add
`/trio_e_files/trio-e-card.js` as a `module` resource manually).

```yaml
type: custom:trio-e-card
name: Bath
compact: false
presets:
  - { name: Sander, temperature: 40, volume: 180 }
  - { name: Quick,  temperature: 41, volume: 215 }
  - { name: Kids,   temperature: 36, volume: 90 }
```

Entity ids are auto-defaulted to this integration's entities and can be
overridden per key under `entities:`. A visual editor is included.

Note: the drain-popup button shows the **last commanded** position — the
device has no position sensor, so a hand-operated plug goes unseen.

## Service

```yaml
service: trio_e.fill_bath
data:
  temperature: 40   # °C
  volume: 180       # litres — the Trio E stops itself
```

Perfect for a "Run my bath" script, voice command, or dashboard button.

## Install

1. HACS → Integrations → ⋮ → *Custom repositories* → add this repo (category: Integration)
2. Install **Viega Trio E**, restart Home Assistant
3. Settings → Devices & Services → *Add Integration* → **Viega Trio E** → enter the module's IP

Give the WLAN module a static IP / DHCP reservation.

## Notes

- The module keeps no persistent temperature setpoint; HA holds the target and
  sends it with each command (same approach as the device's own app).
- Opening the tap first triggers the module's quick-program arm sequence —
  a quirk inherited from [homebridge-trio-e](https://github.com/AxelTerizaki/homebridge-trio-e),
  without which flow commands are ignored.
- Polling is 10 s when idle, 2 s while water is running.

## Credits

API reverse-engineering based on
[AxelTerizaki/homebridge-trio-e](https://github.com/AxelTerizaki/homebridge-trio-e) (MIT).
