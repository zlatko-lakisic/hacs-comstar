# Install & pairing

## Prerequisites

- Home Assistant 2024.6+
- AO engine with `AGENTIC_SERVE_SESSION_OVERLAY=1`
- For tunnels: `AGENTIC_SERVE_MCP_TUNNEL=1`
- For PreferReach speech: `AGENTIC_SPEECH_ENABLED=1` + sidecars
- mTLS enroll uses `openssl` when available, otherwise the Core image’s `cryptography` package
- `npx` on PATH when enabling tunnel MCPs

## Mint token

1. AO Admin → Access → **API tokens**
2. Mint → External client → `appId: comstar-ha`
3. Copy `ao_…` once into the Comstar config flow (or `comstar.set_api_token`)

Do **not** reuse watering’s `home-assistant` token — revoke independently.

## mTLS enroll

1. On AO host: mint enroll token (`python -m orchestration.serve.mtls mint-token …`)
2. Comstar config flow **or** `comstar.pair_ao` with `enroll_token`
3. Confirm `binary_sensor.comstar_ao_paired` is on
4. `comstar.probe` → `binary_sensor.comstar_ao_healthy`

## Clear / re-pair

- `comstar.clear_certs` — deletes local PEMs only; Assist fail-closed until re-enroll
- `comstar.refresh_status` — pushes diagnostic entity updates

## Catalogs

```bash
# Example: list agents
ha service call comstar.catalog_list -d '{"kind":"agent_providers"}'
```

YAML files under `config/comstar/` merge over stock overlay; `comstar.refresh_overlay` or catalog upsert reloads the live Reach session.

## Tunnel MCPs

Enable in Comstar options: Google, Nextcloud, LDAP, vision. Terminal stays **off** by default. Requires credentials via env / `env_from` in MCP YAML.
