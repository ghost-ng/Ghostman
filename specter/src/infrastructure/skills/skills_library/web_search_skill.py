"""
Web Search Skill - Search the web via DuckDuckGo (ddgs library).

Uses the ``ddgs`` library (the de-facto standard for AI agent web search,
used by LangChain, CrewAI, MetaGPT, etc.) to perform searches without
requiring any API key.  Falls back to Tavily if the user configures an
API key in settings for higher-quality, AI-optimised results.

All results are returned as structured dicts with title, URL, and snippet.
"""

import logging
import time
import random
from typing import Any, Dict, List, Optional

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

logger = logging.getLogger("specter.skills.web_search")

# Minimum seconds between consecutive DuckDuckGo searches to avoid rate-limits.
# Kept low — ddgs handles its own backoff; we just avoid hammering.
_MIN_DDG_DELAY = 1.0

# Simple in-memory cache: {query_key: (timestamp, results)}
_RESULT_CACHE: Dict[str, tuple] = {}
_CACHE_TTL = 300  # 5 minutes


class WebSearchSkill(BaseSkill):
    """
    Skill for searching the web.

    Primary provider: DuckDuckGo via the ``ddgs`` library (free, no API key).
    Optional provider: Tavily (free tier: 1 000 searches / month, requires key).

    Example:
        >>> skill = WebSearchSkill()
        >>> result = await skill.execute(query="Python asyncio tutorial", num_results=5)
        >>> for item in result.data["results"]:
        ...     print(item["title"], item["url"])
    """

    # Class-level timestamp shared across invocations to enforce rate-limiting
    _last_ddg_search: float = 0.0

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="web_search",
            name="Web Search",
            description="Search the web using DuckDuckGo (free) or Tavily",
            category=SkillCategory.PRODUCTIVITY,
            icon="search",
            enabled_by_default=True,
            requires_confirmation=False,
            permissions_required=[PermissionType.NETWORK_ACCESS],
            ai_callable=True,
            version="2.0.0",
            author="Specter",
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type=str,
                required=True,
                description="Search query to execute",
                constraints={"min_length": 1, "max_length": 500},
            ),
            SkillParameter(
                name="num_results",
                type=int,
                required=False,
                description="Maximum number of results to return",
                default=5,
                constraints={"min": 1, "max": 20},
            ),
        ]

    # ------------------------------------------------------------------
    # Provider dispatch
    # ------------------------------------------------------------------

    def _get_provider(self) -> str:
        """Return 'tavily' if an API key is configured, else 'ddg'."""
        try:
            from ...storage.settings_manager import settings
            tavily_key = settings.get("tools.web_search.tavily_api_key", "")
            if tavily_key and isinstance(tavily_key, str) and tavily_key.strip():
                return "tavily"
        except Exception:
            pass
        return "ddg"

    # ------------------------------------------------------------------
    # DuckDuckGo via ddgs library
    # ------------------------------------------------------------------

    def _search_ddg(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """
        Search via the ``ddgs`` library (DuckDuckGo).

        Implements polite rate-limiting, a hard timeout, and retry-on-ratelimit
        to avoid getting blocked by DuckDuckGo's anti-bot protections.
        """
        try:
            from ddgs import DDGS
        except ImportError:
            raise RuntimeError(
                "The 'ddgs' package is required for web search. "
                "Install it with: pip install ddgs"
            )

        # Polite delay between searches (short — ddgs handles its own backoff)
        elapsed = time.time() - WebSearchSkill._last_ddg_search
        if elapsed < _MIN_DDG_DELAY:
            wait = _MIN_DDG_DELAY - elapsed + random.uniform(0.1, 0.5)
            logger.debug("Rate-limiting: waiting %.1fs before DDG search", wait)
            time.sleep(wait)

        def _do_search() -> list:
            """Run the search in a thread with a hard timeout."""
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(DDGS().text, query, max_results=max_results)
                return future.result(timeout=15)  # 15s hard timeout

        try:
            raw = _do_search()
            WebSearchSkill._last_ddg_search = time.time()
        except Exception as exc:
            exc_str = str(exc)
            if "Ratelimit" in exc_str or "202" in exc_str:
                logger.warning("DuckDuckGo rate-limited, retrying in 5s …")
                time.sleep(5)
                try:
                    raw = _do_search()
                    WebSearchSkill._last_ddg_search = time.time()
                except Exception:
                    logger.warning("DuckDuckGo retry also failed")
                    return []
            elif "TimeoutError" in type(exc).__name__ or "timed out" in exc_str.lower():
                logger.warning("DuckDuckGo search timed out after 15s")
                return []
            else:
                raise

        results: List[Dict[str, str]] = []
        for item in raw or []:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "snippet": item.get("body", "")[:300],
            })
        return results

    # ------------------------------------------------------------------
    # Tavily (optional, API-key based)
    # ------------------------------------------------------------------

    def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search via the Tavily API (requires API key in settings)."""
        try:
            from tavily import TavilyClient
        except ImportError:
            raise RuntimeError(
                "The 'tavily-python' package is required for Tavily search. "
                "Install it with: pip install tavily-python"
            )

        from ...storage.settings_manager import settings
        api_key = settings.get("tools.web_search.tavily_api_key", "")
        if not api_key:
            raise RuntimeError("Tavily API key not configured in settings")

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

        results: List[Dict[str, str]] = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:300],
            })
        return results

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute a web search.

        Tries the configured provider (Tavily if key set, else DuckDuckGo).
        If Tavily fails, automatically falls back to DuckDuckGo.
        Results are cached for 5 minutes to avoid redundant lookups when
        the model issues duplicate or near-identical queries.
        """
        try:
            query: str = params["query"]
            num_results: int = params.get("num_results", 5)
            provider = self._get_provider()

            # Check cache (exact query match, same provider)
            cache_key = f"{provider}:{query.strip().lower()}:{num_results}"
            cached = _RESULT_CACHE.get(cache_key)
            if cached:
                ts, cached_results = cached
                if time.time() - ts < _CACHE_TTL:
                    logger.info("Cache hit for: %s (%d results)", query, len(cached_results))
                    provider_name = "Tavily" if provider == "tavily" else "DuckDuckGo"
                    return SkillResult(
                        success=True,
                        message=f"Search complete for '{query}'",
                        data={
                            "results": cached_results,
                            "count": len(cached_results),
                            "query": query,
                            "provider": provider_name,
                        },
                        action_taken=f"Searched '{provider_name}' for: {query} (cached)",
                    )

            results: List[Dict[str, str]] = []

            # Try primary provider
            if provider == "tavily":
                try:
                    logger.info("Searching with Tavily for: %s", query)
                    results = self._search_tavily(query, num_results)
                    provider_name = "Tavily"
                except Exception as e:
                    logger.warning("Tavily search failed (%s), falling back to DuckDuckGo", e)
                    provider = "ddg"

            if provider == "ddg":
                logger.info("Searching with DuckDuckGo for: %s", query)
                results = self._search_ddg(query, num_results)
                provider_name = "DuckDuckGo"

            # Cache results
            if results:
                _RESULT_CACHE[cache_key] = (time.time(), results)
                # Evict old entries
                now = time.time()
                stale = [k for k, (t, _) in _RESULT_CACHE.items() if now - t > _CACHE_TTL]
                for k in stale:
                    del _RESULT_CACHE[k]

            if not results:
                logger.info("Search returned no results for: %s", query)
                return SkillResult(
                    success=True,
                    message=f"Search completed but no results found for '{query}'",
                    data={
                        "results": [],
                        "count": 0,
                        "query": query,
                        "provider": provider_name,
                    },
                    action_taken=f"Searched '{provider_name}' for: {query}",
                )

            logger.info(
                "Search via '%s' returned %d result(s) for: %s",
                provider_name, len(results), query,
            )

            return SkillResult(
                success=True,
                message=f"Search complete for '{query}'",
                data={
                    "results": results,
                    "count": len(results),
                    "query": query,
                    "provider": provider_name,
                },
                action_taken=f"Searched '{provider_name}' for: {query}",
            )

        except Exception as e:
            logger.error("Web search skill failed: %s", e, exc_info=True)
            return SkillResult(
                success=False,
                message="Web search failed",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    async def on_success(self, result: SkillResult) -> None:
        count = result.data.get("count", 0) if result.data else 0
        provider = result.data.get("provider", "unknown") if result.data else "unknown"
        logger.info("Web search succeeded: %d results via %s", count, provider)

    async def on_error(self, result: SkillResult) -> None:
        logger.warning("Web search failed: %s", result.error)
