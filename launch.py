#!/usr/bin/env python3
"""
Bilbasen Fiat Panda Finder - One-command launcher
Scrapes data, updates scoring, and launches the web application.
"""

import asyncio
import sys
import subprocess
from pathlib import Path

# Ensure we're in the right directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.app.logging_conf import get_logger
from src.app.db import create_db_and_tables, engine, ListingCRUD
from src.app.scraper.scraper import scrape_bilbasen_listings
from src.app.api import rescore_all_listings
from sqlmodel import Session

logger = get_logger("launcher")

async def main():
    """Main launcher function."""
    print("Bilbasen Fiat Panda Finder - Launcher")
    print("=" * 50)
    
    try:
        # 1. Initialize database
        print("[1/5] Initializing database...")
        create_db_and_tables()
        logger.info("Database initialized")
        
        # 2. Scrape fresh data
        print("[2/5] Scraping fresh car listings...")
        listings = await scrape_bilbasen_listings(max_pages=1, use_json=True)
        print(f"[OK] Scraped {len(listings)} listings")
        
        # 3. Store in database
        print("[3/5] Storing listings in database...")
        session = Session(engine)
        try:
            stored_count = 0
            updated_count = 0
            
            for listing in listings:
                # Check if listing exists by URL
                existing = ListingCRUD.get_listing_by_url(session, listing.url)
                if existing:
                    # Update the existing listing
                    for field, value in listing.model_dump(exclude={'id'}).items():
                        if value is not None:  # Only update non-None values
                            setattr(existing, field, value)
                    updated_count += 1
                else:
                    # Create new listing
                    try:
                        ListingCRUD.create_listing(session, listing)
                        stored_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to create listing {listing.url}: {e}")
                        continue
                        
            session.commit()
            print(f"[OK] Stored {stored_count} new listings, updated {updated_count} existing")
            
            # 4. Update scoring
            print("[4/5] Updating scores...")
            rescored_count = await rescore_all_listings(session)
            print(f"[OK] Rescored {rescored_count} listings")
            
        finally:
            session.close()
        
        # 5. Launch web server
        print("\n[5/5] Launching web application...")
        print("Server will be available at: http://127.0.0.1:8001")
        print("Use Ctrl+C to stop the server")
        print("-" * 50)
        
        # Launch uvicorn server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "src.app.server:app", 
            "--host", "127.0.0.1", 
            "--port", "8001", 
            "--reload"
        ], cwd=project_root)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"ERROR: {e}")
        logger.error(f"Launcher error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())