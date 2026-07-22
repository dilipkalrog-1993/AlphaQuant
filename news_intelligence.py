"""Bounded, non-blocking market-news intelligence for AlphaQuant.

Only provider metadata and snippets are retained; article bodies are never fetched.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree
import hashlib
import json
import os
import re
import tempfile
import time

import requests

CATEGORIES = ("MARKET", "MACRO", "SECTOR", "COMPANY", "EARNINGS", "REGULATORY",
    "CORPORATE ACTION", "MANAGEMENT", "M&A", "ORDER WIN", "PRODUCT", "LITIGATION",
    "CREDIT RATING", "FUND RAISING", "DIVIDEND", "SPLIT / BONUS",
    "FRAUD / GOVERNANCE", "BROKER / EXCHANGE", "OTHER")
SOURCE_QUALITY = {"Reuters": 95, "Business Standard": 85, "The Hindu BusinessLine": 85,
    "Economic Times": 80, "NewsAPI": 70, "Google News": 65, "Unknown": 50}
ALIASES = {"RELIANCE": ("reliance industries", "ril"), "TCS": ("tata consultancy services",),
    "INFY": ("infosys",), "HDFCBANK": ("hdfc bank",), "ICICIBANK": ("icici bank",),
    "SBIN": ("state bank of india",), "BHARTIARTL": ("bharti airtel",),
    "ITC": ("itc limited",), "LT": ("larsen and toubro", "l&t")}
SECTORS = {"RELIANCE":"Energy", "TCS":"Information Technology", "INFY":"Information Technology",
    "HDFCBANK":"Financial Services", "ICICIBANK":"Financial Services", "SBIN":"Financial Services",
    "BHARTIARTL":"Telecommunication", "ITC":"Consumer Goods", "LT":"Industrials"}
AMBIGUOUS_ALIASES = {"it", "ai", "oil", "bank", "lt", "in", "tcs"}


def _utc(value: Any = None) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value:
        try: return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError: pass
    return datetime.now(timezone.utc)


def _clean(text: Any, limit: int = 600) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()[:limit]


def _canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")])
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))
    except ValueError: return url


@dataclass
class NewsArticle:
    headline: str
    description: str
    source: str
    published_at: str
    url: str
    provider: str
    author: str = ""
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    related_symbols: list[str] = field(default_factory=list)
    related_sectors: list[str] = field(default_factory=list)
    match_confidence: float = 0.0
    category: str = "OTHER"
    urgency: str = "LOW"
    sentiment: str = "UNKNOWN"
    news_relevance_score: int = 0
    news_risk_score: int = 0
    news_sentiment_score: int = 0
    score_reasons: list[str] = field(default_factory=list)


class NewsProvider(ABC):
    name = "provider"
    @abstractmethod
    def fetch(self, query: str, timeout: float) -> list[dict[str, Any]]: ...


class NewsAPIProvider(NewsProvider):
    name = "NewsAPI"
    def __init__(self, api_key: str): self.api_key = api_key
    def fetch(self, query: str, timeout: float) -> list[dict[str, Any]]:
        response = requests.get("https://newsapi.org/v2/everything", params={"q":query,
            "language":"en", "sortBy":"publishedAt", "pageSize":100},
            headers={"X-Api-Key":self.api_key}, timeout=timeout)
        response.raise_for_status()
        return response.json().get("articles", [])


class RSSProvider(NewsProvider):
    name = "RSS"
    DEFAULT_FEEDS = ("https://news.google.com/rss/search?q=Indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en",)
    def __init__(self, feeds: tuple[str, ...] | None = None): self.feeds = feeds or self.DEFAULT_FEEDS
    def fetch(self, query: str, timeout: float) -> list[dict[str, Any]]:
        rows = []
        for feed in self.feeds:
            response = requests.get(feed, timeout=timeout, headers={"User-Agent":"AlphaQuant/3.1"})
            response.raise_for_status()
            for item in ElementTree.fromstring(response.content).findall(".//item")[:100]:
                get = lambda tag: _clean(item.findtext(tag))
                rows.append({"title":get("title"), "description":get("description"),
                    "url":get("link"), "publishedAt":get("pubDate"),
                    "source":{"name":get("source") or "Google News"}, "author":""})
        return rows


class NewsManager:
    """One process-wide worker, TTL cache, scoring, clustering and persistence."""
    def __init__(self, cache_path: str | Path, config: dict[str, Any] | None = None):
        self.cache_path, self.lock = Path(cache_path), RLock()
        self.config = {"enabled":False, "provider":"RSS", "fetch_interval_minutes":15,
            "ttl_hours":24, "retention_days":14, "request_timeout":10, "max_articles":500,
            "api_key":"", **(config or {})}
        self.state = {"articles":[], "clusters":[], "briefing_history":[], "alerted_ids":[],
            "provider_status":"DISABLED", "last_fetch":None, "last_successful_fetch":None,
            "last_error":None, "request_duration_ms":None, "deduplication_count":0,
            "unmapped_count":0, "rate_limit_state":"OK", "next_scheduled_fetch":None,
            "stale":False}
        self.stop_event, self.wake, self.thread = Event(), Event(), None
        self._load()

    def configure(self, **changes: Any) -> None:
        with self.lock:
            # API keys remain memory-only and are never included in state/cache/logs.
            changed = any(self.config.get(key) != value for key, value in changes.items())
            self.config.update(changes)
        if self.config["enabled"]: self.start()
        if changed: self.wake.set()

    def start(self) -> bool:
        with self.lock:
            if self.thread and self.thread.is_alive(): return False
            self.stop_event.clear()
            self.thread = Thread(target=self._run, name="alphaquant-news-worker", daemon=True)
            self.thread.start()
            return True

    def stop(self) -> None: self.stop_event.set(); self.wake.set()
    def request_refresh(self) -> None: self.wake.set()

    def _provider(self) -> NewsProvider:
        if self.config.get("provider") == "NewsAPI" and self.config.get("api_key"):
            return NewsAPIProvider(str(self.config["api_key"]))
        return RSSProvider()

    def _run(self) -> None:
        failures = 0
        while not self.stop_event.is_set():
            if self.config.get("enabled"):
                try: self.fetch_once(); failures = 0
                except Exception as exc:
                    failures += 1
                    with self.lock:
                        self.state.update(provider_status="DEGRADED", stale=True,
                            last_error=f"{type(exc).__name__}: news transport failed",
                            rate_limit_state="BACKOFF" if failures else "OK")
                        self._persist()
            interval = max(60, int(self.config.get("fetch_interval_minutes", 15)) * 60)
            delay = min(interval, 60 * (2 ** min(failures, 5))) if failures else interval
            with self.lock: self.state["next_scheduled_fetch"] = (datetime.now(timezone.utc)+timedelta(seconds=delay)).isoformat()
            self.wake.wait(delay); self.wake.clear()

    def fetch_once(self, raw_articles: list[dict[str, Any]] | None = None,
            context: dict[str, set[str]] | None = None) -> dict[str, Any]:
        started, now = time.perf_counter(), datetime.now(timezone.utc)
        provider = self._provider()
        raw = raw_articles if raw_articles is not None else provider.fetch(
            "India stock market OR NSE OR earnings OR RBI", float(self.config["request_timeout"]))
        articles = [self._normalize(item, provider.name, context or {}) for item in raw]
        articles = [item for item in articles if item.headline and item.url]
        cutoff = now - timedelta(days=int(self.config["retention_days"]))
        articles = [item for item in articles if _utc(item.published_at) >= cutoff]
        clusters = self._cluster(articles)
        with self.lock:
            previous = {item["url"]:item for item in self.state.get("articles", [])}
            previous.update({_canonical_url(item.url):asdict(item) for item in articles})
            kept = sorted(previous.values(), key=lambda x:x.get("published_at", ""), reverse=True)[:int(self.config["max_articles"])]
            self.state.update(articles=kept, clusters=clusters, provider_status="HEALTHY",
                last_fetch=now.isoformat(), last_successful_fetch=now.isoformat(), last_error=None,
                stale=False, request_duration_ms=round((time.perf_counter()-started)*1000, 1),
                deduplication_count=max(0, len(articles)-len(clusters)),
                unmapped_count=sum(not item.related_symbols for item in articles), rate_limit_state="OK")
            self._persist()
            return self.snapshot()

    def _normalize(self, raw: dict[str, Any], provider: str, context: dict[str, set[str]]) -> NewsArticle:
        source = raw.get("source", {})
        source = source.get("name", "Unknown") if isinstance(source, dict) else str(source or "Unknown")
        article = NewsArticle(headline=_clean(raw.get("title") or raw.get("headline"), 300),
            description=_clean(raw.get("description") or raw.get("summary")), source=source,
            author=_clean(raw.get("author"), 100), published_at=_utc(raw.get("publishedAt") or raw.get("published_at")).isoformat(),
            url=_canonical_url(str(raw.get("url") or raw.get("link") or "")), provider=provider)
        self._map(article); self._classify(article); self._score(article, context)
        return article

    def _map(self, article: NewsArticle) -> None:
        text = f" {article.headline} {article.description} ".lower()
        matches = []
        for symbol, aliases in ALIASES.items():
            for alias in aliases:
                if alias in AMBIGUOUS_ALIASES or len(alias) < 4: continue
                if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text): matches.append(symbol); break
        article.related_symbols = sorted(set(matches))
        article.related_sectors = sorted({SECTORS[s] for s in matches if s in SECTORS})
        article.match_confidence = 0.95 if matches else 0.0

    def _classify(self, article: NewsArticle) -> None:
        text = f"{article.headline} {article.description}".lower()
        rules = [("FRAUD / GOVERNANCE",("fraud","governance","accounting irregular")),
            ("REGULATORY",("regulator","sebi","rbi penalty","regulatory")), ("EARNINGS",("earnings","quarterly result","profit","revenue")),
            ("M&A",("merger","acquisition","takeover")), ("LITIGATION",("lawsuit","court","litigation")),
            ("DIVIDEND",("dividend",)), ("SPLIT / BONUS",("stock split","bonus share")),
            ("CREDIT RATING",("credit rating","downgrade")), ("FUND RAISING",("fund raising","fundraising","rights issue")),
            ("ORDER WIN",("wins order","order win")), ("MANAGEMENT",("ceo","resignation","management")),
            ("CORPORATE ACTION",("buyback","corporate action")), ("MACRO",("inflation","interest rate","gdp","rbi"))]
        article.category = next((category for category, words in rules if any(word in text for word in words)),
            "COMPANY" if article.related_symbols else "MARKET")
        negative = ("fraud","probe","penalty","downgrade","loss","default","lawsuit","resigns","fall","decline")
        positive = ("beats","growth","upgrade","profit rises","order win","record high","dividend")
        neg, pos = sum(word in text for word in negative), sum(word in text for word in positive)
        score = max(-100, min(100, (pos-neg)*30)); article.news_sentiment_score = score
        article.sentiment = "MIXED" if pos and neg else "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL"
        severe = article.category in {"FRAUD / GOVERNANCE","REGULATORY","LITIGATION"}
        article.urgency = "CRITICAL" if severe and article.sentiment == "NEGATIVE" and article.related_symbols else "HIGH" if severe or article.category == "EARNINGS" else "MEDIUM" if article.related_symbols else "LOW"

    def _score(self, article: NewsArticle, context: dict[str, set[str]]) -> None:
        age = max(0, (_utc()-_utc(article.published_at)).total_seconds()/3600)
        recency = max(0, 30-int(age*2)); quality = SOURCE_QUALITY.get(article.source, 50)//5
        reasons = [f"Published {int(age)} hours ago" if age >= 1 else "Published within the last hour"]
        relevance = recency + quality
        if article.related_symbols: relevance += 25; reasons.append("Direct company alias match")
        symbols = set(article.related_symbols)
        if symbols & set(context.get("positions", set())): relevance += 20; reasons.append("Open-position relevance")
        if symbols & set(context.get("candidates", set())): relevance += 15; reasons.append("Active-candidate relevance")
        if symbols & set(context.get("watchlist", set())): relevance += 10; reasons.append("Watchlist relevance")
        severity = {"CRITICAL":45,"HIGH":30,"MEDIUM":15,"LOW":5}[article.urgency]
        article.news_relevance_score = min(100, relevance)
        article.news_risk_score = min(100, severity + max(0, -article.news_sentiment_score)//2 + (20 if symbols else 0))
        article.score_reasons = reasons

    def _cluster(self, articles: list[NewsArticle]) -> list[dict[str, Any]]:
        clusters: list[dict[str, Any]] = []
        for article in sorted(articles, key=lambda x:x.published_at):
            normalized = re.sub(r"[^a-z0-9 ]", "", article.headline.lower())
            found = None
            for cluster in clusters:
                close = abs((_utc(article.published_at)-_utc(cluster["latest_update"])).total_seconds()) <= 86400
                overlap = bool(set(article.related_symbols) & set(cluster["related_symbols"])) or not article.related_symbols
                if article.url in cluster["urls"] or (close and overlap and SequenceMatcher(None, normalized, cluster["normalized_headline"]).ratio() >= .78): found=cluster; break
            if found:
                found["supporting_sources"] = sorted(set(found["supporting_sources"]+[article.source]))
                found["urls"].append(article.url); found["latest_update"] = article.published_at
                found["source_count"] = len(found["supporting_sources"])
            else:
                clusters.append({"id":hashlib.sha256((normalized+article.published_at[:10]).encode()).hexdigest()[:16],
                    "primary_headline":article.headline, "normalized_headline":normalized,
                    "supporting_sources":[article.source], "urls":[article.url],
                    "earliest_publication":article.published_at, "latest_update":article.published_at,
                    "source_count":1, "related_symbols":article.related_symbols})
        return clusters

    def briefing(self, kind: str = "INTRADAY") -> str:
        with self.lock: items = list(self.state.get("articles", []))[:8]
        label = kind.upper().replace("_", " ") + " BRIEF"
        if not items: return f"{label}. No current verified news metadata is available."
        lines = [label + "."]
        for item in items[:5]:
            affected = f" Affected: {', '.join(item['related_symbols'])}." if item.get("related_symbols") else ""
            lines.append(f"{item['headline']}. Source: {item['source']}.{affected}")
        return " ".join(lines)

    def candidate_effect(self, symbol: str) -> dict[str, Any]:
        cutoff = _utc()-timedelta(hours=float(self.config.get("ttl_hours", 24)))
        with self.lock: relevant = [a for a in self.state.get("articles", []) if symbol in a.get("related_symbols", []) and _utc(a.get("published_at")) >= cutoff]
        relevant.sort(key=lambda a:a.get("news_risk_score",0), reverse=True)
        top = relevant[0] if relevant else None
        veto = bool(top and top.get("urgency") == "CRITICAL" and top.get("sentiment") == "NEGATIVE")
        return {"news_status":"RISK VETO" if veto else "CONFIRMATION" if top else "NO CURRENT NEWS",
            "news_relevance":top.get("news_relevance_score",0) if top else 0,
            "news_sentiment":top.get("news_sentiment_score",0) if top else 0,
            "news_risk":top.get("news_risk_score",0) if top else 0,
            "news_summary":top.get("description") or top.get("headline","") if top else "",
            "news_timestamp":top.get("published_at") if top else None,
            "news_sources":[top.get("source")] if top else [],
            "news_effect_on_confidence":-10 if veto else 3 if top and top.get("sentiment") == "POSITIVE" else 0,
            "news_veto_reason":"Critical negative company-specific news requires risk review." if veto else None}

    def claim_critical_alert(self, cooldown_minutes: int = 30) -> str | None:
        """Atomically claim one unseen critical alert, preventing repeated speech."""
        now = _utc()
        with self.lock:
            alerted = {item.get("id"):_utc(item.get("time")) for item in self.state.get("alerted_ids", [])}
            for article in self.state.get("articles", []):
                if article.get("urgency") != "CRITICAL": continue
                alert_id = hashlib.sha256((article.get("url","")+article.get("headline","")).encode()).hexdigest()[:16]
                if alert_id in alerted and now-alerted[alert_id] < timedelta(minutes=cooldown_minutes): continue
                self.state.setdefault("alerted_ids", []).append({"id":alert_id,"time":now.isoformat()})
                self.state["alerted_ids"] = self.state["alerted_ids"][-200:]
                self._persist()
                symbol = next(iter(article.get("related_symbols", [])), "the market")
                category = str(article.get("category", "important event")).lower().replace("/", " or ")
                return f"Critical news for {symbol}. {category} detected. Review risk now."
        return None

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            state = json.loads(json.dumps(self.state)); state["cache_size"] = len(state.get("articles", []))
            state["worker_alive"] = bool(self.thread and self.thread.is_alive()); return state

    def _load(self) -> None:
        try:
            saved = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(saved, dict): self.state.update(saved)
        except (OSError, ValueError): pass

    def _persist(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.state, ensure_ascii=False, indent=2)
        fd, temporary = tempfile.mkstemp(prefix="news-", suffix=".tmp", dir=self.cache_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle: handle.write(payload)
            os.replace(temporary, self.cache_path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
