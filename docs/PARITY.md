# HACS Comstar ↔ Comstar Pi parity

Living matrix. Pi reference: `comstar` (terminal bridge + overlays). HA product: this repo (`domain: comstar`, Reach `appId: comstar-ha`).

## Include (Reach / overlay / brain)

| Pi feature | HACS Comstar |
|------------|--------------|
| `SessionBridge` | Python `ao_reach.SessionBridge` |
| Overlay register (`client.*`) | Stock + user catalogs → OverlayPacker |
| `directAgent(voice_responder)` | Conversation agent |
| `text_responder` | Assist text / `comstar.direct_agent` |
| HA / Google / NC / LDAP / vision skills | Stock overlay + user catalogs |
| `SpeechClient` PreferReach | `stt` + `tts` platforms |
| `LocalMcpHost` + MCP tunnels | Python host + `mcp_bootstrap` |
| mTLS enroll / clear / probe | `comstar.pair_ao` / `clear_certs` / `probe` |
| Hosted `home_assistant` MCP | AO-side; Assist-expose required |
| Guest policy (no HA MCP) | `identity.py` |
| Working-ack / latency UX | Progress while crew runs |

## Adapt

| Pi feature | HA adaptation |
|------------|---------------|
| Face → userid | HA user / satellite person |
| Attention ladder | Assist conversation lifecycle |
| Wake word | Satellite / pipeline wake |
| Kiosk avatar | Assist TTS playback |
| Telegram channel | HA notify / conversation |
| Announce | `comstar.announce` |
| Admin AO pairing | Config flow + services + diagnostics |
| HaAgentClient bypass | `intents/home_data.py` |

## Defer (hardware-bound)

- Pi HDMI kiosk SVG avatar
- Continuous CPAI ambient camera
- Road VPN / Pi nmcli / hotspot
- Pi full-duplex AEC stack
- systemd bridge/audio/kiosk units

## Catalogs

User create/use under HA `config/comstar/`: `agent_providers`, `mcp_providers`, `agent_skills`, `agent_harnesses`, `harnesses`. Merged over stock `custom_components/comstar/overlays/`.
