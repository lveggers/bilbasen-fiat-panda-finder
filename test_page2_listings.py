#!/usr/bin/env python3
"""Test if page 2 has different listings."""

import asyncio
from src.app.scraper.json_extractor import BilbasenJSONExtractor  
from src.app.scraper.playwright_client import get_playwright_client
from src.app.scraper.selectors import get_selector

async def compare_pages():
    """Compare listings between page 1 and page 2."""
    
    base_url = "https://www.bilbasen.dk/brugt/bil/fiat/panda?includeengroscvr=true&includeleasing=false"
    page2_url = f"{base_url}&page=2"
    
    extractor = BilbasenJSONExtractor()
    
    async with get_playwright_client() as client:
        # Get page 1 listings
        print("=== PAGE 1 LISTINGS ===")
        page1, content1 = await client.get_page_with_retry(base_url)
        listings1 = extractor.extract_listings_from_html(content1)
        print(f"Page 1: Found {len(listings1)} listings")
        
        if listings1:
            print("First 3 listings on page 1:")
            for i, listing in enumerate(listings1[:3]):
                print(f"  {i+1}. {listing.get('title', 'N/A')} - {listing.get('price', 'N/A')} - {listing.get('url', 'N/A')}")
        
        await page1.close()
        
        # Get page 2 listings  
        print("\n=== PAGE 2 LISTINGS ===")
        page2, content2 = await client.get_page_with_retry(page2_url)
        listings2 = extractor.extract_listings_from_html(content2)
        print(f"Page 2: Found {len(listings2)} listings")
        
        if listings2:
            print("First 3 listings on page 2:")
            for i, listing in enumerate(listings2[:3]):
                print(f"  {i+1}. {listing.get('title', 'N/A')} - {listing.get('price', 'N/A')} - {listing.get('url', 'N/A')}")
        
        await page2.close()
        
        # Compare listings
        print("\n=== COMPARISON ===")
        if not listings1 and not listings2:
            print("Both pages returned no listings")
        elif not listings2:
            print("Page 2 returned no listings - might indicate end of results")
        elif listings1 and listings2:
            # Check if any listings are different
            urls1 = {listing.get('url', '') for listing in listings1}
            urls2 = {listing.get('url', '') for listing in listings2} 
            
            common = urls1 & urls2
            page1_only = urls1 - urls2
            page2_only = urls2 - urls1
            
            print(f"Common listings: {len(common)}")
            print(f"Page 1 only: {len(page1_only)}")  
            print(f"Page 2 only: {len(page2_only)}")
            
            if page2_only:
                print("SUCCESS: Page 2 has unique listings - pagination is working!")
            else:
                print("ISSUE: Page 2 shows same listings as Page 1")
        
if __name__ == "__main__":
    asyncio.run(compare_pages())