"""
BloomCraft AI - free-tier LLM client
====================================

One tiny client for every OpenAI-compatible free tier. Nothing about models is hard-coded:

* Providers (Groq, OpenRouter, Cerebras, Mistral) are only *endpoints*.
* The model list is DISCOVERED AT RUNTIME from each provider's /models endpoint
  (OpenRouter: only models whose price is 0), filtered to chat models and ranked by
  size / capability hints, then cached for a few hours.
* If a model is retired, rate-limited or slow it is "benched" for a while and the next
  model - then the next provider - is used automatically.

Keys come from the Settings screen (api_config) or environment variables:

    GROQ_API_KEY        https://console.groq.com/keys          (free tier, no card)
    OPENROUTER_API_KEY  https://openrouter.ai/keys              (":free" models)
    CEREBRAS_API_KEY    https://cloud.cerebras.ai               (free tier)
    MISTRAL_API_KEY     https://console.mistral.ai              (free "Experiment" plan)

Optional env: BLOOMCRAFT_LLM_ORDER="mistral,cerebras,groq,openrouter"  (default order)
              BLOOMCRAFT_<PROVIDER>_MODEL="exact-model-id"   (pins a model; tried first)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("bloomcraft.llm")


def _load_env_files() -> None:
    """Tiny .env loader (no dependency). Real environment variables always win."""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "..", ".env"), os.path.join(here, "..", "..", ".env")):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    if v:
                        os.environ.setdefault(k.strip(), v)
        except OSError:
            continue


_load_env_files()

PROVIDERS: List[Dict[str, Any]] = [
    # Default fallback order (override with BLOOMCRAFT_LLM_ORDER). Providers without a key are skipped.
    {"name": "mistral", "base": "https://api.mistral.ai/v1", "cfg_key": "mistral_key", "env": ["MISTRAL_API_KEY"]},
    {"name": "cerebras", "base": "https://api.cerebras.ai/v1", "cfg_key": "cerebras_key", "env": ["CEREBRAS_API_KEY"]},
    {"name": "groq", "base": "https://api.groq.com/openai/v1", "cfg_key": "groq_key", "env": ["GROQ_API_KEY"]},
    {"name": "openrouter", "base": "https://openrouter.ai/api/v1", "cfg_key": "openrouter_key",
     "env": ["OPENROUTER_API_KEY"], "free_only": True},
]
_BY_NAME = {p["name"]: p for p in PROVIDERS}

MODEL_CACHE_TTL = 6 * 3600
_UA = "BloomCraft-AI/1.0 (+question-paper-generator)"

_model_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_bench: Dict[Tuple[str, str], float] = {}      # (provider, model-or-"*") -> benched until
last_used: Dict[str, str] = {}
last_errors: List[str] = []                    # failures of the most recent complete() call (for logs / UI)

# Some free tiers (Mistral "Experiment") enforce ONE shared limit per key (about 1 request/second),
# NOT one bucket per model - so trying the next model after a 429 only burns more requests.
PROVIDER_WIDE_LIMIT = {"mistral"}
MIN_INTERVAL = {"mistral": 1.3}                # seconds between requests to the same provider
_throttle_lock = threading.Lock()
_next_slot: Dict[str, float] = {}


def _throttle(provider: str) -> None:
    """Space requests out per provider (thread-safe) so parallel figure/question calls don't trip 429s."""
    gap = MIN_INTERVAL.get(provider)
    if not gap:
        return
    with _throttle_lock:
        now = time.time()
        slot = max(now, _next_slot.get(provider, 0.0))
        _next_slot[provider] = slot + gap
    if slot > now:
        time.sleep(slot - now)


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

def _key_for(p: Dict[str, Any], api_config: Optional[Dict[str, Any]]) -> Optional[str]:
    key = (api_config or {}).get(p["cfg_key"])
    if key:
        return str(key).strip() or None
    for env in p["env"]:
        if os.environ.get(env):
            return os.environ[env].strip()
    return None


def configured_providers(api_config: Optional[Dict[str, Any]] = None) -> List[Tuple[Dict[str, Any], str]]:
    """Providers that have a key, in fallback order."""
    order_raw = (api_config or {}).get("provider_order") or os.environ.get("BLOOMCRAFT_LLM_ORDER") or ""
    names = [n.strip().lower() for n in str(order_raw).split(",") if n.strip()]
    ordered = [_BY_NAME[n] for n in names if n in _BY_NAME] + [p for p in PROVIDERS if p["name"] not in names]
    out = []
    for p in ordered:
        key = _key_for(p, api_config)
        if key:
            out.append((p, key))
    return out


def is_available(api_config: Optional[Dict[str, Any]] = None) -> bool:
    return bool(configured_providers(api_config))


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class _HTTPFail(Exception):
    def __init__(self, code: int, body: str, retry_after: Optional[float] = None) -> None:
        super().__init__(f"HTTP {code}: {body[:200]}")
        self.code, self.body, self.retry_after = code, body, retry_after


def _request(method: str, url: str, key: str, payload: Optional[Dict[str, Any]], timeout: float,
             provider: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Accept": "application/json", "User-Agent": _UA}
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://localhost"
        headers["X-Title"] = "BloomCraft AI"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        ra = None
        try:
            ra = float(e.headers.get("Retry-After")) if e.headers.get("Retry-After") else None
        except Exception:
            ra = None
        raise _HTTPFail(e.code, body, ra)


# ---------------------------------------------------------------------------
# Runtime model discovery + ranking (no model ids are hard-coded)
# ---------------------------------------------------------------------------

_NON_CHAT = re.compile(
    r"whisper|tts|orpheus|guard|safeguard|embed|moderation|rerank|image|speech|transcri|ocr|audio|"
    r"dall|sora|veo|lyria|vision-preview|playai|compound|router|voxtral|^openrouter/", re.I)


def _param_size_b(model_id: str) -> float:
    s = model_id.lower().replace("-", " ").replace("_", " ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", s)
    return float(m.group(1)) if m else 0.0


def _score(model_id: str, meta: Dict[str, Any]) -> float:
    low = model_id.lower()
    s = min(_param_size_b(model_id), 200.0)
    if "large" in low:
        s += 90
    elif "medium" in low:
        s += 45
    elif "small" in low:
        s += 20
    if re.search(r"instruct|versatile|chat|gpt-oss", low):
        s += 10
    if re.search(r"preview|beta|exp\b|experimental", low):
        s -= 15
    if re.search(r"coder|code\b|codestral|devstral", low):
        s -= 20
    if re.search(r"reason|think|r1\b|qwq|qwen3|gpt-oss|magistral", low):
        s -= 60                       # hidden reasoning = slow, eats the token budget and the free-tier rate limit
    ctx = meta.get("context_length") or meta.get("context_window") or 0
    if ctx and ctx < 16000:
        s -= 30
    return s


def _discover(p: Dict[str, Any], key: str, timeout: float = 15.0, force: bool = False) -> List[Dict[str, Any]]:
    cached = _model_cache.get(p["name"])
    if cached and not force and time.time() - cached[0] < MODEL_CACHE_TTL:
        return cached[1]
    try:
        data = _request("GET", f"{p['base']}/models", key, None, timeout, p["name"])
    except Exception as exc:
        log.warning("Model discovery failed for %s: %s", p["name"], exc)
        return cached[1] if cached else []
    models: List[Dict[str, Any]] = []
    for m in data.get("data", []) or []:
        mid = m.get("id")
        if not mid or _NON_CHAT.search(mid):
            continue
        if m.get("active") is False:
            continue
        if p.get("free_only"):
            pr = m.get("pricing") or {}
            if not (str(pr.get("prompt")) == "0" and str(pr.get("completion")) == "0"):
                continue
            outs = (m.get("architecture") or {}).get("output_modalities")
            if outs and "text" not in outs:
                continue
            ins = (m.get("architecture") or {}).get("input_modalities")
            if ins and "text" not in ins:
                continue
        models.append({"id": mid, "score": _score(mid, m), "meta": m})
    models.sort(key=lambda x: x["score"], reverse=True)
    _model_cache[p["name"]] = (time.time(), models)
    return models


def _pinned(p: Dict[str, Any], api_config: Optional[Dict[str, Any]]) -> Optional[str]:
    pinned = ((api_config or {}).get("models") or {}).get(p["name"]) if isinstance((api_config or {}).get("models"), dict) else None
    return pinned or os.environ.get(f"BLOOMCRAFT_{p['name'].upper()}_MODEL")


def _bench_remaining(provider: str, model: str) -> float:
    now = time.time()
    return max(_bench.get((provider, "*"), 0) - now, _bench.get((provider, model), 0) - now, 0.0)


def _benched(provider: str, model: str) -> bool:
    return _bench_remaining(provider, model) > 0


def _tiny_cap(body: str) -> bool:
    """True when a 429 says the model's tokens-per-minute cap itself is too small (e.g. 'Limit 1000')."""
    m = re.search(r"tokens per minute[^.]*?Limit (\d+)", body or "", re.I)
    return bool(m and int(m.group(1)) < 2500)


def _parse_wait(e: "_HTTPFail") -> Optional[float]:
    """Seconds to wait after a 429: Retry-After header, or 'try again in 7.5s / 1m3s / 250ms' in the body."""
    if e.retry_after:
        return e.retry_after
    m = re.search(r"try again in\s+([0-9hms.]+)", e.body or "", re.I)
    if not m:
        return None
    total, found = 0.0, False
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", m.group(1)):
        found = True
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total if found else None


def _bench_for(provider: str, model: str, seconds: float) -> None:
    _bench[(provider, model)] = time.time() + seconds


# ---------------------------------------------------------------------------
# Completion with fallback
# ---------------------------------------------------------------------------

_THINK = re.compile(r"<think>[\s\S]*?</think>", re.I)


_OPTIONAL_PARAMS = ("response_format", "reasoning_effort", "reasoning")


def _chat_once(p: Dict[str, Any], key: str, model: str, system: str, user: str, json_mode: bool,
               temperature: float, max_tokens: int, timeout: float) -> str:
    reasoning_model = bool(re.search(r"gpt-oss|magistral|qwen3|r1\b|think", model, re.I))
    payload: Dict[str, Any] = {
        "model": model, "temperature": temperature,
        "max_tokens": max_tokens + (1500 if reasoning_model else 0),     # hidden reasoning also uses tokens
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if re.search(r"gpt-oss", model, re.I):                               # keep reasoning short: faster, fewer tokens
        if p["name"] == "openrouter":
            payload["reasoning"] = {"effort": "low"}
        else:
            payload["reasoning_effort"] = "low"
    _throttle(p["name"])
    try:
        data = _request("POST", f"{p['base']}/chat/completions", key, payload, timeout, p["name"])
    except _HTTPFail as e:
        if e.code in (400, 422) and any(k in payload for k in _OPTIONAL_PARAMS):
            for k in _OPTIONAL_PARAMS:                                   # model lacks JSON mode / reasoning params
                payload.pop(k, None)
            _throttle(p["name"])
            data = _request("POST", f"{p['base']}/chat/completions", key, payload, timeout, p["name"])
        else:
            raise
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    text = msg.get("content") or ""
    text = _THINK.sub("", text).strip()
    if not text:
        raise _HTTPFail(502, "empty completion")
    return text


def complete(
    system: str,
    user: str,
    json_mode: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    api_config: Optional[Dict[str, Any]] = None,
    validate: Optional[Callable[[str], bool]] = None,
    models_per_provider: int = 4,
    timeout: float = 40.0,
    total_budget: float = 90.0,
) -> Optional[Tuple[str, str]]:
    """
    Returns (text, "provider:model") or None when every provider/model failed.

    * Models are tried best-first; each model has its own rate-limit bucket, so a 429 on one model
      simply moves on to the next model, then the next provider.
    * If everything is rate limited, we wait for the soonest bucket to reset (<= 30 s) and try again.
    * `validate(text)` lets the caller reject unusable output (e.g. broken JSON) so the next model is tried.
    """
    started = time.time()
    last_errors.clear()
    providers = configured_providers(api_config)
    if not providers:
        return None

    for _round in range(3):
        soonest: Optional[float] = None

        def note_wait(sec: float) -> None:
            nonlocal soonest
            soonest = sec if soonest is None else min(soonest, sec)

        for p, key in providers:
            if time.time() - started > total_budget:
                break
            prov_rem = _bench.get((p["name"], "*"), 0) - time.time()
            if prov_rem > 0:
                note_wait(prov_rem)
                continue
            candidates: List[str] = []
            pin = _pinned(p, api_config)
            if pin:
                candidates.append(pin)
            candidates += [m["id"] for m in _discover(p, key) if m["id"] != pin]
            tried = 0
            for model in candidates:
                if tried >= models_per_provider or time.time() - started > total_budget:
                    break
                rem = _bench_remaining(p["name"], model)
                if rem > 0:
                    note_wait(rem)
                    continue
                tried += 1
                try:
                    text = _chat_once(p, key, model, system, user, json_mode, temperature, max_tokens, timeout)
                except _HTTPFail as e:
                    last_errors.append(f"{p['name']}/{model}: HTTP {e.code} {e.body[:120].strip()}")
                    log.warning("%s/%s failed: HTTP %s %s", p["name"], model, e.code, e.body[:160].strip())
                    if e.code in (401, 403):
                        _bench_for(p["name"], "*", 600)        # bad key / blocked: skip provider for a while
                        break
                    if e.code in (400, 404, 410, 422):
                        _bench_for(p["name"], model, 3600)     # retired / unsupported model
                    elif e.code == 429 and p["name"] in PROVIDER_WIDE_LIMIT:
                        wait = min(max(_parse_wait(e) or 8.0, 2.0), 60.0)
                        _bench_for(p["name"], "*", wait)       # whole key is limited: skip provider, go to next one
                        note_wait(wait)
                        break
                    elif e.code == 429 and _tiny_cap(e.body):
                        _bench_for(p["name"], model, 3600)     # per-minute cap too small for any diagram
                    elif e.code == 429:
                        wait = min(max(_parse_wait(e) or 20.0, 2.0), 120.0)
                        _bench_for(p["name"], model, wait)
                        note_wait(wait)
                    else:
                        _bench_for(p["name"], model, 60)
                    continue
                except Exception as exc:                       # timeout, DNS, SSL ...
                    last_errors.append(f"{p['name']}/{model}: {exc}")
                    log.warning("%s/%s error: %s", p["name"], model, exc)
                    _bench_for(p["name"], model, 60)
                    continue
                if validate is not None and not validate(text):
                    last_errors.append(f"{p['name']}/{model}: unusable output")
                    log.warning("%s/%s returned unusable output", p["name"], model)
                    continue
                tag = f"{p['name']}:{model}"
                last_used["last"] = tag
                return text, tag

        # nothing worked this round: if a rate-limit bucket resets soon, wait for it and go again
        if soonest is None or soonest > 30 or (time.time() - started) + soonest > total_budget:
            break
        log.info("All models rate-limited; waiting %.1fs for the next bucket", soonest)
        time.sleep(soonest + 0.5)
    return None


def status(api_config: Optional[Dict[str, Any]] = None, refresh: bool = False) -> Dict[str, Any]:
    """Diagnostics for the UI: which providers have keys and which models would be tried."""
    out: Dict[str, Any] = {"providers": [], "last_used": last_used.get("last")}
    for p, key in configured_providers(api_config):
        models = _discover(p, key, force=refresh)
        out["providers"].append({
            "name": p["name"],
            "benched": _benched(p["name"], "*"),
            "pinned": _pinned(p, api_config),
            "top_models": [m["id"] for m in models[:4]],
            "discovered": len(models),
        })
    out["configured"] = len(out["providers"])
    return out
