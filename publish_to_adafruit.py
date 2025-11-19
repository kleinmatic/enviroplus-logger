#!/usr/bin/env python3

"""
Publish Enviro+ sensor readings to Adafruit IO and Home Assistant
Designed to be run via cron
"""

import sys
import os
import time
import logging
import json
from pathlib import Path
from datetime import datetime
from bme280 import BME280
from smbus2 import SMBus

try:
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

from enviroplus import gas
from Adafruit_IO import Client, RequestError
import paho.mqtt.client as mqtt

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    env_path = script_dir / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    logging.warning("python-dotenv not installed. Install with: pip install python-dotenv")
    logging.warning("Falling back to environment variables only")

# Configure logging for cron
# Log to the same directory as this script
script_dir = Path(__file__).parent.absolute()
log_file = script_dir / 'sensor_log.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# ============================================
# CONFIGURATION - Load from environment variables
# ============================================

# Publishing control flags (default both to true)
ENABLE_ADAFRUIT_IO = os.getenv('ENABLE_ADAFRUIT_IO', 'true').lower() == 'true'
ENABLE_HOMEASSISTANT = os.getenv('ENABLE_HOMEASSISTANT', 'true').lower() == 'true'

# Adafruit IO Configuration
ADAFRUIT_IO_USERNAME = os.getenv('ADAFRUIT_IO_USERNAME')
ADAFRUIT_IO_KEY = os.getenv('ADAFRUIT_IO_KEY')

# Home Assistant MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', 'homeassistant.local')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')

# Temperature compensation factor (set to 0 to disable)
TEMP_COMPENSATION_FACTOR = float(os.getenv('TEMP_COMPENSATION_FACTOR', '0'))


def get_cpu_temperature():
    """Get CPU temperature for BME280 compensation"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = f.read()
            temp = int(temp) / 1000.0
        return temp
    except Exception as e:
        logging.error(f"Failed to read CPU temperature: {e}")
        return None


def read_sensors():
    """Read all sensor values and return as dict"""
    sensors = {}

    try:
        # Initialize sensors
        bus = SMBus(1)
        bme280 = BME280(i2c_dev=bus)

        # Discard first reading (BME280 returns stale data on first read)
        _ = bme280.get_temperature()
        _ = bme280.get_pressure()
        _ = bme280.get_humidity()
        time.sleep(0.1)  # Brief delay for sensor stabilization

        # Temperature with compensation
        cpu_temp = get_cpu_temperature()
        raw_temp = bme280.get_temperature()

        if cpu_temp and TEMP_COMPENSATION_FACTOR > 0:
            compensation = (cpu_temp - raw_temp) / TEMP_COMPENSATION_FACTOR
            sensors['temperature'] = round(raw_temp - compensation, 2)
        else:
            sensors['temperature'] = round(raw_temp, 2)

        # Pressure and Humidity
        sensors['pressure'] = round(bme280.get_pressure(), 2)
        sensors['humidity'] = round(bme280.get_humidity(), 2)

        # Light and Proximity
        sensors['light'] = round(ltr559.get_lux(), 2)
        sensors['proximity'] = round(ltr559.get_proximity(), 2)

        # Gas sensors
        gas_data = gas.read_all()
        sensors['oxidising'] = round(gas_data.oxidising / 1000, 2)
        sensors['reducing'] = round(gas_data.reducing / 1000, 2)
        sensors['nh3'] = round(gas_data.nh3 / 1000, 2)

        logging.info(f"Successfully read all sensors")
        return sensors

    except Exception as e:
        logging.error(f"Error reading sensors: {e}")
        return None


def publish_to_adafruit(sensors):
    """Publish sensor data to Adafruit IO"""

    # Check credentials
    if not ADAFRUIT_IO_USERNAME or not ADAFRUIT_IO_KEY:
        logging.error("Adafruit IO credentials not configured!")
        logging.error("Create a .env file with ADAFRUIT_IO_USERNAME and ADAFRUIT_IO_KEY")
        logging.error("See .env.example for template")
        return False

    try:
        # Create Adafruit IO client
        aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

        # Publish each sensor to its own feed
        feed_mapping = {
            'temperature': 'enviro-temperature',
            'pressure': 'enviro-pressure',
            'humidity': 'enviro-humidity',
            'light': 'enviro-light',
            'proximity': 'enviro-proximity',
            'oxidising': 'enviro-oxidising',
            'reducing': 'enviro-reducing',
            'nh3': 'enviro-nh3'
        }

        for sensor, feed_name in feed_mapping.items():
            if sensor in sensors:
                try:
                    aio.send_data(feed_name, sensors[sensor])
                    logging.info(f"Published {sensor}: {sensors[sensor]} to {feed_name}")
                    # Small delay to avoid rate limiting
                    time.sleep(0.5)
                except RequestError as e:
                    # Check if feed doesn't exist (404)
                    if "404" in str(e) or "not found" in str(e).lower():
                        logging.info(f"Feed {feed_name} doesn't exist, creating it...")
                        try:
                            # Create the feed
                            from Adafruit_IO import Feed
                            new_feed = Feed(name=feed_name)
                            aio.create_feed(new_feed)
                            logging.info(f"Created feed {feed_name}")
                            time.sleep(0.5)
                            # Now send the data
                            aio.send_data(feed_name, sensors[sensor])
                            logging.info(f"Published {sensor}: {sensors[sensor]} to {feed_name}")
                        except Exception as create_error:
                            logging.error(f"Failed to create/publish {sensor}: {create_error}")
                    # Check if it's a rate limit error (429)
                    elif "429" in str(e) or "throttle" in str(e).lower():
                        logging.warning(f"Rate limited - waiting 30 seconds")
                        time.sleep(30)
                        try:
                            aio.send_data(feed_name, sensors[sensor])
                        except Exception as retry_error:
                            logging.error(f"Failed to publish {sensor} after retry: {retry_error}")
                    else:
                        logging.error(f"Failed to publish {sensor}: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error publishing {sensor}: {e}")

        logging.info("Successfully published all data to Adafruit IO")
        return True

    except Exception as e:
        logging.error(f"Error publishing to Adafruit IO: {e}")
        return False


def publish_to_homeassistant(sensors):
    """Publish sensor data to Home Assistant via MQTT with auto-discovery"""

    # Check if MQTT is configured
    if not MQTT_USERNAME or not MQTT_PASSWORD:
        logging.info("MQTT credentials not configured - skipping Home Assistant publishing")
        return True

    try:
        # Create MQTT client
        client = mqtt.Client(client_id="enviroplus", protocol=mqtt.MQTTv5)
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        # Connect to broker
        logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        # Give connection time to establish
        time.sleep(1)

        # Define sensor configurations for MQTT Discovery
        sensor_configs = {
            'temperature': {
                'name': 'Enviro+ Temperature',
                'unit': '°C',
                'device_class': 'temperature',
                'icon': 'mdi:thermometer'
            },
            'pressure': {
                'name': 'Enviro+ Pressure',
                'unit': 'hPa',
                'device_class': 'atmospheric_pressure',
                'icon': 'mdi:gauge'
            },
            'humidity': {
                'name': 'Enviro+ Humidity',
                'unit': '%',
                'device_class': 'humidity',
                'icon': 'mdi:water-percent'
            },
            'light': {
                'name': 'Enviro+ Light Level',
                'unit': 'lx',
                'device_class': 'illuminance',
                'icon': 'mdi:brightness-5'
            },
            'proximity': {
                'name': 'Enviro+ Proximity',
                'unit': '',
                'icon': 'mdi:hand-wave'
            },
            'oxidising': {
                'name': 'Enviro+ Oxidising',
                'unit': 'kΩ',
                'icon': 'mdi:molecule'
            },
            'reducing': {
                'name': 'Enviro+ Reducing',
                'unit': 'kΩ',
                'icon': 'mdi:molecule'
            },
            'nh3': {
                'name': 'Enviro+ NH3',
                'unit': 'kΩ',
                'icon': 'mdi:molecule'
            }
        }

        # Device information (groups all sensors together in HA)
        device_info = {
            'identifiers': ['enviroplus_sensor'],
            'name': 'Enviro+ Sensor',
            'model': 'Pimoroni Enviro+',
            'manufacturer': 'Pimoroni'
        }

        # Publish discovery configs and sensor values
        for sensor_key, sensor_value in sensors.items():
            if sensor_key in sensor_configs:
                config = sensor_configs[sensor_key]

                # MQTT Discovery configuration
                discovery_topic = f"homeassistant/sensor/enviroplus/{sensor_key}/config"
                state_topic = f"homeassistant/sensor/enviroplus/{sensor_key}/state"

                discovery_payload = {
                    'name': config['name'],
                    'state_topic': state_topic,
                    'unique_id': f'enviroplus_{sensor_key}',
                    'device': device_info,
                    'icon': config['icon']
                }

                # Add unit and device_class if present
                if config.get('unit'):
                    discovery_payload['unit_of_measurement'] = config['unit']
                if config.get('device_class'):
                    discovery_payload['device_class'] = config['device_class']

                # Publish discovery config
                client.publish(discovery_topic, json.dumps(discovery_payload), qos=1, retain=True)
                logging.info(f"Published MQTT discovery for {sensor_key}")

                # Publish sensor value
                client.publish(state_topic, str(sensor_value), qos=1, retain=True)
                logging.info(f"Published {sensor_key}: {sensor_value} to Home Assistant")

                # Small delay to avoid overwhelming the broker
                time.sleep(0.2)

        # Clean disconnect
        time.sleep(1)
        client.loop_stop()
        client.disconnect()

        logging.info("Successfully published all data to Home Assistant")
        return True

    except Exception as e:
        logging.error(f"Error publishing to Home Assistant: {e}")
        return False


def main():
    logging.info("=" * 60)
    logging.info("Starting Enviro+ sensor read and publish")

    # Log which services are enabled
    services_enabled = []
    if ENABLE_ADAFRUIT_IO:
        services_enabled.append("Adafruit IO")
    if ENABLE_HOMEASSISTANT:
        services_enabled.append("Home Assistant")

    if not services_enabled:
        logging.error("No publishing services enabled! Check ENABLE_ADAFRUIT_IO and ENABLE_HOMEASSISTANT in .env")
        sys.exit(1)

    logging.info(f"Publishing enabled for: {', '.join(services_enabled)}")

    # Read sensors
    sensors = read_sensors()
    if not sensors:
        logging.error("Failed to read sensors - aborting")
        sys.exit(1)

    # Publish to enabled services
    adafruit_success = True  # Default to success if disabled
    homeassistant_success = True  # Default to success if disabled

    if ENABLE_ADAFRUIT_IO:
        adafruit_success = publish_to_adafruit(sensors)
    else:
        logging.info("Adafruit IO publishing disabled - skipping")

    if ENABLE_HOMEASSISTANT:
        homeassistant_success = publish_to_homeassistant(sensors)
    else:
        logging.info("Home Assistant publishing disabled - skipping")

    # Consider it a success if all enabled services worked
    if adafruit_success and homeassistant_success:
        logging.info("Sensor reading and publishing completed successfully")
        sys.exit(0)
    else:
        logging.error("Failed to publish data to one or more enabled services")
        sys.exit(1)


if __name__ == "__main__":
    main()
