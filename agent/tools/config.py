"""Connected-service settings: the platform's own keys for servers that work without one."""

from config import BaseConfig


class ToolsConfig(BaseConfig):
    # Optional. Sent to that server while the user has saved no key of their own, for its higher rate limit:
    # every build calls from our one address, so the anonymous limit is shared by every user.
    CONTEXT7_API_KEY: str = ""
    HF_TOKEN: str = ""


tools_settings = ToolsConfig()
