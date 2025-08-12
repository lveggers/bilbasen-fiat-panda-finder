"""Extract listing data from Bilbasen JSON structure."""

import json
import re
from typing import List, Optional, Dict, Any
from ..logging_conf import get_logger
from ..models import ListingCreate

logger = get_logger("json_extractor")


class BilbasenJSONExtractor:
    """Extract car listing data from Bilbasen's Next.js JSON data."""

    def extract_listings_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract listing data from HTML containing Next.js JSON data.

        Args:
            html_content: HTML content from Bilbasen page

        Returns:
            List of listing dictionaries
        """
        try:
            # Find the Next.js data script tag
            script_pattern = (
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            )
            match = re.search(script_pattern, html_content, re.DOTALL)

            if not match:
                logger.warning("No __NEXT_DATA__ script found in HTML")
                return []

            json_str = match.group(1)
            data = json.loads(json_str)

            # Navigate to the listings data
            listings_data = self._extract_listings_from_data(data)

            logger.info(f"Extracted {len(listings_data)} listings from JSON data")
            return listings_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error extracting listings from HTML: {e}")
            return []

    def _extract_listings_from_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract listings from the parsed JSON data structure."""
        try:
            # Navigate through the Next.js data structure
            page_props = data.get("props", {}).get("pageProps", {})
            dehydrated_state = page_props.get("dehydratedState", {})
            queries = dehydrated_state.get("queries", [])

            listings = []

            # Find the query containing listings data
            for query in queries:
                query_data = query.get("state", {}).get("data", {})
                if "listings" in query_data:
                    raw_listings = query_data["listings"]

                    for listing_data in raw_listings:
                        normalized_listing = self._normalize_listing_data(listing_data)
                        if normalized_listing:
                            listings.append(normalized_listing)
                    break

            return listings

        except Exception as e:
            logger.error(f"Error navigating JSON data structure: {e}")
            return []

    def _normalize_listing_data(
        self, listing_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize a single listing from Bilbasen JSON format.

        Args:
            listing_data: Raw listing data from JSON

        Returns:
            Normalized listing dictionary or None if invalid
        """
        try:
            # Extract basic information
            external_id = listing_data.get("externalId")
            uri = listing_data.get("uri", "")
            make = listing_data.get("make", "")
            model = listing_data.get("model", "")
            variant = listing_data.get("variant", "")

            # Create title from make, model, and variant
            title_parts = [make, model, variant]
            title = " ".join(part for part in title_parts if part).strip()

            # Extract price information
            price_info = listing_data.get("price", {})
            price_dkk = price_info.get("price")

            # Extract location information
            location_info = listing_data.get("location", {})
            city = location_info.get("city", "")
            region = location_info.get("region", "")
            zip_code = location_info.get("zipCode", "")

            location_parts = (
                [str(zip_code), city, region] if zip_code else [city, region]
            )
            location = " ".join(part for part in location_parts if part).strip()

            # Extract properties
            properties = listing_data.get("properties", {})

            # First registration date (year)
            year = None
            if "firstregistrationdate" in properties:
                reg_date = properties["firstregistrationdate"].get(
                    "displayTextShort", ""
                )
                year_match = re.search(r"\b(19|20)\d{2}\b", reg_date)
                if year_match:
                    year = int(year_match.group())

            # Mileage (kilometers)
            kilometers = None
            if "mileage" in properties:
                mileage_text = properties["mileage"].get("displayTextShort", "")
                km_match = re.search(r"([\d.]+)", mileage_text.replace(".", ""))
                if km_match:
                    kilometers = int(km_match.group(1))

            # Fuel type
            fuel_type = None
            if "fueltype" in properties:
                fuel_type = properties["fueltype"].get("displayTextShort", "")

            # Transmission
            transmission = None
            if "geartype" in properties:
                transmission = properties["geartype"].get("displayTextShort", "")

            # Power (HP)
            power_hp = None
            if "hk" in properties:
                hp_text = properties["hk"].get("displayTextShort", "")
                hp_match = re.search(r"(\d+)", hp_text)
                if hp_match:
                    power_hp = int(hp_match.group(1))

            # Description
            description = listing_data.get("description", "")

            # Number of doors
            doors = listing_data.get("doors")

            normalized = {
                "external_id": external_id,
                "title": title or "Untitled Listing",
                "url": uri,
                "price_dkk": price_dkk,
                "year": year,
                "kilometers": kilometers,
                "brand": make,
                "model": model,
                "variant": variant,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "power_hp": power_hp,
                "doors": doors,
                "location": location,
                "description": description,
                "raw_data": listing_data,  # Keep raw data for debugging
            }

            return normalized

        except Exception as e:
            logger.warning(f"Error normalizing listing data: {e}")
            return None

    def create_listing_models(
        self, normalized_listings: List[Dict[str, Any]]
    ) -> List[ListingCreate]:
        """
        Convert normalized listing dictionaries to ListingCreate models.

        Args:
            normalized_listings: List of normalized listing dictionaries

        Returns:
            List of ListingCreate model instances
        """
        listing_models = []

        for listing_data in normalized_listings:
            try:
                # Parse condition from description if available
                condition_result = self._parse_condition_from_description(
                    listing_data.get("description", "")
                )

                listing_model = ListingCreate(
                    title=listing_data.get("title", ""),
                    url=listing_data.get("url", ""),
                    price_dkk=listing_data.get("price_dkk"),
                    year=listing_data.get("year"),
                    kilometers=listing_data.get("kilometers"),
                    condition_str=condition_result["label"],
                    condition_score=condition_result["score"],
                    brand=listing_data.get("brand"),
                    model=listing_data.get("model"),
                    fuel_type=listing_data.get("fuel_type"),
                    transmission=listing_data.get("transmission"),
                    body_type=None,  # Not directly available
                    location=listing_data.get("location"),
                    dealer_name=None,  # Would need to be extracted from detailed page
                )

                listing_models.append(listing_model)

            except Exception as e:
                logger.warning(f"Error creating ListingCreate model: {e}")
                continue

        logger.info(f"Created {len(listing_models)} ListingCreate models")
        return listing_models

    def _parse_condition_from_description(self, description: str) -> dict:
        """
        Parse condition score and label from description text.

        Args:
            description: Listing description text

        Returns:
            Dictionary with 'score' (0.0-1.0) and 'label' (string)
        """
        if not description:
            return {"score": 0.5, "label": "Ukendt"}  # Default neutral score

        description_lower = description.lower()

        # Good condition keywords with their labels
        good_keywords = {
            "topstand": "Topstand",
            "velholdt": "Velholdt",
            "nysynet": "Nysynet",
            "flot": "Flot stand",
            "pæn": "Pæn stand",
            "god stand": "God stand",
            "professionelt klargjort": "Professionelt klargjort",
            "klar til levering": "Klar til levering",
        }

        # Poor condition keywords with their labels
        poor_keywords = {
            "defekt": "Defekt",
            "reparationsobjekt": "Reparationsobjekt",
            "slidte": "Slidt",
            "skader": "Skader",
            "rust": "Rust",
            "problemer": "Problemer",
        }

        # Find the best matching keywords
        found_good = [
            label
            for keyword, label in good_keywords.items()
            if keyword in description_lower
        ]
        found_poor = [
            label
            for keyword, label in poor_keywords.items()
            if keyword in description_lower
        ]

        good_count = len(found_good)
        poor_count = len(found_poor)

        # Determine score
        if good_count > poor_count:
            score = min(1.0, 0.5 + (good_count - poor_count) * 0.1)
            label = found_good[0]  # Use the first good keyword found
        elif poor_count > good_count:
            score = max(0.0, 0.5 - (poor_count - good_count) * 0.1)
            label = found_poor[0]  # Use the first poor keyword found
        else:
            score = 0.5
            # If both good and poor found, use the first one, otherwise default
            if found_good:
                label = found_good[0]
            elif found_poor:
                label = found_poor[0]
            else:
                label = "Almindelig"  # Standard condition if no keywords found

        return {"score": score, "label": label}
