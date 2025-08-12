#!/usr/bin/env python3
"""Simple pagination test."""

import asyncio
from src.app.scraper.playwright_client import get_playwright_client

async def test_page_urls():
    """Test different page URLs to see if pagination works."""
    
    base_url = "https://www.bilbasen.dk/brugt/bil/fiat/panda?includeengroscvr=true&includeleasing=false"
    page2_url = f"{base_url}&page=2"
    
    print(f"Testing URLs:")
    print(f"  Page 1: {base_url}")
    print(f"  Page 2: {page2_url}")
    
    async with get_playwright_client() as client:
        # Test page 1
        print("\n--- Testing Page 1 ---")
        try:
            page, content = await client.get_page_with_retry(base_url)
            title = await page.title()
            listings_count = content.count('listing')  # Rough count
            print(f"Page 1 - Title: {title}")
            print(f"Page 1 - Listing mentions: {listings_count}")
            await page.close()
        except Exception as e:
            print(f"Error on page 1: {e}")
        
        # Test page 2 
        print("\n--- Testing Page 2 ---")
        try:
            page, content = await client.get_page_with_retry(page2_url)
            title = await page.title()
            listings_count = content.count('listing')  # Rough count
            
            # Check if we got redirected back to page 1
            current_url = page.url
            print(f"Page 2 - Current URL: {current_url}")
            print(f"Page 2 - Title: {title}")
            print(f"Page 2 - Listing mentions: {listings_count}")
            
            # Check if the URL contains page=2
            if "page=2" in current_url:
                print("SUCCESS: Page 2 URL structure works")
            else:
                print("NOTICE: Got redirected, probably no page 2 available")
                
            await page.close()
        except Exception as e:
            print(f"Error on page 2: {e}")

if __name__ == "__main__":
    asyncio.run(test_page_urls())