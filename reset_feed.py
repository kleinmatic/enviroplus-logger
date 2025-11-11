#!/usr/bin/env python3

"""
Reset (clear all data from) Adafruit IO feeds by deleting and recreating them
Usage:
  ./reset_feed.py enviro-temperature          # Reset one feed
  ./reset_feed.py enviro-temperature enviro-pressure  # Reset multiple feeds
  ./reset_feed.py all                         # Reset all feeds

Note: This deletes the entire feed and recreates it (faster than deleting
individual data points which can trigger rate limiting).
"""

import sys
import os
from pathlib import Path
from Adafruit_IO import Client, RequestError

try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent.absolute()
    env_path = script_dir / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    print("Warning: python-dotenv not installed")

# Load credentials
ADAFRUIT_IO_USERNAME = os.getenv('ADAFRUIT_IO_USERNAME')
ADAFRUIT_IO_KEY = os.getenv('ADAFRUIT_IO_KEY')

# All feed names used by this project
ALL_FEEDS = [
    'enviro-temperature',
    'enviro-pressure',
    'enviro-humidity',
    'enviro-light',
    'enviro-proximity',
    'enviro-oxidising',
    'enviro-reducing',
    'enviro-nh3'
]


def reset_feed(aio, feed_name):
    """Reset a feed by deleting and recreating it"""
    try:
        print(f"Resetting feed: {feed_name}")

        # Check if feed exists
        try:
            feed = aio.feeds(feed_name)
            print(f"  Feed exists, deleting...")
        except RequestError as e:
            if "404" in str(e):
                print(f"  Feed {feed_name} does not exist - nothing to reset")
                return False
            else:
                raise

        # Delete the feed (this deletes all data too)
        aio.delete_feed(feed_name)
        print(f"  Deleted feed {feed_name}")

        # Recreate the feed
        from Adafruit_IO import Feed
        new_feed = Feed(name=feed_name)
        aio.create_feed(new_feed)
        print(f"  Recreated feed {feed_name} (empty)")

        return True

    except RequestError as e:
        print(f"  Error resetting {feed_name}: {e}")
        return False
    except Exception as e:
        print(f"  Unexpected error: {e}")
        return False


def main():
    # Check credentials
    if not ADAFRUIT_IO_USERNAME or not ADAFRUIT_IO_KEY:
        print("Error: Adafruit IO credentials not configured!")
        print("Make sure .env file exists with ADAFRUIT_IO_USERNAME and ADAFRUIT_IO_KEY")
        sys.exit(1)

    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: ./reset_feed.py <feed-name> [feed-name2 ...]")
        print("       ./reset_feed.py all")
        print("")
        print("Available feeds:")
        for feed in ALL_FEEDS:
            print(f"  - {feed}")
        sys.exit(1)

    # Create Adafruit IO client
    aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

    # Determine which feeds to reset
    if sys.argv[1] == "all":
        feeds_to_reset = ALL_FEEDS
        print(f"Resetting ALL feeds ({len(ALL_FEEDS)} total)\n")
    else:
        feeds_to_reset = sys.argv[1:]
        print(f"Resetting {len(feeds_to_reset)} feed(s)\n")

    # Confirm with user
    print("WARNING: This will DELETE and RECREATE the feeds, removing all data.")
    print("The feeds will be empty after this operation.")
    response = input("Are you sure you want to proceed? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled")
        sys.exit(0)

    print("")

    # Reset each feed
    success_count = 0
    for feed_name in feeds_to_reset:
        if reset_feed(aio, feed_name):
            success_count += 1
        print("")

    print(f"Complete! Successfully reset {success_count} of {len(feeds_to_reset)} feeds")


if __name__ == "__main__":
    main()
