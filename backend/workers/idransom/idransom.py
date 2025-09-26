import os
import json
import logging
import datetime
import requests
from typing import Any, Dict, List
from supabase import create_client, Client
from gotrue.errors import AuthApiError
from dotenv import load_dotenv # <-- Add this line

# Load environment variables from .env file
load_dotenv() # <-- Add this line

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Supabase Credentials from Environment Variables ---
# Use os.environ.get() to safely retrieve environment variables.
# This prevents the function from crashing if a variable isn't set.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TABLE_NAME = os.environ.get("SUPABASE_TABLE_NAME", "idransom")

# --- Ransomware Live API Configuration ---
COUNTRY_CODE = os.environ.get("COUNTRY_CODE", "id")
HOURS_TO_FILTER = int(os.environ.get("HOURS_TO_FILTER", 60000))

def connect_to_supabase(url: str, key: str) -> Client:
    """
    Establishes a synchronous connection to a Supabase database.

    Args:
        url (str): The Supabase project URL.
        key (str): The Supabase 'anon' key.

    Returns:
        Client: A Supabase client object, or None if the connection fails.
    """
    try:
        # Create and return the Supabase client
        supabase_client: Client = create_client(url, key)
        print("Successfully connected to Supabase!")
        return supabase_client
    except AuthApiError as e:
        print(f"Authentication error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def filter_new_entries(supabase_client: Client, processed_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters a list of processed entries, returning only those not
    already present in the Supabase database based on a compound key.
    
    Checks by title, published_date, and url_source.
    
    Args:
        supabase_client: The Supabase client instance.
        processed_entries: A list of dictionaries representing new entries.
    
    Returns:
        List[Dict[str, Any]]: A list containing only the unique new entries.
    """
    if not processed_entries:
        return []

    existing_keys = set()
    
    try:
        # Fetch existing entries from the Supabase table, only selecting the key columns.
        response = supabase_client.from_(TABLE_NAME).select("title, published_date, url_source").execute()
        
        # Check if the response contains data and process it.
        if response.data:
            for entry in response.data:
                existing_keys.add((entry['title'], entry['published_date'], entry['url_source']))
                
    except AuthApiError as e:
        print(f"Authentication error: {e}. Please check your Supabase key.")
        return []
    except Exception as e:
        print(f"An error occurred while fetching existing entries: {e}")
        return []
        
    # Filter the new entries based on whether their key is in the existing set.
    unique_new_entries = [entry for entry in processed_entries if (entry['title'], entry['published_date'], entry['url_source']) not in existing_keys]
    
    return unique_new_entries
def insert_new_entries(supabase_client: Client, entries: List[Dict[str, Any]]):
    """
    Inserts a list of new entries into the Supabase database table.

    Args:
        supabase_client: The Supabase client instance.
        entries: A list of dictionaries representing new entries to insert.
    """
    if not entries:
        logger.info("No new entries to insert.")
        return

    try:
        response = supabase_client.from_(TABLE_NAME).insert(entries).execute()
        
        # Check if the insertion was successful
        if response.data:
            logger.info(f"Successfully inserted {len(response.data)} new entries into the database.")
        else:
            logger.error("Insertion failed. No data returned from Supabase.")
            
    except Exception as e:
        logger.error(f"An error occurred during insertion: {e}")


def grabber_ransomwarelive_country(country_code: str) -> List[Dict[str, Any]]:
    """
    Fetch victims for a given country code from the ransomware.live API.
    """
    url = f"https://api.ransomware.live/v2/countryvictims/{country_code}"
    try:
        logger.info("Fetching %s", url)
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        payload = resp.json()

        # Common response shapes: {"data": [...]}, [...] or { ... }
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
        else:
            data = payload

        if data is None:
            return []

        # Ensure we return a list of dicts
        if isinstance(data, dict):
            # Try to find an inner list value if returned as a dict
            # e.g. {"victims": [...]}
            for v in ("victims", "items", "results"): # heuristics
                if v in data and isinstance(data[v], list):
                    return data[v]
            return [data]

        if isinstance(data, list):
            return data

        # Unexpected type
        return []

    except requests.RequestException as e:
        logger.warning("Request failed: %s", e)
        return []
    except ValueError as e:
        logger.warning("Invalid JSON from API: %s", e)
        return []

def processor_ransomwarelive_country(
    entries: List[Dict[str, Any]], hours_to_filter: int
) -> List[Dict[str, Any]]:
    """
    Transform ransomware.live country victim entries and filter for the last X hours.

    Mappings:
    post_title -> title
    description -> description
    discovered -> discovered_date
    published -> published_date
    website -> website
    post_url -> url_source
    activity -> industry
    country -> country

    Any missing field will be returned as an empty string.
    """
    out: List[Dict[str, Any]] = []
    # Calculate the cutoff time
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=hours_to_filter
    )
    for e in entries:
        # Check if 'discovered' date is present and recent
        discovered_date_str = e.get("discovered")
        published_date_str = e.get("published")
        if discovered_date_str:
            try:
                # Assuming the 'discovered' date is in ISO 8601 format
                discovered_date = datetime.datetime.fromisoformat(discovered_date_str.replace('Z', '+00:00'))
                # Convert the discovered date to UTC for a consistent comparison.
                # If the date from the API is already in UTC, this will do nothing.
                discovered_date_utc = discovered_date.astimezone(datetime.timezone.utc)

                if discovered_date_utc >= cutoff_time:
                    # Format the published date to YYYY-MM-DD for consistent key comparison
                    if published_date_str:
                        published_date_obj = datetime.datetime.fromisoformat(published_date_str.replace('Z', '+00:00'))
                        published_date_formatted = published_date_obj.strftime('%Y-%m-%d')
                    else:
                        published_date_formatted = ""

                    out.append(
                        {
                            "title": e.get("post_title", "").strip(),
                            "description": e.get("description") or "",
                            "discovered_date": discovered_date_str,
                            "published_date": published_date_formatted,
                            "url_source": e.get("post_url") or "",
                            "website": e.get("website") or "",
                            "industry": e.get("activity") or "",
                            "country": e.get("country") or "",
                            "source": "ransomware.live",
                        }
                    )
            except ValueError as ve:
                logger.warning(
                    f"Could not parse date '{discovered_date_str}': {ve}. Skipping."
                )
                continue
    return out

def main():
    """
    Main function to run the script.
    """
    # Note: For production use, install dependencies with:
    # pip install -r requirements.txt
    
    # Establish the connection to Supabase
    supabase = connect_to_supabase(SUPABASE_URL, SUPABASE_KEY)

    if supabase:
        print(f"\nFetching and processing data from the ransomware.live API for country '{COUNTRY_CODE}'...")
        
        # Step 1: Grab raw data from the API
        raw_entries = grabber_ransomwarelive_country(COUNTRY_CODE)
        
        # Step 2: Process and filter the raw data (now with cleaned titles and dates)
        processed_entries = processor_ransomwarelive_country(raw_entries, HOURS_TO_FILTER)
        
        # Step 3: Filter for new entries not already in the database
        new_entries = filter_new_entries(supabase, processed_entries)

        # Step 4: Insert the unique new entries into the database
        insert_new_entries(supabase, new_entries)
        
        # Step 5: Print the non-existing entries that were just inserted (or would be)
        if new_entries:
            print(f"Found {len(new_entries)} unique new entries.")

        else:
            print("No new unique entries were found after processing and filtering.")

if __name__ == "__main__":
    main()
