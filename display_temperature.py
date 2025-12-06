#!/usr/bin/env python3

"""
Display temperature readings on the Enviro+ LCD screen
Shows both raw and compensated temperature for calibration
Press Ctrl+C to exit
"""

import time
from bme280 import BME280
from smbus2 import SMBus
from PIL import Image, ImageDraw, ImageFont
import st7735

# Initialize display
disp = st7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)

# Initialize display
disp.begin()

# Display dimensions
WIDTH = disp.width
HEIGHT = disp.height

# Initialize BME280 sensor
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

# Load environment variables for temperature compensation factor
try:
    from dotenv import load_dotenv
    from pathlib import Path
    import os
    script_dir = Path(__file__).parent.absolute()
    env_path = script_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    TEMP_COMPENSATION_FACTOR = float(os.getenv('TEMP_COMPENSATION_FACTOR', '0'))
except:
    TEMP_COMPENSATION_FACTOR = 0


def get_cpu_temperature():
    """Get CPU temperature for BME280 compensation"""
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
    return temp


def main():
    print("Starting temperature display...")
    print("Press Ctrl+C to exit")

    # Try to load a font
    try:
        # Large font for single compensated temperature
        font_temp = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        print("Warning: Could not load TrueType font, using default")
        font_temp = ImageFont.load_default()

    # Rolling average - keep last 10 readings (20 seconds)
    temp_readings = []
    max_readings = 10

    try:
        while True:
            # Discard first reading (BME280 returns stale data)
            _ = bme280.get_temperature()
            time.sleep(0.1)

            # Get readings
            cpu_temp = get_cpu_temperature()
            raw_temp = bme280.get_temperature()

            # Calculate compensated temperature
            if TEMP_COMPENSATION_FACTOR > 0:
                compensation_amount = (cpu_temp - raw_temp) / TEMP_COMPENSATION_FACTOR
                comp_temp = raw_temp - compensation_amount
            else:
                comp_temp = raw_temp

            # Add to rolling average
            temp_readings.append(comp_temp)
            if len(temp_readings) > max_readings:
                temp_readings.pop(0)  # Remove oldest

            # Calculate average
            avg_temp = sum(temp_readings) / len(temp_readings)

            # Create blank image
            img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Just compensated temperature - large and centered
            y_pos = 20  # Centered vertically

            # Averaged compensated temperature (green) - large
            draw.text((10, y_pos), f"{avg_temp:.1f}°C", font=font_temp, fill=(100, 255, 100))

            # Display image
            disp.display(img)

            # Also print to console
            print(f"\rRaw: {raw_temp:.1f}°C | Comp: {comp_temp:.1f}°C | Avg: {avg_temp:.1f}°C | CPU: {cpu_temp:.1f}°C", end="", flush=True)

            # Update every 10 seconds
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nExiting...")
        # Clear display
        img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
        disp.display(img)


if __name__ == "__main__":
    main()
