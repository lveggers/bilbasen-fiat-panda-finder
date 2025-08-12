#!/usr/bin/env python3
"""Test the fixed pagination logic."""

import asyncio
from src.app.scraper.scraper import scrape_bilbasen_listings

async def test_fixed_pagination():
    print('Testing fixed pagination with max_pages=5...')
    listings = await scrape_bilbasen_listings(max_pages=5, use_json=True)
    print(f'Total listings found: {len(listings)}')
    
    # Show unique URLs to verify no duplicates
    urls = {listing.url for listing in listings}
    print(f'Unique URLs: {len(urls)}')
    
    if len(urls) != len(listings):
        print('WARNING: Found duplicate listings!')
    else:
        print('SUCCESS: All listings are unique')

if __name__ == "__main__":
    asyncio.run(test_fixed_pagination())