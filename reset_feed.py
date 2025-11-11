#!/usr/bin/env python3

"""
Reset (clear all data from) Adafruit IO feeds
Usage:
  ./reset_feed.py enviro-temperature          # Reset one feed
  ./reset_feed.py enviro-temperature enviro-pressure  # Reset multiple feeds
  ./reset_feed.py all                         # Reset all feeds
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
    """Delete all data from a feed"""
    try:
        print(f"Resetting feed: {feed_name}")

        # Get all data from the feed
        data = aio.data(feed_name)

        if not data:
            print(f"  No data to delete in {feed_name}")
            return True

        print(f"  Found {len(data)} data points")

        # Delete each data point
        deleted = 0
        for point in data:
            try:
                aio.delete(feed_name, point.id)
                deleted += 1
            except Exception as e:
                print(f"  Error deleting data point: {e}")

        print(f"  Successfully deleted {deleted} data points from {feed_name}")
        return True

    except RequestError as e:
        if "404" in str(e):
            print(f"  Feed {feed_name} does not exist - skipping")
            return False
        else:
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
    response = input("Are you sure you want to delete all data from these feeds? (yes/no): ")
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
