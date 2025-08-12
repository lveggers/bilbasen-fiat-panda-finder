"""Playwright client with rate limiting and error handling for Bilbasen scraping."""

import asyncio
import random
import time
from typing import Optional, List
from contextlib import asynccontextmanager

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError,
)
from playwright.async_api import Error as PlaywrightError

from ..config import settings
from ..logging_conf import get_logger
from .selectors import get_selector

logger = get_logger("playwright_client")


class RateLimiter:
    """Simple rate limiter for web requests."""

    def __init__(self, min_delay: float, max_delay: float):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0.0

    async def wait(self):
        """Wait for the appropriate delay between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Calculate delay with jitter
        base_delay = random.uniform(self.min_delay, self.max_delay)
        jitter = random.uniform(-0.2, 0.2) * base_delay
        delay = max(0.1, base_delay + jitter)

        # If we haven't waited long enough, sleep for the remaining time
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()


class PlaywrightClient:
    """Playwright client with built-in rate limiting and error handling."""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.rate_limiter = RateLimiter(
            settings.request_delay_min, settings.request_delay_max
        )
        self.fixtures_dir = settings.get_fixtures_path()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the browser and create context."""
        logger.info("Starting Playwright browser")

        try:
            self.playwright = await async_playwright().start()

            # Launch browser with appropriate settings
            self.browser = await self.playwright.chromium.launch(
                headless=settings.headless_browser,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                ],
            )

            # Create context with realistic settings
            self.context = await self.browser.new_context(
                user_agent=settings.user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="da-DK",
                timezone_id="Europe/Copenhagen",
                # Add some realistic browser features
                java_script_enabled=True,
                accept_downloads=False,
                has_touch=False,
                is_mobile=False,
            )

            # Set default timeouts
            self.context.set_default_timeout(30000)  # 30 seconds

            logger.info("Playwright browser started successfully")

        except Exception as e:
            logger.error(f"Failed to start Playwright browser: {e}")
            await self.close()
            raise

    async def close(self):
        """Close the browser and cleanup."""
        logger.info("Closing Playwright browser")

        try:
            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if hasattr(self, "playwright"):
                await self.playwright.stop()

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def new_page(self) -> Page:
        """Create a new page with common setup."""
        if not self.context:
            raise RuntimeError("Browser context not initialized")

        page = await self.context.new_page()

        # Add some stealth measures
        await page.add_init_script(
            """
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Mock plugins and languages
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['da-DK', 'da', 'en-US', 'en'],
            });
        """
        )

        return page

    async def get_page_with_retry(
        self,
        url: str,
        max_retries: int | None = None,
        wait_for_selector: str | None = None,
        save_fixture: bool = True,
    ) -> tuple[Page, str]:
        """
        Get a page with retry logic and fixture saving.

        Args:
            url: URL to fetch
            max_retries: Maximum number of retries (defaults to settings)
            wait_for_selector: CSS selector to wait for after loading
            save_fixture: Whether to save page content as fixture

        Returns:
            Tuple of (page, html_content)
        """
        if max_retries is None:
            max_retries = settings.retry_attempts

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Rate limiting
                if attempt > 0:
                    # Exponential backoff for retries
                    delay = settings.retry_delay_base * (2 ** (attempt - 1))
                    jitter = random.uniform(0.8, 1.2) * delay
                    logger.info(
                        f"Retry {attempt}/{max_retries} for {url}, waiting {jitter:.1f}s"
                    )
                    await asyncio.sleep(jitter)
                else:
                    await self.rate_limiter.wait()

                # Create new page for each attempt
                page = await self.new_page()

                try:
                    logger.info(f"Fetching: {url}")

                    # Navigate to page
                    response = await page.goto(url, wait_until="domcontentloaded")

                    if not response:
                        raise PlaywrightError("No response received")

                    if response.status >= 400:
                        raise PlaywrightError(
                            f"HTTP {response.status}: {response.status_text}"
                        )

                    # Handle cookie consent if present
                    await self._handle_cookie_consent(page)

                    # Wait for specific selector if provided
                    if wait_for_selector:
                        try:
                            await page.wait_for_selector(
                                wait_for_selector, timeout=10000
                            )
                        except TimeoutError:
                            logger.warning(
                                f"Timeout waiting for selector: {wait_for_selector}"
                            )

                    # Wait a bit for dynamic content
                    await page.wait_for_timeout(1000)

                    # Get page content
                    content = await page.content()

                    # Save fixture if requested
                    if save_fixture:
                        await self._save_fixture(url, content)

                    logger.info(f"Successfully fetched {url} (attempt {attempt + 1})")
                    return page, content

                except Exception as e:
                    await page.close()
                    raise e

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")

                # Check for specific errors that shouldn't be retried
                if isinstance(
                    e, PlaywrightError
                ) and "net::ERR_NAME_NOT_RESOLVED" in str(e):
                    logger.error(f"DNS resolution failed for {url}, not retrying")
                    break

        logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
        raise last_error or PlaywrightError(f"Failed to fetch {url}")

    async def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent banner if present."""
        try:
            cookie_selector = get_selector("common", "cookie_accept")
            if cookie_selector:
                cookie_button = await page.query_selector(cookie_selector)
                if cookie_button:
                    logger.debug("Accepting cookies")
                    await cookie_button.click()
                    await page.wait_for_timeout(1000)
        except Exception as e:
            logger.debug(f"Cookie consent handling failed (non-critical): {e}")

    async def _save_fixture(self, url: str, content: str):
        """Save page content as fixture for testing."""
        try:
            # Create a safe filename from URL
            filename = url.replace("https://", "").replace("http://", "")
            filename = "".join(
                c if c.isalnum() or c in ".-_" else "_" for c in filename
            )
            filename = filename[:100]  # Limit length

            timestamp = int(time.time())
            fixture_path = self.fixtures_dir / f"{filename}_{timestamp}.html"

            with open(fixture_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.debug(f"Saved fixture: {fixture_path}")

            # Keep only latest 5 fixtures per URL pattern
            pattern = filename.split("_")[0]
            existing_fixtures = list(self.fixtures_dir.glob(f"{pattern}_*.html"))
            if len(existing_fixtures) > 5:
                # Sort by modification time and remove oldest
                existing_fixtures.sort(key=lambda x: x.stat().st_mtime)
                for old_fixture in existing_fixtures[:-5]:
                    old_fixture.unlink()
                    logger.debug(f"Removed old fixture: {old_fixture}")

        except Exception as e:
            logger.warning(f"Failed to save fixture for {url}: {e}")

    async def extract_links(self, page: Page, selector: str) -> List[str]:
        """Extract all links matching selector from page."""
        try:
            elements = await page.query_selector_all(selector)
            links = []

            for element in elements:
                href = await element.get_attribute("href")
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith("/"):
                        href = f"{settings.base_url}{href}"
                    elif not href.startswith("http"):
                        href = f"{settings.base_url}/{href}"
                    links.append(href)

            return links

        except Exception as e:
            logger.error(f"Failed to extract links with selector {selector}: {e}")
            return []

    async def extract_text(self, page: Page, selector: str, default: str = "") -> str:
        """Extract text content from first matching element."""
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                return text.strip() if text else default
            return default

        except Exception as e:
            logger.debug(f"Failed to extract text with selector {selector}: {e}")
            return default

    async def extract_texts(self, page: Page, selector: str) -> List[str]:
        """Extract text content from all matching elements."""
        try:
            elements = await page.query_selector_all(selector)
            texts = []

            for element in elements:
                text = await element.inner_text()
                if text and text.strip():
                    texts.append(text.strip())

            return texts

        except Exception as e:
            logger.debug(f"Failed to extract texts with selector {selector}: {e}")
            return []


# Context manager for easy usage
@asynccontextmanager
async def get_playwright_client():
    """Context manager for PlaywrightClient."""
    client = PlaywrightClient()
    try:
        await client.start()
        yield client
    finally:
        await client.close()
