"""Rewrite a transcript for the model about to read it (spec 2: "rewriting history when
the model changes"). A port of Pi's packages/ai/src/api/transform-messages.ts.

Replay data a provider signs or encrypts is valid only for the model that produced it.
Cross-model, it is dropped; readable reasoning becomes plain text. It runs on the
copy sent to the provider; compaction may later persist that copy, which is harmless
because only the current model's signatures are ever validated.
"""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

# Gemini's thought signatures and its raw function-call echo; OpenAI and OpenRouter reasoning.
_REPLAY_ONLY = ("__gemini_function_call_thought_signatures__", "function_call", "reasoning", "reasoning_content")
# Where langchain-google-genai keeps signatures inside content blocks (_block_signature).
_BLOCK_SIGNATURES = ("signature", "thought_signature", "extras")


def for_model(messages: list[BaseMessage], model_id: str) -> list[BaseMessage]:
    return [
        _rewrite(message) if isinstance(message, AIMessage) and not _same_model(message, model_id) else message
        for message in messages
    ]


def _same_model(message: AIMessage, model_id: str) -> bool:
    # Providers may report a dated snapshot of the requested id ("gpt-5.6-luna-2026-09-01").
    produced = str(message.response_metadata.get("model_name") or "").removeprefix("models/")
    return produced == model_id or produced.startswith(model_id + "-")


def _rewrite(message: AIMessage) -> AIMessage:
    content: Any = message.content
    if isinstance(content, list):
        kept: list[Any] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in ("thinking", "reasoning"):
                text = block.get("thinking") or block.get("reasoning") or block.get("text")
                # Pi: empty or opaque (encrypted) thinking is dropped; readable thinking becomes text.
                if isinstance(text, str) and text.strip():
                    kept.append({"type": "text", "text": text})
                continue
            if isinstance(block, dict):
                block = {key: value for key, value in block.items() if key not in _BLOCK_SIGNATURES}
            kept.append(block)
        content = kept
    kwargs = {key: value for key, value in message.additional_kwargs.items() if key not in _REPLAY_ONLY}
    return message.model_copy(update={"content": content, "additional_kwargs": kwargs})
