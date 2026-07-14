import json
from urllib import error, request

from django.conf import settings


class AIProviderError(RuntimeError):
    pass


class OpenRouterProvider:
    def __init__(self, api_key, model, endpoint_url, site_url, app_name, timeout):
        self.api_key = api_key
        self.model = model
        self.endpoint_url = endpoint_url
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout

    def generate_json(self, messages):
        missing_settings = []
        if not self.api_key:
            missing_settings.append("OPENROUTER_API_KEY")
        if not self.model:
            missing_settings.append("AI_MODEL")
        if not self.endpoint_url:
            missing_settings.append("OPENROUTER_API_URL")
        if not self.app_name:
            missing_settings.append("AI_APP_NAME")
        if missing_settings:
            raise AIProviderError(
                f"Missing AI provider settings: {', '.join(missing_settings)}"
            )
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        provider_request = request.Request(
            self.endpoint_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.site_url,
                "X-Title": self.app_name,
            },
            method="POST",
        )
        try:
            with request.urlopen(provider_request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise AIProviderError(f"AI provider request failed: {exc}") from exc
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("AI provider returned invalid JSON.") from exc


def get_ai_provider():
    if not settings.AI_PROVIDER:
        raise AIProviderError("Missing AI provider settings: AI_PROVIDER")
    provider = settings.AI_PROVIDER.lower()
    if provider == "openrouter":
        return OpenRouterProvider(
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.AI_MODEL,
            endpoint_url=settings.OPENROUTER_API_URL,
            site_url=settings.AI_SITE_URL,
            app_name=settings.AI_APP_NAME,
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
    raise AIProviderError(f"Unsupported AI provider: {settings.AI_PROVIDER}")
