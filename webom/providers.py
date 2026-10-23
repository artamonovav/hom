from __future__ import annotations

import json
import logging
import os
import re
import time

import requests

log = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class QuotaExceeded(TranslationError):
    pass


class BaseProvider:
    name = "base"
    max_items = 20
    max_chars = 1800

    def translate(self, texts: list[str], src: str = "ja", tgt: str = "ru") -> list[str]:
        raise NotImplementedError

    def batches(self, texts: list[str]):
        batch: list[str] = []
        chars = 0
        for text in texts:
            if batch and (len(batch) >= self.max_items or chars + len(text) > self.max_chars):
                yield batch
                batch, chars = [], 0
            batch.append(text)
            chars += len(text)
        if batch:
            yield batch


_SENTENCE_SPLIT = re.compile(r"(?<=[。．！？!?])|\n")


def split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for part in _SENTENCE_SPLIT.split(text):
        if not part:
            continue
        if len(current) + len(part) > limit and current:
            chunks.append(current)
            current = part
        else:
            current += part
    if current:
        chunks.append(current)
    out: list[str] = []
    for chunk in chunks:
        while len(chunk) > limit:
            out.append(chunk[:limit])
            chunk = chunk[limit:]
        if chunk:
            out.append(chunk)
    return out


class GoogleWebProvider(BaseProvider):
    """Unofficial Google endpoint used by the Chrome translation extension.

    No API key required. Keeps HTML tags intact. Be polite: ~2 requests/sec.
    """

    name = "google-web"
    max_items = 16
    max_chars = 1600
    endpoint = "https://clients5.google.com/translate_a/t"

    def __init__(self, min_interval: float = 0.4) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
            )
        })
        self.min_interval = min_interval
        self._last = 0.0

    def _wait(self) -> None:
        delay = self.min_interval - (time.monotonic() - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()

    def _request(self, texts: list[str], src: str, tgt: str) -> list[str]:
        params = [("client", "dict-chrome-ex"), ("sl", src), ("tl", tgt)]
        params += [("q", t) for t in texts]
        for attempt in range(6):
            self._wait()
            try:
                resp = self.session.get(self.endpoint, params=params, timeout=40)
            except requests.RequestException as exc:
                log.warning("google-web: %s (попытка %d)", exc, attempt + 1)
                time.sleep(2 * (attempt + 1))
                continue
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise TranslationError(f"google-web: bad JSON: {resp.text[:200]}") from exc
                if isinstance(data, str):
                    data = [data]
                if isinstance(data, list) and len(data) == len(texts):
                    return [str(x) for x in data]
                if isinstance(data, list) and len(texts) == 1 and len(data) == 1:
                    return [str(data[0])]
                raise TranslationError(f"google-web: unexpected reply: {str(data)[:200]}")
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = min(60, 3 * (attempt + 1) ** 2)
                log.warning("google-web: HTTP %d, пауза %ds", resp.status_code, wait)
                time.sleep(wait)
                continue
            if resp.status_code == 400:
                if len(texts) == 1:
                    raise TranslationError("google-web: 400 для одного блока (слишком длинный?)")
                mid = max(1, len(texts) // 2)
                left = self._request(texts[:mid], src, tgt)
                right = self._request(texts[mid:], src, tgt)
                return left + right
            raise TranslationError(f"google-web: HTTP {resp.status_code}: {resp.text[:200]}")
        raise TranslationError("google-web: не удалось получить перевод после повторов")

    def translate(self, texts: list[str], src: str = "ja", tgt: str = "ru") -> list[str]:
        out: list[str] = []
        for batch in self.batches(texts):
            try:
                out.extend(self._request(batch, src, tgt))
            except TranslationError:
                if len(batch) == 1:
                    raise
                for text in batch:
                    out.extend(self._request([text], src, tgt))
        return out


class DeepLProvider(BaseProvider):
    name = "deepl"
    max_items = 50
    max_chars = 80_000

    def __init__(self) -> None:
        self.key = os.environ.get("DEEPL_API_KEY")
        if not self.key:
            raise SystemExit("DEEPL_API_KEY не задан")
        suffix = ":fx" if self.key.endswith(":fx") else ""
        host = "api-free.deepl.com" if suffix else "api.deepl.com"
        self.endpoint = f"https://{host}/v2/translate"
        self.headers = {"Authorization": f"DeepL-Auth-Key {self.key}"}

    def translate(self, texts: list[str], src: str = "ja", tgt: str = "ru") -> list[str]:
        out: list[str] = []
        for batch in self.batches(texts):
            data = [
                ("source_lang", src.upper()),
                ("target_lang", tgt.upper()),
                ("tag_handling", "html"),
                ("preserve_formatting", "1"),
                ("split_sentences", "1"),
            ]
            data += [("text", t) for t in batch]
            resp = None
            for attempt in range(4):
                resp = requests.post(self.endpoint, data=data, headers=self.headers, timeout=60)
                if resp.status_code == 200:
                    break
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    delay = 2 ** attempt
                    log.warning("deepl: HTTP %d, повтор через %d с", resp.status_code, delay)
                    time.sleep(delay)
                    continue
                break
            if resp is None or resp.status_code != 200:
                if resp is not None and (resp.status_code == 456 or
                                         "quota" in resp.text.lower() or
                                         "limit" in resp.text.lower()):
                    raise QuotaExceeded(f"deepl: HTTP {resp.status_code}: {resp.text[:300]}")
                raise TranslationError(f"deepl: HTTP {resp.status_code}: {resp.text[:300]}")
            out.extend(t["text"] for t in resp.json()["translations"])
        return out


class YandexProvider(BaseProvider):
    name = "yandex"
    max_items = 20
    max_chars = 8000

    def __init__(self) -> None:
        self.key = os.environ.get("YANDEX_API_KEY")
        self.folder = os.environ.get("YANDEX_FOLDER_ID")
        if not self.key or not self.folder:
            raise SystemExit("YANDEX_API_KEY / YANDEX_FOLDER_ID не заданы")
        self.endpoint = "https://translate.api.cloud.yandex.net/translate/v2/translate"

    def translate(self, texts: list[str], src: str = "ja", tgt: str = "ru") -> list[str]:
        out: list[str] = []
        for batch in self.batches(texts):
            body = {
                "folderId": self.folder,
                "texts": batch,
                "sourceLanguageCode": src,
                "targetLanguageCode": tgt,
                "format": "HTML",
            }
            resp = requests.post(self.endpoint, json=body, timeout=60,
                                 headers={"Authorization": f"Api-Key {self.key}"})
            if resp.status_code != 200:
                raise TranslationError(f"yandex: HTTP {resp.status_code}: {resp.text[:300]}")
            out.extend(t["text"] for t in resp.json()["translations"])
        return out


class OllamaProvider(BaseProvider):
    name = "ollama"
    max_items = 1
    max_chars = 4000

    def __init__(self) -> None:
        self.model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        self.endpoint = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat"

    def translate(self, texts: list[str], src: str = "ja", tgt: str = "ru") -> list[str]:
        out: list[str] = []
        for text in texts:
            prompt = (
                "Translate the following Japanese text into Russian. "
                "Keep all HTML tags, ids and [[...]] placeholders unchanged. "
                "Return only the translation.\n\n" + text
            )
            body = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0},
            }
            resp = requests.post(self.endpoint, json=body, timeout=600)
            if resp.status_code != 200:
                raise TranslationError(f"ollama: HTTP {resp.status_code}: {resp.text[:300]}")
            out.append(resp.json()["message"]["content"].strip())
        return out


class OpenAIProvider(BaseProvider):
    name = "openai"
    max_items = 1
    max_chars = 4000

    def __init__(self) -> None:
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise SystemExit("OPENAI_API_KEY не задан")
        self.base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def translate(self, texts: list[str], src: str = "ja", tgt: str = "ru") -> list[str]:
        out: list[str] = []
        for text in texts:
            body = {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "Translate Japanese HTML into Russian. "
                                                  "Preserve every HTML tag, id and placeholder exactly."},
                    {"role": "user", "content": text},
                ],
            }
            resp = requests.post(f"{self.base}/chat/completions", json=body, timeout=120,
                                 headers={"Authorization": f"Bearer {self.key}"})
            if resp.status_code != 200:
                raise TranslationError(f"openai: HTTP {resp.status_code}: {resp.text[:300]}")
            out.append(resp.json()["choices"][0]["message"]["content"].strip())
        return out


PROVIDERS = {
    "google-web": GoogleWebProvider,
    "google": GoogleWebProvider,
    "deepl": DeepLProvider,
    "yandex": YandexProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str) -> BaseProvider:
    try:
        cls = PROVIDERS[name]
    except KeyError:
        raise SystemExit(f"Неизвестный провайдер {name!r}. Доступны: {', '.join(PROVIDERS)}")
    return cls()
