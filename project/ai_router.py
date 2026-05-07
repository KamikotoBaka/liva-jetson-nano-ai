from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import request as urllib_request


@dataclass
class RouteDecision:
    route: str
    reason: str
    intent_guess: str


class AIRouter:
    def __init__(self, dispatcher, settings_getter) -> None:
        self.dispatcher = dispatcher
        self.settings_getter = settings_getter
        legacy_ollama_url = os.getenv("LIVA_OLLAMA_URL", "").rstrip("/")
        self.llm_url = os.getenv(
            "NON_THINKING_URL",
            os.getenv("NORMAL_URL", os.getenv("LIVA_NON_THINKING_URL", legacy_ollama_url)),
        ).rstrip("/")

    def handle_text(self, text: str) -> dict:
        normalized_text = text.strip()
        if not normalized_text:
            return {
                "sttText": "",
                "commandText": "",
                "ttsText": "Please tell me what you need.",
                "intent": "empty_input",
                "route": "non-thinking",
                "routeReason": "No input provided",
            }

        decision = self._route(normalized_text)
        if decision.route == "non-thinking":
            dispatch_result = self.dispatcher.dispatch(normalized_text)
            return {
                "sttText": normalized_text,
                "commandText": dispatch_result.get("command", ""),
                "ttsText": dispatch_result.get("tts_text", ""),
                "intent": dispatch_result.get("intent", "unknown"),
                "route": decision.route,
                "routeReason": decision.reason,
                "intentGuess": decision.intent_guess,
                "errorEventId": (dispatch_result.get("error_event") or {}).get("id"),
                "errorTimestamp": (dispatch_result.get("error_event") or {}).get("timestamp"),
            }

        answer = self._answer_question(normalized_text)
        return {
            "sttText": normalized_text,
            "commandText": "LLM: answer",
            "ttsText": answer,
            "intent": "chat_response",
            "route": decision.route,
            "routeReason": decision.reason,
            "intentGuess": decision.intent_guess,
            "errorEventId": None,
            "errorTimestamp": None,
        }

    def _route(self, text: str) -> RouteDecision:
        intent, _ = self.dispatcher.resolve_intent(text)
        if intent != "unknown":
            return RouteDecision(
                route="non-thinking",
                reason="Matched deterministic intent routing",
                intent_guess=intent,
            )

        if self._looks_like_question(text):
            return RouteDecision(
                route="non-thinking",
                reason="Detected question-like phrasing",
                intent_guess="chat_response",
            )

        model_route = self._route_with_model(text)
        if model_route is not None:
            return model_route

        return RouteDecision(
            route="non-thinking",
            reason="Unknown command fallback to LLM",
            intent_guess="chat_response",
        )

    def _looks_like_question(self, text: str) -> bool:
        lowered = text.strip().lower()
        if lowered.endswith("?"):
            return True

        prefixes = (
            "what ",
            "why ",
            "how ",
            "when ",
            "where ",
            "who ",
            "which ",
            "explain ",
            "compare ",
            "tell me about ",
        )
        return lowered.startswith(prefixes)

    def _route_with_model(self, text: str) -> RouteDecision | None:
        settings = self.settings_getter()
        if settings.get("responseMode") != "llm":
            return None

        prompt = (
            "You are a strict classifier for a voice assistant. "
            "Classify the user text as either 'command' or 'question'. "
            "Return JSON only with keys route, reason, intent_guess.\n"
            f"Text: {text}"
        )

        raw = self._call_model(
            base_url=self.llm_url,
            prompt=prompt,
            max_tokens=128,
            temperature=0.0,
        )
        if not raw:
            return None

        parsed = self._extract_json(raw)
        if not parsed:
            return None

        route = str(parsed.get("route", "")).strip().lower()
        if route not in {"command", "question"}:
            return None

        return RouteDecision(
            route="non-thinking",
            reason=str(parsed.get("reason", "Model routing decision")).strip() or "Model routing decision",
            intent_guess=str(parsed.get("intent_guess", "unknown")).strip() or "unknown",
        )

    def _answer_question(self, text: str) -> str:
        settings = self.settings_getter()
        if settings.get("responseMode") != "llm":
            return (
                "I can execute commands right now. "
                "Switch response mode to LLM to enable long-form AI answers."
            )

        prompt = (
            "You are LIVA, a concise local assistant. "
            "Answer clearly, avoid unsafe actions, and keep the answer practical.\n"
            f"User: {text}\nAssistant:"
        )
        answer = self._call_model(
            base_url=self.llm_url,
            prompt=prompt,
            max_tokens=512,
            temperature=0.2,
        )
        if not answer:
            return "The LLM is unavailable right now. Please try again in a moment."
        return answer.strip()

    def _call_model(
        self,
        base_url: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        if not base_url:
            return None

        llama_payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        llama_data = self._post_json(f"{base_url}/completion", llama_payload)
        text = self._extract_text_from_response(llama_data)
        return text

    def _post_json(self, url: str, payload: dict) -> dict | None:
        req = urllib_request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=20) as response:
                body = response.read().decode("utf-8", errors="ignore")
        except (urllib_error.URLError, TimeoutError, ValueError):
            return None

        try:
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _extract_text_from_response(self, data: dict | None) -> str | None:
        if not data:
            return None

        response_value = data.get("response")
        if isinstance(response_value, str) and response_value.strip():
            return response_value

        content_value = data.get("content")
        if isinstance(content_value, str) and content_value.strip():
            return content_value

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                text = first.get("text")
                if isinstance(text, str) and text.strip():
                    return text

                message = first.get("message")
                if isinstance(message, dict):
                    message_content = message.get("content")
                    if isinstance(message_content, str) and message_content.strip():
                        return message_content

        return None

    def _extract_json(self, value: str) -> dict | None:
        cleaned = value.strip()
        if not cleaned:
            return None

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None

        snippet = cleaned[start : end + 1]
        try:
            parsed = json.loads(snippet)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
