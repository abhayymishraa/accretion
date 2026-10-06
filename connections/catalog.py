"""The servers the Connections page offers, checked by hand: each is a remote Streamable HTTP server whose sign-in
was confirmed (none, a key, or OAuth with dynamic client registration). Users can also add any https URL.

Curated rather than read live from the MCP Registry, which is in preview and asks hosts to mirror and filter it.
"""

from typing import TypedDict

from agent.tools import mcp


class Entry(TypedDict):
    id: str
    title: str
    description: str
    url: str
    auth: mcp.Auth
    # Header servers: the header the key goes in, and where to get one.
    header_name: str | None
    key_hint: str | None
    # Every tool only reads, though the server does not mark them so: shown as reading, not changing.
    read_only: bool
    # Who makes the server, and its own page about it: the service page's Details.
    maker: str
    docs_url: str


def _entry(
    id: str,
    title: str,
    description: str,
    url: str,
    auth: mcp.Auth,
    *,
    maker: str,
    docs_url: str,
    header_name: str | None = None,
    key_hint: str | None = None,
    read_only: bool = False,
) -> Entry:
    return Entry(
        id=id,
        title=title,
        description=description,
        url=url,
        auth=auth,
        header_name=header_name,
        key_hint=key_hint,
        read_only=read_only,
        maker=maker,
        docs_url=docs_url,
    )


# The services Bolt's Connectors page lists come first, in its order; ours follow.
CATALOG: list[Entry] = [
    _entry(
        "notion",
        "Notion",
        "Read and edit pages and databases in your Notion workspace.",
        "https://mcp.notion.com/mcp",
        "oauth",
        maker="Notion",
        docs_url="https://developers.notion.com/guides/mcp/mcp",
    ),
    _entry(
        "linear",
        "Linear",
        "Read and manage issues, projects and teams in Linear.",
        "https://mcp.linear.app/mcp",
        "oauth",
        maker="Linear",
        docs_url="https://linear.app/docs/mcp",
    ),
    _entry(
        "miro",
        "Miro",
        "Read and edit boards, sticky notes and diagrams in Miro.",
        "https://mcp.miro.com/",
        "oauth",
        maker="Miro",
        docs_url="https://miro.com/ai/mcp",
    ),
    _entry(
        "context7",
        "Context7",
        "Up-to-date documentation and code examples for libraries and frameworks.",
        "https://mcp.context7.com/mcp",
        "none",
        maker="Context7",
        docs_url="https://context7.com",
        header_name="Context7-API-Key",
        key_hint="context7.com, Dashboard. The key is optional and gives you a higher rate limit.",
    ),
    _entry(
        "github",
        "GitHub",
        "Read and manage repositories, issues and pull requests.",
        "https://api.githubcopilot.com/mcp/",
        "header",
        maker="GitHub",
        docs_url="https://github.com/github/github-mcp-server",
        header_name="Authorization",
        key_hint="GitHub Settings, Developer settings: a fine-grained personal access token with read access to the "
        "repositories you want. Add write access only for issues and pull requests.",
    ),
    _entry(
        "sentry",
        "Sentry",
        "Look up errors, issues and performance data in Sentry.",
        "https://mcp.sentry.dev/mcp",
        "oauth",
        maker="Sentry",
        docs_url="https://docs.sentry.io/product/sentry-mcp",
    ),
    _entry(
        "granola",
        "Granola",
        "Read your meeting notes and transcripts from Granola.",
        "https://mcp.granola.ai/mcp",
        "oauth",
        maker="Granola",
        docs_url="https://docs.granola.ai/help-center/sharing/integrations/mcp",
    ),
    _entry(
        "shaders",
        "Shaders",
        "Add shader effects you design in Shaders to your app. Some presets need Shaders Pro.",
        "https://shaders.com/mcp",
        "oauth",
        maker="Shaders",
        docs_url="https://shaders.com/docs/guide/mcp",
    ),
    _entry(
        "jira",
        "Jira",
        "Read and manage Jira issues and projects.",
        "https://mcp.atlassian.com/v2/mcp",
        "oauth",
        maker="Atlassian",
        docs_url="https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server",
    ),
    _entry(
        "deepwiki",
        "DeepWiki",
        "Answers questions about public GitHub repositories from their generated wikis.",
        "https://mcp.deepwiki.com/mcp",
        "none",
        maker="Cognition",
        docs_url="https://docs.devin.ai/work-with-devin/deepwiki-mcp",
        read_only=True,
    ),
    _entry(
        "huggingface",
        "Hugging Face",
        "Search models, datasets, Spaces and papers on Hugging Face.",
        "https://huggingface.co/mcp",
        "none",
        maker="Hugging Face",
        docs_url="https://huggingface.co/settings/mcp",
        header_name="Authorization",
        key_hint="Hugging Face Settings, Access Tokens (read access). The token is optional and gives you a higher "
        "rate limit.",
    ),
    _entry(
        "cloudflare-docs",
        "Cloudflare Docs",
        "Search Cloudflare's developer documentation.",
        "https://docs.mcp.cloudflare.com/mcp",
        "none",
        maker="Cloudflare",
        docs_url="https://developers.cloudflare.com/agents/model-context-protocol/mcp-servers-for-cloudflare/",
    ),
    _entry(
        "stripe",
        "Stripe",
        "Work with Stripe products, prices, customers and payments.",
        "https://mcp.stripe.com",
        "oauth",
        maker="Stripe",
        docs_url="https://docs.stripe.com/mcp",
    ),
    _entry(
        "supabase",
        "Supabase",
        "Manage Supabase projects, databases and edge functions.",
        "https://mcp.supabase.com/mcp",
        "oauth",
        maker="Supabase",
        docs_url="https://supabase.com/docs/guides/getting-started/mcp",
    ),
    _entry(
        "neon",
        "Neon",
        "Manage Neon Postgres projects, branches and databases.",
        "https://mcp.neon.tech/mcp",
        "oauth",
        maker="Neon",
        docs_url="https://neon.com/docs/ai/neon-mcp-server",
    ),
    _entry(
        "vercel",
        "Vercel",
        "Look up Vercel projects, deployments and logs.",
        "https://mcp.vercel.com",
        "oauth",
        maker="Vercel",
        docs_url="https://vercel.com/docs/mcp/vercel-mcp",
    ),
]

BY_ID = {entry["id"]: entry for entry in CATALOG}
