"""The configured model client. Budget and usage hooks ride on its HTTP transport."""
import os
import httpx
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from ..budget.usage import capture_provider_usage
from ..budget.model_budget import reserve_model_request, settle_model_response
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
    api_key=api_key,
    use_responses_api=True,
    output_version="v0",
    reasoning={"effort": "low"},
    max_tokens=8192,
    timeout=90,
    max_retries=1,
    http_async_client=httpx.AsyncClient(event_hooks={
        'request': [reserve_model_request],
        'response': [capture_provider_usage, settle_model_response],
    }),
)
