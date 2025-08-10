"""Main scraper module for Bilbasen Fiat Panda listings."""

import asyncio
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

from ..config import settings
from ..logging_conf import get_logger
from ..models import ListingCreate
from ..parse_condition import parse_condition
from .playwright_client import get_playwright_client
from .selectors import get_selector, get_pattern, URL_PATTERNS
from .json_extractor import BilbasenJSONExtractor

logger = get_logger("scraper")


@dataclass
class ScrapedListing:
    """Raw scraped listing data."""

    title: str
    url: str
    price_text: str = ""
    year_text: str = ""
    kilometers_text: str = ""
    condition_text: str = ""
    brand_text: str = ""
    model_text: str = ""
    fuel_type_text: str = ""
    transmission_text: str = ""
    body_type_text: str = ""
    location_text: str = ""
    dealer_name_text: str = ""


class BilbasenScraper:
    """Scraper for Bilbasen.dk Fiat Panda listings."""

    def __init__(self):
        self.search_url = settings.get_search_url()
        self.base_url = settings.base_url
        self.json_extractor = BilbasenJSONExtractor()

    async def scrape_search_results(self, max_pages: int = 5) -> List[ScrapedListing]:
        """
        Scrape search results from Bilbasen.

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            List of scraped listings
        """
        logger.info(
            f"Starting scrape of Bilbasen search results for '{settings.search_term}'"
        )
        all_listings = []

        async with get_playwright_client() as client:
            for page_num in range(1, max_pages + 1):
                try:
                    # Construct page URL
                    page_url = (
                        f"{self.search_url}&page={page_num}"
                        if page_num > 1
                        else self.search_url
                    )

                    logger.info(f"Scraping page {page_num}: {page_url}")

                    # Get page content
                    page, content = await client.get_page_with_retry(
                        page_url,
                        wait_for_selector=get_selector("search", "listings_container"),
                    )

                    try:
                        # Extract listing URLs from search results
                        listing_urls = await self._extract_listing_urls(page)

                        if not listing_urls:
                            logger.warning(f"No listings found on page {page_num}")
                            if page_num == 1:
                                # If no results on first page, check for "no results" message
                                no_results = await client.extract_text(
                                    page, get_selector("search", "no_results")
                                )
                                if no_results:
                                    logger.info("No results found for search term")
                                    break
                            else:
                                logger.info(
                                    f"Reached end of results at page {page_num}"
                                )
                                break

                        logger.info(
                            f"Found {len(listing_urls)} listings on page {page_num}"
                        )

                        # Scrape basic info from search results page
                        page_listings = await self._extract_search_page_listings(
                            page, listing_urls
                        )
                        all_listings.extend(page_listings)

                        # Check if there's a next page
                        next_page_link = await page.query_selector(
                            get_selector("search", "pagination_next")
                        )
                        if not next_page_link:
                            logger.info(f"No more pages after page {page_num}")
                            break

                    finally:
                        await page.close()

                except Exception as e:
                    logger.error(f"Error scraping page {page_num}: {e}")
                    continue

        logger.info(f"Scraped {len(all_listings)} total listings from {page_num} pages")
        return all_listings

    async def _extract_listing_urls(self, page) -> List[str]:
        """Extract listing URLs from search results page."""
        try:
            # Use the client from parameter, not undefined variable
            listing_link_elements = await page.query_selector_all(
                get_selector("search", "listing_link")
            )
            links = []

            for element in listing_link_elements:
                href = await element.get_attribute("href")
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith("/"):
                        href = f"{settings.base_url}{href}"
                    elif not href.startswith("http"):
                        href = f"{settings.base_url}/{href}"
                    links.append(href)

            # Filter and validate URLs
            listing_urls = []
            pattern = re.compile(URL_PATTERNS["listing_detail"])

            for link in links:
                if pattern.search(link):
                    listing_urls.append(link)

            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in listing_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)

            return unique_urls

        except Exception as e:
            logger.error(f"Failed to extract listing URLs: {e}")
            return []

    async def _extract_search_page_listings(
        self, page, urls: List[str]
    ) -> List[ScrapedListing]:
        """Extract basic listing data from search results page."""
        listings = []

        try:
            # Get all listing containers
            listing_containers = await page.query_selector_all(
                get_selector("search", "listing_items")
            )

            for i, container in enumerate(listing_containers):
                if i >= len(urls):
                    break

                try:
                    # Extract basic information from search result item
                    title = await self._extract_text_from_element(
                        container, get_selector("search", "listing_title")
                    )

                    price_text = await self._extract_text_from_element(
                        container, get_selector("search", "listing_price")
                    )

                    year_text = await self._extract_text_from_element(
                        container, get_selector("search", "listing_year")
                    )

                    kilometers_text = await self._extract_text_from_element(
                        container, get_selector("search", "listing_kilometers")
                    )

                    location_text = await self._extract_text_from_element(
                        container, get_selector("search", "listing_location")
                    )

                    # Create scraped listing
                    listing = ScrapedListing(
                        title=title or f"Fiat Panda Listing {i+1}",
                        url=urls[i],
                        price_text=price_text,
                        year_text=year_text,
                        kilometers_text=kilometers_text,
                        location_text=location_text,
                    )

                    listings.append(listing)

                except Exception as e:
                    logger.warning(
                        f"Failed to extract data from listing container {i}: {e}"
                    )
                    # Still add URL-only listing
                    if i < len(urls):
                        listing = ScrapedListing(
                            title=f"Fiat Panda Listing {i+1}", url=urls[i]
                        )
                        listings.append(listing)

        except Exception as e:
            logger.error(f"Failed to extract search page listings: {e}")
            # Fallback: create minimal listings from URLs
            for i, url in enumerate(urls):
                listing = ScrapedListing(title=f"Fiat Panda Listing {i+1}", url=url)
                listings.append(listing)

        return listings

    async def scrape_search_results_json(
        self, max_pages: int = 5
    ) -> List[ListingCreate]:
        """
        Scrape search results from Bilbasen using JSON extraction.

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            List of normalized listings ready for database
        """
        logger.info(f"Starting JSON-based scrape of Bilbasen search results")
        all_listings = []

        async with get_playwright_client() as client:
            for page_num in range(1, max_pages + 1):
                try:
                    # Construct page URL
                    page_url = (
                        f"{self.search_url}&page={page_num}"
                        if page_num > 1
                        else self.search_url
                    )

                    logger.info(f"Scraping page {page_num}: {page_url}")

                    # Get page content
                    page, content = await client.get_page_with_retry(
                        page_url,
                        wait_for_selector=get_selector("search", "listings_container"),
                    )

                    try:
                        # Extract listings from JSON data
                        normalized_listings = (
                            self.json_extractor.extract_listings_from_html(content)
                        )

                        if not normalized_listings:
                            logger.warning(f"No listings found on page {page_num}")
                            if page_num == 1:
                                logger.info("No results found for search term")
                                break
                            else:
                                logger.info(
                                    f"Reached end of results at page {page_num}"
                                )
                                break

                        logger.info(
                            f"Found {len(normalized_listings)} listings on page {page_num}"
                        )

                        # Convert to ListingCreate models
                        listing_models = self.json_extractor.create_listing_models(
                            normalized_listings
                        )
                        all_listings.extend(listing_models)

                        # Check if there are more pages by looking for next page button
                        next_page_link = await page.query_selector(
                            get_selector("search", "pagination_next")
                        )
                        if not next_page_link:
                            logger.info(f"No more pages after page {page_num}")
                            break

                    finally:
                        await page.close()

                except Exception as e:
                    logger.error(f"Error scraping page {page_num}: {e}")
                    continue

        logger.info(
            f"JSON-based scraping completed: {len(all_listings)} normalized listings"
        )
        return all_listings

    async def scrape_listing_details(
        self, scraped_listing: ScrapedListing
    ) -> ScrapedListing:
        """
        Scrape detailed information from individual listing page.

        Args:
            scraped_listing: Scraped listing with at least URL

        Returns:
            Updated scraped listing with detailed information
        """
        logger.info(f"Scraping details for: {scraped_listing.url}")

        async with get_playwright_client() as client:
            try:
                page, content = await client.get_page_with_retry(
                    scraped_listing.url,
                    wait_for_selector=get_selector("detail", "title"),
                )

                try:
                    # Extract detailed information
                    title = await client.extract_text(
                        page, get_selector("detail", "title")
                    )
                    if title:
                        scraped_listing.title = title

                    # Price information
                    if not scraped_listing.price_text:
                        scraped_listing.price_text = await client.extract_text(
                            page, get_selector("detail", "price")
                        )

                    # Year information
                    if not scraped_listing.year_text:
                        scraped_listing.year_text = await client.extract_text(
                            page, get_selector("detail", "year")
                        )

                    # Kilometers information
                    if not scraped_listing.kilometers_text:
                        scraped_listing.kilometers_text = await client.extract_text(
                            page, get_selector("detail", "kilometers")
                        )

                    # Condition information
                    scraped_listing.condition_text = await client.extract_text(
                        page, get_selector("detail", "condition")
                    )

                    # Additional details
                    scraped_listing.brand_text = await client.extract_text(
                        page, get_selector("detail", "brand")
                    )

                    scraped_listing.model_text = await client.extract_text(
                        page, get_selector("detail", "model")
                    )

                    scraped_listing.fuel_type_text = await client.extract_text(
                        page, get_selector("detail", "fuel_type")
                    )

                    scraped_listing.transmission_text = await client.extract_text(
                        page, get_selector("detail", "transmission")
                    )

                    scraped_listing.body_type_text = await client.extract_text(
                        page, get_selector("detail", "body_type")
                    )

                    scraped_listing.dealer_name_text = await client.extract_text(
                        page, get_selector("detail", "dealer_name")
                    )

                    if not scraped_listing.location_text:
                        scraped_listing.location_text = await client.extract_text(
                            page, get_selector("detail", "location")
                        )

                    # Try to extract from specifications table if main selectors fail
                    await self._extract_from_specs_table(page, scraped_listing)

                    logger.info(
                        f"Successfully scraped details for: {scraped_listing.url}"
                    )

                finally:
                    await page.close()

            except Exception as e:
                logger.error(f"Failed to scrape details for {scraped_listing.url}: {e}")

        return scraped_listing

    async def _extract_from_specs_table(self, page, scraped_listing: ScrapedListing):
        """Extract information from specifications table if available."""
        try:
            specs_table = await page.query_selector(
                get_selector("detail", "specs_table")
            )
            if not specs_table:
                return

            rows = await specs_table.query_selector_all(
                get_selector("detail", "specs_rows")
            )

            for row in rows:
                try:
                    label_element = await row.query_selector(
                        get_selector("detail", "spec_label")
                    )
                    value_element = await row.query_selector(
                        get_selector("detail", "spec_value")
                    )

                    if not (label_element and value_element):
                        continue

                    label = (await label_element.inner_text()).lower().strip()
                    value = (await value_element.inner_text()).strip()

                    # Map specifications to our fields
                    if not scraped_listing.year_text and "år" in label:
                        scraped_listing.year_text = value
                    elif not scraped_listing.kilometers_text and (
                        "km" in label or "kilometer" in label
                    ):
                        scraped_listing.kilometers_text = value
                    elif not scraped_listing.fuel_type_text and (
                        "brændstof" in label or "fuel" in label
                    ):
                        scraped_listing.fuel_type_text = value
                    elif not scraped_listing.transmission_text and (
                        "gear" in label or "transmission" in label
                    ):
                        scraped_listing.transmission_text = value
                    elif not scraped_listing.condition_text and (
                        "stand" in label or "condition" in label
                    ):
                        scraped_listing.condition_text = value

                except Exception as e:
                    logger.debug(f"Error processing spec row: {e}")

        except Exception as e:
            logger.debug(f"Error extracting from specs table: {e}")

    async def _extract_text_from_element(self, element, selector: str) -> str:
        """Extract text from element using selector."""
        try:
            sub_element = await element.query_selector(selector)
            if sub_element:
                text = await sub_element.inner_text()
                return text.strip() if text else ""
            return ""
        except Exception:
            return ""

    def normalize_scraped_data(self, scraped_listing: ScrapedListing) -> ListingCreate:
        """
        Normalize scraped data into structured format.

        Args:
            scraped_listing: Raw scraped data

        Returns:
            Normalized listing data ready for database
        """
        # Extract and normalize price
        price_dkk = self._extract_price(scraped_listing.price_text)

        # Extract and normalize year
        year = self._extract_year(scraped_listing.year_text)

        # Extract and normalize kilometers
        kilometers = self._extract_kilometers(scraped_listing.kilometers_text)

        # Parse condition
        condition_score, _ = parse_condition(scraped_listing.condition_text)

        # Normalize brand and model
        brand = self._normalize_text(scraped_listing.brand_text) or "Fiat"
        model = self._normalize_text(scraped_listing.model_text) or "Panda"

        return ListingCreate(
            title=scraped_listing.title,
            url=scraped_listing.url,
            price_dkk=price_dkk,
            year=year,
            kilometers=kilometers,
            condition_str=self._normalize_text(scraped_listing.condition_text),
            condition_score=condition_score,
            brand=brand,
            model=model,
            fuel_type=self._normalize_text(scraped_listing.fuel_type_text),
            transmission=self._normalize_text(scraped_listing.transmission_text),
            body_type=self._normalize_text(scraped_listing.body_type_text),
            location=self._normalize_text(scraped_listing.location_text),
            dealer_name=self._normalize_text(scraped_listing.dealer_name_text),
        )

    def _extract_price(self, price_text: str) -> Optional[int]:
        """Extract price from text."""
        if not price_text:
            return None

        try:
            # Remove common currency symbols and text
            clean_text = re.sub(r"[^\d.,]", "", price_text)
            clean_text = clean_text.replace(",", "").replace(".", "")

            if clean_text:
                return int(clean_text)
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse price: '{price_text}'")

        return None

    def _extract_year(self, year_text: str) -> Optional[int]:
        """Extract year from text."""
        if not year_text:
            return None

        try:
            # Look for 4-digit year
            match = re.search(r"\b(19|20)\d{2}\b", year_text)
            if match:
                year = int(match.group())
                # Sanity check
                if 1980 <= year <= 2030:
                    return year
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse year: '{year_text}'")

        return None

    def _extract_kilometers(self, km_text: str) -> Optional[int]:
        """Extract kilometers from text."""
        if not km_text:
            return None

        try:
            # Remove non-digit characters except decimal separators
            clean_text = re.sub(r"[^\d.,]", "", km_text)
            clean_text = clean_text.replace(",", "").replace(".", "")

            if clean_text:
                km = int(clean_text)
                # Sanity check (reasonable range for car mileage)
                if 0 <= km <= 2000000:  # Up to 2 million km
                    return km
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse kilometers: '{km_text}'")

        return None

    def _normalize_text(self, text: str) -> Optional[str]:
        """Normalize text field."""
        if not text or not text.strip():
            return None

        normalized = text.strip()
        # Remove excessive whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized if normalized else None

    async def scrape_full_listings(
        self, max_pages: int = 5, use_json: bool = True
    ) -> List[ListingCreate]:
        """
        Complete scraping workflow.

        Args:
            max_pages: Maximum number of search result pages to scrape
            use_json: Whether to use JSON extraction (recommended) or DOM scraping

        Returns:
            List of normalized listings ready for database
        """
        logger.info(
            f"Starting full scraping workflow (max_pages={max_pages}, use_json={use_json})"
        )

        if use_json:
            # Use the new JSON-based approach (faster and more reliable)
            return await self.scrape_search_results_json(max_pages)
        else:
            # Use the legacy DOM-based approach
            return await self._scrape_full_listings_legacy(max_pages)

    async def _scrape_full_listings_legacy(
        self, max_pages: int = 5
    ) -> List[ListingCreate]:
        """Legacy DOM-based scraping workflow (kept for compatibility)."""
        logger.info("Using legacy DOM-based scraping")

        # Step 1: Scrape search results
        scraped_listings = await self.scrape_search_results(max_pages)

        if not scraped_listings:
            logger.warning("No listings found in search results")
            return []

        # Step 2: Scrape individual listing details
        logger.info(f"Scraping details for {len(scraped_listings)} listings")

        detailed_listings = []
        for i, listing in enumerate(scraped_listings):
            try:
                logger.info(f"Processing listing {i+1}/{len(scraped_listings)}")
                detailed_listing = await self.scrape_listing_details(listing)
                detailed_listings.append(detailed_listing)

                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"Completed {i+1}/{len(scraped_listings)} listings")

            except Exception as e:
                logger.error(f"Failed to scrape details for listing {i+1}: {e}")
                # Keep the original listing without details
                detailed_listings.append(listing)

        scraped_listings = detailed_listings

        # Step 3: Normalize all data
        logger.info("Normalizing scraped data")
        normalized_listings = []

        for listing in scraped_listings:
            try:
                normalized = self.normalize_scraped_data(listing)
                normalized_listings.append(normalized)
            except Exception as e:
                logger.error(f"Failed to normalize listing {listing.url}: {e}")

        logger.info(
            f"Legacy scraping completed: {len(normalized_listings)} normalized listings"
        )
        return normalized_listings


# Convenience function
async def scrape_bilbasen_listings(
    max_pages: int = 3, use_json: bool = True
) -> List[ListingCreate]:
    """
    Convenience function to scrape Bilbasen listings.

    Args:
        max_pages: Maximum number of search result pages to scrape
        use_json: Whether to use JSON extraction (recommended) or DOM scraping

    Returns:
        List of normalized listings ready for database
    """
    scraper = BilbasenScraper()
    return await scraper.scrape_full_listings(max_pages, use_json)
