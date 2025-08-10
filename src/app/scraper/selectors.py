"""CSS and XPath selectors for Bilbasen.dk scraping."""

from typing import Dict, Any

# CSS selectors for different page elements
SELECTORS = {
    # Search results page
    "search": {
        "listings_container": "section.srp_results__2UEV_",
        "listing_items": "article.Listing_listing__XwaYe",
        "listing_link": "a.Listing_link__6Z504",
        "listing_title": ".Listing_title__qH4Gv, h3, .bb-listing-headline",
        "listing_price": ".Listing_price__q15mE, .bb-listing-price, [data-testid='price']",
        "listing_year": ".Listing_year__dBuOe, .bb-listing-year, [data-testid='year']",
        "listing_kilometers": ".Listing_km__Kd7o4, .bb-listing-km, [data-testid='mileage']",
        "listing_location": ".Listing_location__KjqBZ, .bb-listing-location, [data-testid='location']",
        "pagination_next": "button[aria-label='Næste'], a[aria-label='Næste'], .pagination-next",
        "no_results": ".no-results, .empty-state",
    },
    # Individual listing detail page
    "detail": {
        "title": "h1, .listing-title, [data-testid='title']",
        "price": ".price, .listing-price, [data-testid='price']",
        "year": ".year, [data-testid='year']",
        "kilometers": ".kilometers, .mileage, [data-testid='mileage']",
        "condition": ".condition, .state, [data-testid='condition']",
        "brand": ".brand, [data-testid='brand']",
        "model": ".model, [data-testid='model']",
        "fuel_type": ".fuel, [data-testid='fuel-type']",
        "transmission": ".transmission, [data-testid='transmission']",
        "body_type": ".body-type, [data-testid='body-type']",
        "dealer_name": ".dealer-name, [data-testid='dealer-name']",
        "location": ".location, [data-testid='location']",
        "description": ".description, .listing-description",
        # Detailed specifications table
        "specs_table": "table.specifications, .specs-table",
        "specs_rows": "tr",
        "spec_label": "td:first-child, th:first-child",
        "spec_value": "td:last-child, td:nth-child(2)",
        # Alternative selectors for different page layouts
        "alt_price": ".price-value, .listing-price-value",
        "alt_year": ".production-year, .car-year",
        "alt_kilometers": ".odometer, .car-mileage",
        "alt_condition": ".car-condition, .vehicle-state",
    },
    # Common elements
    "common": {
        "cookie_banner": ".cookie-banner, #cookie-consent",
        "cookie_accept": ".accept-cookies, #accept-cookies",
        "loading_spinner": ".loading, .spinner",
        "error_message": ".error, .alert-danger",
        "captcha": ".captcha, #captcha",
    },
}

# XPath selectors for more complex queries
XPATH_SELECTORS = {
    "search": {
        "listing_links": "//a[contains(@href, '/brugt/bil/')]",
        "price_text": "//text()[contains(., 'kr.') or contains(., 'DKK')]",
        "year_text": "//text()[matches(., '\\d{4}')]",
        "km_text": "//text()[contains(., 'km')]",
    },
    "detail": {
        "price_numbers": "//text()[matches(., '[0-9.,]+\\s*kr')]",
        "year_numbers": "//text()[matches(., '(19|20)\\d{2}')]",
        "km_numbers": "//text()[matches(., '[0-9.,]+\\s*km')]",
        "spec_pairs": "//tr[td[2]]",
    },
}

# Text patterns for extracting data
TEXT_PATTERNS = {
    "price": {
        "regex": r"([\d.,]+)\s*(?:kr\.?|DKK)",
        "clean": r"[^\d]",  # Remove non-digits for conversion
    },
    "year": {
        "regex": r"\b(19|20)\d{2}\b",
        "clean": r"[^\d]",
    },
    "kilometers": {
        "regex": r"([\d.,]+)\s*km",
        "clean": r"[^\d]",
    },
    "condition": {
        "keywords": [
            "nysynet",
            "topstand",
            "velholdt",
            "pæn",
            "god stand",
            "brugt",
            "slidte",
            "reparationsobjekt",
            "defekt",
        ]
    },
}

# Fallback selectors for different layouts or updates
FALLBACK_SELECTORS = {
    "listing_containers": [
        "div[data-testid='search-results']",
        ".search-results",
        ".listings-container",
        "main .listings",
        "#search-results",
    ],
    "listing_items": [
        "div[data-testid='listing-item']",
        ".bb-listing-clickable",
        ".listing-item",
        ".car-listing",
        "article",
    ],
    "prices": [
        "[data-testid='price']",
        ".bb-listing-price",
        ".price",
        ".listing-price",
        ".price-value",
    ],
    "titles": [
        "h3",
        ".bb-listing-headline",
        ".listing-title",
        "[data-testid='title']",
        "h2",
    ],
}

# Common wait conditions
WAIT_CONDITIONS = {
    "search_loaded": "div[data-testid='search-results'], .search-results",
    "detail_loaded": "h1, .listing-title",
    "no_captcha": ":not(.captcha)",
    "no_loading": ":not(.loading)",
}

# URL patterns for validation
URL_PATTERNS = {
    "listing_detail": r"/brugt/bil/[^/]+/\d+",
    "search_results": r"/brugt/bil\?.*FreeTxt=",
    "valid_domain": r"^https?://(?:www\.)?bilbasen\.dk",
}


def get_selector(category: str, key: str, fallback: bool = True) -> str:
    """
    Get a CSS selector with optional fallback.

    Args:
        category: Selector category ('search', 'detail', 'common')
        key: Specific selector key
        fallback: Whether to include fallback selectors

    Returns:
        CSS selector string, potentially with multiple selectors separated by commas
    """
    primary_selector = SELECTORS.get(category, {}).get(key, "")

    if not fallback or not primary_selector:
        return primary_selector

    # Add fallback selectors if available
    fallback_key = f"{key}s" if key.endswith(("item", "container")) else key
    fallbacks = FALLBACK_SELECTORS.get(fallback_key, [])

    if fallbacks:
        all_selectors = [primary_selector] + fallbacks
        return ", ".join(filter(None, all_selectors))

    return primary_selector


def get_xpath(category: str, key: str) -> str:
    """Get an XPath selector."""
    return XPATH_SELECTORS.get(category, {}).get(key, "")


def get_pattern(data_type: str, pattern_type: str = "regex") -> str:
    """Get a regex pattern for data extraction."""
    return TEXT_PATTERNS.get(data_type, {}).get(pattern_type, "")


def get_wait_condition(condition: str) -> str:
    """Get a wait condition selector."""
    return WAIT_CONDITIONS.get(condition, "")
