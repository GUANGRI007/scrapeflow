"""Config loading and validation.

A config is a YAML file. This module turns it into typed objects and fails
loudly on anything malformed, so the scraper itself never has to guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a config file is missing keys or has the wrong shape."""


@dataclass(frozen=True)
class Field:
    """One output column."""

    name: str
    selector: str
    attr: str | None = None
    regex: re.Pattern[str] | None = None
    default: str = ""
    required: bool = False


@dataclass(frozen=True)
class Pagination:
    selector: str
    attr: str = "href"
    max_pages: int = 10


@dataclass(frozen=True)
class RequestSettings:
    delay: float = 0.5
    timeout: float = 20.0
    retries: int = 3
    user_agent: str = "ScrapeFlow/1.0"


@dataclass(frozen=True)
class Config:
    name: str
    start_urls: list[str]
    row_selector: str
    fields: list[Field]
    pagination: Pagination | None = None
    request: RequestSettings = field(default_factory=RequestSettings)

def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise ConfigError(f"{where}: missing required key {key!r}")
    return data[key]

def _parse_field(name: str, spec: Any) -> Field:
    where = f"fields.{name}"

    # Shorthand: `title: "h3 a"` means just a selector.
    if isinstance(spec, str):
        return Field(name=name, selector=spec)

    if not isinstance(spec, dict):
        raise ConfigError(f"{where}: expected a string or a mapping, got {type(spec).__name__}")

    selector = _require(spec, "selector", where)
    if not isinstance(selector, str) or not selector.strip():
        raise ConfigError(f"{where}.selector: must be a non-empty string")

    raw_regex = spec.get("regex")
    pattern = None
    if raw_regex is not None:
        try:
            pattern = re.compile(raw_regex)
        except re.error as exc:
            raise ConfigError(f"{where}.regex: invalid pattern ({exc})") from exc
        if pattern.groups < 1:
            raise ConfigError(f"{where}.regex: pattern needs at least one capture group")

    return Field(
        name=name,
        selector=selector,
        attr=spec.get("attr"),
        regex=pattern,
        default=str(spec.get("default", "")),
        required=bool(spec.get("required", False)),
    )


def _parse_pagination(spec: Any) -> Pagination:
    if not isinstance(spec, dict):
        raise ConfigError("pagination: expected a mapping")

    selector = _require(spec, "selector", "pagination")
    max_pages = spec.get("max_pages", 10)
    if not isinstance(max_pages, int) or max_pages < 1:
        raise ConfigError("pagination.max_pages: must be a positive integer")

    return Pagination(
        selector=selector,
        attr=spec.get("attr", "href"),
        max_pages=max_pages,
    )

def _parse_request(spec: Any) -> RequestSettings:
    if spec is None:
        return RequestSettings()
    if not isinstance(spec, dict):
        raise ConfigError("request: expected a mapping")

    defaults = RequestSettings()
    delay = float(spec.get("delay", defaults.delay))
    timeout = float(spec.get("timeout", defaults.timeout))
    retries = int(spec.get("retries", defaults.retries))

    if delay < 0:
        raise ConfigError("request.delay: must not be negative")
    if timeout <= 0:
        raise ConfigError("request.timeout: must be positive")
    if retries < 0:
        raise ConfigError("request.retries: must not be negative")

    return RequestSettings(
        delay=delay,
        timeout=timeout,
        retries=retries,
        user_agent=str(spec.get("user_agent", defaults.user_agent)),
    )


def parse_config(data: Any) -> Config:
    """Build a Config from an already-loaded mapping."""
    if not isinstance(data, dict):
        raise ConfigError("config root: expected a mapping")

    start_urls = _require(data, "start_urls", "config")
    if isinstance(start_urls, str):
        start_urls = [start_urls]
    if not isinstance(start_urls, list) or not start_urls:
        raise ConfigError("start_urls: must be a non-empty list of URLs")
    for url in start_urls:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ConfigError(f"start_urls: {url!r} is not an http(s) URL")

    raw_fields = _require(data, "fields", "config")
    if not isinstance(raw_fields, dict) or not raw_fields:
        raise ConfigError("fields: must be a non-empty mapping of name -> spec")

    return Config(
        name=str(data.get("name", "scrapeflow")),
        start_urls=list(start_urls),
        row_selector=_require(data, "row_selector", "config"),
        fields=[_parse_field(name, spec) for name, spec in raw_fields.items()],
        pagination=_parse_pagination(data["pagination"]) if data.get("pagination") else None,
        request=_parse_request(data.get("request")),
    )


def load_config(path: str | Path) -> Config:
    """Read a YAML config file from disk."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: could not parse YAML ({exc})") from exc
    return parse_config(data)
