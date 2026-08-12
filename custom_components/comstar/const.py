"""HACS Comstar constants."""

DOMAIN = "comstar"
CONF_ENGINE_URL = "engine_url"
CONF_API_TOKEN = "api_token"
CONF_APP_ID = "app_id"
CONF_TTL_SECONDS = "ttl_seconds"
CONF_SPEECH_TOKEN = "speech_token"
CONF_STT_OVERRIDE = "stt_base_url_override"
CONF_TTS_OVERRIDE = "tts_base_url_override"
CONF_DEFAULT_AGENT = "default_agent"
CONF_DEFAULT_MCP_ALLOWLIST = "default_mcp_allowlist"
CONF_ENABLE_GOOGLE = "enable_google_tunnel"
CONF_ENABLE_NEXTCLOUD = "enable_nextcloud_tunnel"
CONF_ENABLE_LDAP = "enable_ldap_tunnel"
CONF_ENABLE_VISION = "enable_vision_tunnel"
CONF_ENABLE_TERMINAL = "enable_terminal_tunnel"
CONF_MATERIAL_DIR = "material_dir"

DEFAULT_APP_ID = "comstar-ha"
DEFAULT_AGENT = "client.voice_responder"
DEFAULT_MCP_ALLOWLIST = ["home_assistant"]
DEFAULT_TTL = 3600

ATTR_PAIRED = "paired"
ATTR_HEALTHY = "healthy"
ATTR_REACH_CONNECTED = "reach_connected"

CATALOG_KINDS = (
    "agent_providers",
    "mcp_providers",
    "agent_skills",
    "agent_harnesses",
    "harnesses",
)

PLATFORMS = ["binary_sensor", "sensor", "conversation", "stt", "tts"]
