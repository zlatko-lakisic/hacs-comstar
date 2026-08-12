# HACS Comstar

Home Assistant Assist frontend for [Agentic Orchestration](https://github.com/zlatko-lakisic/agentic-orchestration) via **AO Reach** — the same framework used by the [Comstar](https://github.com/zlatko-lakisic/comstar) Pi terminal.

## Features

- Reach `SessionBridge` → AO engine `:8765` (overlays, `directAgent`, MCP tunnels, mTLS)
- Assist conversation agent (`client.voice_responder` by default)
- PreferReach **STT/TTS** platforms (`SpeechClient`)
- Operator control plane: **pair / probe / clear_certs / refresh_status**
- User catalogs: create & use **agents, MCPs, skills, harnesses**
- Local intents + house-data bypass; guest policy strips `home_assistant`
- Stock overlay forked from Comstar Pi

## Install

1. HACS → Integrations → Custom repositories → `https://github.com/zlatko-lakisic/hacs-comstar` (Integration)
2. Download **Comstar**, restart Home Assistant
3. Settings → Devices & services → Add **Comstar**
4. Engine URL (example): `https://10.0.10.16:8765`
5. Mint Bearer token in AO Admin → API tokens → External client → `appId: **comstar-ha**`
6. Optional: paste one-time mTLS enroll token

## Assist pipeline

1. Settings → Voice assistants → your pipeline
2. Conversation agent → **Comstar**
3. Optional: Speech-to-text → **Comstar AO STT**; Text-to-speech → **Comstar AO TTS**
4. Expose needed entities to Assist (AO `home_assistant` MCP only sees Assist-exposed entities)

## Services

| Service | Purpose |
|---------|---------|
| `comstar.pair_ao` | mTLS enroll |
| `comstar.clear_certs` | Delete local PEMs (no AO revoke) |
| `comstar.probe` | Health check with client cert |
| `comstar.refresh_status` | Refresh diagnostic entities |
| `comstar.set_api_token` | Rotate minted Bearer |
| `comstar.reset_session` / `refresh_overlay` | Session lifecycle |
| `comstar.announce` | Proactive speak |
| `comstar.direct_agent` | Run any `client.*` agent |
| `comstar.catalog_list/get/upsert/delete/enable` | Catalog CRUD |
| `comstar.run_harness` | Harness pack probe |

User catalogs: `config/comstar/{agent_providers,mcp_providers,agent_skills,agent_harnesses,harnesses}/`

## Docs

- [Parity matrix](docs/PARITY.md)
- [Install & pairing](docs/INSTALL.md)

## License

Apache-2.0
