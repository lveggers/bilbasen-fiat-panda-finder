#!/usr/bin/env python3
"""
Debug script to investigate Bilbasen pagination structure.
"""

import asyncio
import json
import re
from src.app.scraper.playwright_client import get_playwright_client
from src.app.scraper.selectors import get_selector
from src.app.logging_conf import get_logger

logger = get_logger("debug_pagination")

async def debug_pagination():
    """Debug pagination structure on Bilbasen."""
    search_url = "https://www.bilbasen.dk/brugt/bil/fiat/panda?includeengroscvr=true&includeleasing=false"
    
    async with get_playwright_client() as client:
        # Get first page
        page, content = await client.get_page_with_retry(
            search_url,
            wait_for_selector=get_selector("search", "listings_container"),
        )
        
        try:
            # Check for pagination elements
            print("=== PAGINATION DEBUGGING ===")
            
            # Check current pagination selector
            current_selector = get_selector("search", "pagination_next")
            print(f"Current pagination selector: {current_selector}")
            
            next_elements = await page.query_selector_all(current_selector)
            print(f"Found {len(next_elements)} elements with current selector")
            
            # Try different pagination selectors
            selectors_to_try = [
                "button[aria-label='Næste']",
                "a[aria-label='Næste']", 
                ".pagination-next",
                "[data-testid='pagination-next']",
                "button:has-text('Næste')",
                "a:has-text('Næste')",
                ".pagination button:last-child",
                ".pagination a:last-child",
                "nav button[disabled]:not(:has-text('Forrige'))",
                "nav a[aria-disabled='false']:has-text('Næste')",
                ".pagination .next",
                ".pager .next",
                "[data-pagination-next]",
                "li.next a",
                ".pagination li:last-child a",
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"[+] Found {len(elements)} elements with selector: {selector}")
                        for i, elem in enumerate(elements[:3]):  # Show first 3
                            text = await elem.inner_text()
                            html = await elem.evaluate("el => el.outerHTML")
                            print(f"  [{i}] Text: '{text}' HTML: {html[:100]}...")
                    else:
                        print(f"[-] No elements found with selector: {selector}")
                except Exception as e:
                    print(f"[!] Error with selector '{selector}': {e}")
            
            # Look for any pagination-related elements
            print("\n=== GENERAL PAGINATION SEARCH ===")
            
            # Search for any elements containing pagination-related text
            pagination_texts = ["Næste", "Next", "side", "page", ">", "»", "›"]
            for text in pagination_texts:
                try:
                    elements = await page.query_selector_all(f"*:has-text('{text}')")
                    print(f"Elements containing '{text}': {len(elements)}")
                    if elements and len(elements) < 20:  # Don't spam too many results
                        for i, elem in enumerate(elements[:5]):
                            try:
                                tag_name = await elem.evaluate("el => el.tagName")
                                element_text = await elem.inner_text()
                                if element_text and len(element_text.strip()) < 50:
                                    print(f"  [{i}] {tag_name}: '{element_text.strip()}'")
                            except:
                                pass
                except Exception as e:
                    print(f"Error searching for text '{text}': {e}")
            
            # Check for JSON data that might contain pagination info
            print("\n=== JSON PAGINATION DATA ===")
            
            script_pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
            match = re.search(script_pattern, content, re.DOTALL)
            
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    
                    # Look for pagination-related keys
                    def find_pagination_keys(obj, path=""):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if any(p in key.lower() for p in ['page', 'total', 'count', 'pagination', 'next', 'hasmore']):
                                    print(f"  Found pagination key: {path}.{key} = {value}")
                                if isinstance(value, (dict, list)) and path.count('.') < 5:  # Limit depth
                                    find_pagination_keys(value, f"{path}.{key}" if path else key)
                        elif isinstance(obj, list) and len(obj) > 0:
                            find_pagination_keys(obj[0], f"{path}[0]")
                    
                    find_pagination_keys(data)
                    
                except json.JSONDecodeError:
                    print("Failed to parse JSON data")
            else:
                print("No __NEXT_DATA__ found")
                
        finally:
            await page.close()

if __name__ == "__main__":
    asyncio.run(debug_pagination())