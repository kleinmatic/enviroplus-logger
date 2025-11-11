# Skills and Context for Enviro+ Logger Project

This document provides context for AI assistants (like Claude) to understand, extend, and troubleshoot this project.

## Project Overview

**Purpose**: Read environmental sensors from a Pimoroni Enviro+ HAT on a Raspberry Pi and publish the data to Adafruit IO for cloud monitoring and visualization.

**Platform**: Raspberry Pi Zero 2W (works on any Pi)
**Language**: Python 3
**Cloud Service**: Adafruit IO (free tier)

## Architecture

```
Raspberry Pi + Enviro+ HAT
    ↓
Python Script (publish_to_adafruit.py)
    ↓
Read Sensors → Format Data → Publish via MQTT/HTTP
    ↓
Adafruit IO Cloud
    ↓
Web Dashboard (viewable at io.adafruit.com)
```

## Hardware Components

### Pimoroni Enviro+ HAT
The Enviro+ is a sensor HAT for Raspberry Pi that includes:

1. **BME280** - Environmental sensor (I2C)
   - Temperature (Celsius)
   - Atmospheric pressure (hPa)
   - Relative humidity (%)

2. **LTR559** - Light/proximity sensor (I2C)
   - Ambient light (Lux)
   - IR proximity detection (0-65535)

3. **MICS6814** - Gas sensor (analog, via ADC)
   - Three channels measuring resistance in kΩ
   - Oxidising gases (NO2, O3, Cl2)
   - Reducing gases (CO, H2, CH4, H2S, ethanol)
   - NH3-type gases (NH3, H2S, alcohols)

4. **ST7735** - 0.96" LCD display (160x80, SPI)
   - Optional, not used in this project

5. **Analog Microphone** - MEMS microphone (ADC)
   - Optional, not used in this project

**Important**: This project does NOT use the PMS5003 particulate matter sensor (it's a separate add-on).

## Software Stack

### Dependencies
- **enviroplus** - Main library for Enviro+ HAT
- **bme280** - BME280 sensor driver
- **ltr559** - LTR559 sensor driver
- **smbus2** - I2C communication
- **Adafruit_IO** - Adafruit IO client library
- **python-dotenv** - Environment variable management

### Virtual Environment
Located at: `/home/kleinmatic/.virtualenvs/pimoroni`

Always activate before running:
```bash
source ~/.virtualenvs/pimoroni/bin/activate
```

## File Structure

```
enviroplus-logger/
├── publish_to_adafruit.py  # Main script (cron-friendly)
├── read_sensors.py          # Simple sensor test script
├── setup_adafruit.sh        # Dependency installer
├── .env                     # Credentials (NOT in git)
├── .env.example             # Template for credentials
├── .gitignore               # Git exclusions
├── README.md                # User documentation
├── SKILLS.md                # This file (AI context)
└── sensor_log.txt           # Runtime log (NOT in git)
```

## Key Design Decisions

### 1. Temperature Compensation
The BME280 sensor is heated by the Raspberry Pi CPU, causing temperature readings to be artificially high. The script includes optional CPU temperature compensation:

```python
comp_temp = raw_temp - ((cpu_temp - raw_temp) / factor)
```

- **Factor = 0**: Disabled (use raw reading)
- **Factor = 20**: Light compensation (recommended for Pi Zero 2W)
- **Factor = 2.25**: Heavy compensation (recommended for Pi 4)

For the Pi Zero 2W, raw readings are often most accurate (factor = 0).

### 2. Gas Sensor Readings
The MICS6814 measures **resistance**, not concentration:
- **Higher resistance (kΩ)** = Cleaner air
- **Lower resistance** = Gas detected

These are **relative measurements**. You must:
1. Establish a baseline in clean air
2. Monitor for changes/drops over time
3. Understand that sensors detect **classes of gases**, not individual gases

Warm-up time: 10-48 hours for stable readings.

### 3. Feed Auto-Creation
The script automatically creates Adafruit IO feeds on first run if they don't exist. This simplifies setup but means feeds appear with default settings.

### 4. Cron Scheduling
Designed to run via cron (non-interactive):
- Logs to file: `sensor_log.txt`
- Also outputs to stdout for debugging
- Handles rate limiting (30 data points/min on free tier)
- Recommended interval: Every 5 minutes

## Common Tasks

### Adding a New Sensor
1. Import the sensor library in `publish_to_adafruit.py`
2. Add sensor initialization in `read_sensors()`
3. Read the sensor value and add to `sensors` dict
4. Add feed mapping in `publish_to_adafruit()`
5. Update README sensor documentation

### Changing Feed Names
Edit the `feed_mapping` dict in `publish_to_adafruit()`:
```python
feed_mapping = {
    'temperature': 'enviro-temperature',  # Change right side
    ...
}
```

### Adjusting Temperature Compensation
Edit `.env` file:
```
TEMP_COMPENSATION_FACTOR=0    # Disabled
TEMP_COMPENSATION_FACTOR=10   # Light
TEMP_COMPENSATION_FACTOR=20   # Very light
```

### Debugging
1. Check logs: `tail -f sensor_log.txt`
2. Run manually: `python3 publish_to_adafruit.py`
3. Test sensors: `python3 read_sensors.py`
4. Check Adafruit IO: https://io.adafruit.com

## Troubleshooting Guide

### Error: "Module not found: enviroplus"
- Virtual environment not activated
- Solution: `source ~/.virtualenvs/pimoroni/bin/activate`

### Error: "Adafruit IO credentials not configured"
- `.env` file missing or incorrect
- Solution: Check `.env` file exists and has correct credentials

### Error: "404 Not Found" from Adafruit IO
- This is normal on first run - script auto-creates feeds
- If persists, check username is correct (case-sensitive)

### Error: "429 Rate Limit" from Adafruit IO
- Publishing too frequently
- Free tier: 30 data points/minute max
- With 8 sensors, run at most every 2 minutes
- Solution: Reduce cron frequency

### Temperature Readings Too High/Low
- CPU heating the sensor OR over-compensation
- Solution: Adjust `TEMP_COMPENSATION_FACTOR` in `.env`
- For Pi Zero 2W, try factor = 0 (disabled)

### Gas Sensor Values Seem Wrong
- Gas sensors measure resistance, not concentration
- Need 10-48 hour warm-up for stable readings
- Establish baseline first, then watch for changes
- Affected by temperature and humidity

### PMS5003 Errors
- This project doesn't use the particulate sensor
- If you have one installed, uncomment PMS5003 code
- Otherwise, ignore these errors

## Security Considerations

### Sensitive Data
- **Adafruit IO credentials**: Stored in `.env` (excluded from git)
- **Log files**: May contain sensor data (excluded from git)
- **No PII**: Project doesn't collect personal information

### Rate Limiting
- Adafruit IO free tier has rate limits
- Script handles 429 errors with exponential backoff
- Logs should not contain credentials

### Network Security
- HTTPS for API calls (handled by Adafruit_IO library)
- No local web server or open ports
- Outbound connections only

## Migration to Home Assistant

When ready to self-host with Home Assistant:

1. Set up MQTT broker (Mosquitto)
2. Replace `publish_to_adafruit()` with MQTT publish
3. Use same sensor reading code
4. Home Assistant auto-discovers MQTT sensors

The architecture is designed for easy migration - just swap the publish function.

## Development Notes

### Testing Changes
1. Always test manually before setting up cron
2. Check both stdout and log file output
3. Verify data appears correctly in Adafruit IO
4. Test with invalid credentials to verify error handling

### Code Style
- Python 3 standard library preferred
- Type hints not used (for simplicity)
- Logging for all major operations
- Exception handling for all I/O

### Future Enhancements
- [ ] Add display output (LCD) option
- [ ] Add noise level monitoring (microphone)
- [ ] Add local SQLite caching for offline resilience
- [ ] Add Home Assistant MQTT mode
- [ ] Add air quality index calculation
- [ ] Add email/SMS alerts for threshold breaches

## Useful References

- [Pimoroni Enviro+ GitHub](https://github.com/pimoroni/enviroplus-python)
- [Adafruit IO Documentation](https://io.adafruit.com/api/docs)
- [BME280 Datasheet](https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/)
- [MICS6814 Datasheet](https://www.sgxsensortech.com/content/uploads/2015/02/1143_Datasheet-MiCS-6814-rev-8.pdf)

## Version History

- **v1.0** (2025-01): Initial release
  - Basic sensor reading
  - Adafruit IO publishing
  - Temperature compensation
  - Auto feed creation
  - Cron-friendly logging
