# Enviroplus Logger - Project Documentation

This is a Raspberry Pi Zero 2W with Pimoroni Enviro+ HAT that monitors environmental sensors and publishes to Adafruit IO and Home Assistant.

## Quick Start

When you start working in this directory:

1. Read this entire file (CLAUDE.md) - it contains everything you need
2. Check the git log for recent changes
3. Review Active Issues section below for current problems
4. **Read README.md** to understand what users expect - it's the human-facing documentation
   - Keep README.md updated when commands, setup steps, or sensor configurations change
   - README.md is for humans, CLAUDE.md is for AI agents

## Active Issues

### Issue #1: Light Sensor Reading ~1/15th of Expected Values

**Status**: ACTIVE - Hardware failure confirmed, awaiting replacement
**Date Identified**: 2025-11-19 04:30 UTC
**Date Started**: After device move on 2025-11-16 22:32 UTC
**Final Diagnosis**: 2025-11-19 14:37 UTC - Visible light photodiode failure

#### Symptoms

1. Light sensor (LTR559) reads extremely low values
2. Kitchen lights on + flashlight 2-3 inches away = only ~26-30 lux
3. Should be reading 500-5000+ lux with flashlight
4. Historical data shows sensor was reading 50-465 lux normally before move

#### Diagnosis

**Visible light photodiode in LTR559 has failed. IR photodiode still functional.**

Confirmed via comprehensive testing on 2025-11-19:

**Power System: ✓ HEALTHY**
- `vcgencmd get_throttled` = 0x0 (no undervoltage, ever)
- Core voltage: 1.2625V (normal)
- CPU temp: 48.3°C, Clock: 1000 MHz (full speed)
- Tested with different power outlet/charger: no change
- Conclusion: Power is NOT the issue

**I2C Communication: ✓ PERFECT**
- LTR559 detected at address 0x23
- Part ID: 0x92 ✓, Manufacturer ID: 0x05 ✓
- Register reads/writes working normally

**Light Sensor Performance: ✗ VISIBLE PHOTODIODE FAILED**

Bright flashlight test at gain=96x, 400ms integration:
```
With flashlight (1-2 inches away):
  CH0 (visible+IR): ~1500
  CH1 (IR only):    ~1530
  Lux: ~8.9

Expected with flashlight at this sensitivity:
  CH0: 20,000-50,000+
  CH1: < CH0 (much lower)
  Lux: 500-5000+
```

**Smoking gun: CH1 ≥ CH0**

In normal operation, CH0 (visible+IR) should be **much higher** than CH1 (IR only) when detecting visible light. The fact that CH1 ≥ CH0 proves the visible light photodiode is non-functional while the IR photodiode still works (proximity detection confirms this).

**Other Sensors: ✓ ALL WORKING NORMALLY**
- BME280 (temp/pressure/humidity): OK
- MICS6814 (gas sensors): OK
- Proximity sensor (IR): OK

The massive drop in sensitivity (~95% reduction) after the physical move, combined with CH0≈CH1, confirms physical damage to the LTR559 visible light photodiode during the move.

#### Resolution Options

**1. Replace the Enviro+ HAT** (~$55-65 USD)
   - Restores full functionality
   - All sensors working again

**2. Continue with broken light sensor**
   - All other sensors work fine (temp, humidity, pressure, gas, proximity)
   - Accept inaccurate light readings (~8.9 lux always)
   - Could disable light sensor publishing to avoid bad data

**3. Workaround: Use high-gain multiplier**
   - Multiply readings by ~100-150x as a crude calibration
   - Won't be accurate but might track relative changes
   - Not recommended for precision

**Current Status**: Awaiting response from PiShop.US regarding replacement.

---

### Issue #2: Gas Sensor "First Reading Discard" Misdiagnosis

**Status**: RESOLVED ✓ (Reverted incorrect fix)
**Date Identified**: 2025-11-19 04:00 UTC
**Date "Fixed"**: 2025-11-19 14:37 UTC
**Date Actually Fixed**: 2025-11-19 21:50 UTC

#### Root Cause: MISDIAGNOSIS - Gas sensors work correctly WITHOUT first reading discard

The MICS6814 gas sensor does **NOT** have a stale first reading problem like the BME280. Applying the BME280 fix to gas sensors was a mistake that broke the readings.

#### What Happened

1. Reducing sensor showed repetitive values (6104.0/6788.44 kΩ)
2. Assumed this was a "stale reading bug" like BME280
3. Applied "discard first reading" fix at 14:37
4. **All three gas sensors immediately dropped 88-98%**:
   - Oxidising: 489-906 kΩ → 9-18 kΩ (98% drop)
   - Reducing: 6104 kΩ → 245-354 kΩ (94% drop)
   - NH3: 1900-4300 kΩ → 96-255 kΩ (95% drop)

#### Actual Root Cause

The repetitive values **were correct**. The indoor air quality was simply stable, causing consistent readings. This is normal sensor behavior.

#### Correct Fix

**Removed** the first reading discard for MICS6814. Gas sensors should be read directly:

```python
# Gas sensors - read directly (NO first reading discard needed)
gas_data = gas.read_all()
```

#### Verification After Revert

Gas sensors returned to normal values matching historical data:
- Oxidising: 374.77 kΩ ✓
- Reducing: 6104.00 kΩ ✓
- NH3: 1810.67 kΩ ✓

#### Key Lesson

**Only BME280 requires first reading discard:**
- ✓ BME280 (temperature/pressure/humidity) - REQUIRES discard
- ✗ MICS6814 (gas sensors) - NO discard needed
- ? LTR559 (light/proximity) - Unknown (I2C, probably no discard needed)

---

## Development Rules & Best Practices

### Hardware Constraints - Raspberry Pi Zero 2W

#### MicroSD Card Longevity
- **NEVER add logging to production code** - This project runs on a Raspberry Pi Zero with a microSD card
- Excessive writes reduce microSD card lifespan
- The current logging in `publish_to_adafruit.py` is acceptable but should not be expanded
- If debugging is needed, use temporary print statements and remove them before committing
- Consider suggesting in-memory logging or syslog for any new logging requirements

#### Performance Considerations
- Pi Zero 2W has limited CPU and RAM
- Keep sensor reading code lightweight
- Avoid adding heavy dependencies
- Test performance impact of any new libraries

### Sensor Code Modifications

#### BME280 (Temperature/Pressure/Humidity)
- **ALWAYS discard first reading** - BME280 returns stale data on first read
- Include 0.1 second delay after discarding first reading for sensor stabilization
- When modifying temperature compensation:
  - Test with factor=0 (disabled), factor=10, and factor=20
  - Document the tested values in commit message
  - RUN `read_sensors.py` manually to verify compensation math
- **Temperature Calibration Tool**: Use `display_temperature.py` for calibration
  - Displays compensated temperature on LCD screen with rolling average (10 readings over 100 seconds)
  - Updates every 10 seconds for stable readings
  - Compare displayed value against reference thermometer
  - Current calibration: factor=1.43 for vertical wall mounting (Dec 2025)
  - Mounting orientation affects heat dissipation and requires recalibration

#### MICS6814 (Gas Sensors)
- **DO NOT discard first reading** - Unlike BME280, gas sensors work correctly on first read
- Gas sensors need 10-48 hour warm-up period for stable readings
- **Test any changes over a 10+ minute period** minimum
- Remember: readings are resistance values, not concentrations
- Lower resistance = gas detected, higher resistance = cleaner air
- Never add "concentration" calculations without proper calibration
- Repetitive values are normal when air quality is stable

#### General Sensor Rules
- Always test with `read_sensors.py` before modifying `publish_to_adafruit.py`
- Only BME280 requires "discard first reading" pattern
- Keep sensor reading code in a try/except block
- Log sensor errors but continue execution when possible

### Security Requirements

#### Credentials
- **NEVER hardcode credentials** - Always use environment variables
- Always load from `.env` file using python-dotenv
- Verify `.env` is in `.gitignore` before committing
- When adding new credentials, update `.env.example` with placeholder values

#### Secrets in Code
- No API keys, tokens, or passwords in any tracked files
- No IP addresses or personal information in comments or documentation
- Check that sensitive files remain in `.gitignore`

### Before Committing

1. **Test hardware**: Run `read_sensors.py` to verify sensors still work
2. **Security check**: Confirm `.env` is still in `.gitignore`
3. **Documentation**:
   - Update CLAUDE.md if architecture or design decisions changed
   - **Update README.md** if user-facing setup/usage changed (commands, configuration, sensor list, troubleshooting)
   - Keep README.md and CLAUDE.md in sync where they overlap
4. **Logging**: Ensure no new excessive logging was added (microSD longevity)
5. **Clean code**: Remove any temporary debug print statements

### Adafruit IO Changes

#### Rate Limiting
- Free tier: 30 data points/minute maximum
- With 8 sensors: minimum 16 seconds between publishes
- **NEVER reduce the 0.5 second delay between individual sensor publishes**
- Current cron schedule (every 5 minutes) is safe - warn if user wants more frequent

#### Feed Management
- Always include feed auto-creation logic for new sensors
- Use try/except with RequestError for 404 errors
- Include 0.5 second delay after creating new feed before first publish
- Handle 429 rate limit errors with 30 second retry

#### Error Handling
- **Log all API errors** - these are important for debugging
- Never fail silently - at minimum log to stderr
- Use RequestError exception from Adafruit_IO library
- Exit with non-zero status on failure (important for cron monitoring)

### Cron Job Considerations

- Script is designed to be **cron-friendly** (non-interactive)
- Uses absolute paths for `.env` file location
- Logs to both file and stdout
- Exit codes: 0 = success, 1 = failure
- Current schedule: `*/5 * * * * /home/kleinmatic/.virtualenvs/pimoroni/bin/python3 /home/kleinmatic/Code/enviroplus-logger/publish_to_adafruit.py`
- **IMPORTANT**: If user renames folder, remind them to update crontab paths

### Code Style

#### Python Conventions
- Follow Python 3 standard library conventions
- Type hints: Not required (keeping code simple)
- Exception handling: Required for all I/O operations
- Logging: Use logging module for important events only (not verbose debug)

#### When Suggesting Changes
- Prefer simple solutions over complex ones
- Avoid adding new dependencies unless necessary
- Consider the Pi Zero's limited resources
- Test with the hardware when possible
- Explain trade-offs clearly to the user

### Home Assistant Integration

**Status**: Completed (2025-11-16)

The project now supports dual publishing to both Adafruit IO and Home Assistant.

#### MQTT Discovery Configuration
- Each sensor must have proper `device_class` to work correctly in Home Assistant
- **Critical**: Light sensor must use unit 'lx' (not 'lux') for illuminance device_class
- All sensors include icons using 'mdi:' prefix (Material Design Icons)
- Sensors are grouped under single device: "Enviro+ Sensor"
- Discovery configs are published with `retain=True` for persistence

#### Testing Home Assistant Changes
1. **Verify MQTT broker connectivity** before publishing
2. **Check Home Assistant logs** for discovery errors (Settings → System → Logs)
3. **Verify sensors in States tab** (Developer Tools → States, filter "enviro")
4. **Check device in MQTT integration** (Settings → Devices & Services → MQTT)
5. **Clear retained messages** if changing sensor configs (use MQTT Developer Tools)

#### Publishing Control
- Both services can be enabled/disabled independently via `.env`
- Script succeeds if at least one enabled service publishes successfully
- If both are disabled, script exits with error
- Always log which services are enabled at startup

### Common Mistakes to Avoid

1. **Don't assume feeds exist** - Always include auto-creation logic (Adafruit IO)
2. **Don't ignore rate limits** - This will cause 429 errors (Adafruit IO)
3. **Don't add verbose logging** - Preserves microSD card lifespan
4. **Don't test gas sensors for < 10 minutes** - Warm-up time is real
5. **Don't forget the virtual environment** - All pip installs and python runs need it activated
6. **Don't commit .env file** - Check git status before committing
7. **Don't remove the BME280 first reading discard** - It's essential for accuracy
8. **Don't add first reading discard to MICS6814** - Gas sensors work correctly on first read
9. **Don't use 'lux' as unit for illuminance device_class** - Use 'lx' for Home Assistant
10. **Don't forget to test both publishing destinations** - If both enabled, verify both work
11. **Don't skip checking Home Assistant logs** - MQTT discovery errors only appear there

### Questions to Ask User

Before making significant changes, confirm:

- **New sensors**: "Should this publish to Adafruit IO, Home Assistant, or both?"
- **Publishing destinations**: "Do you want to keep publishing to Adafruit IO, or switch to Home Assistant only?"
- **Performance impact**: "This library is 5MB - OK for Pi Zero?"
- **Logging changes**: "This adds logging - is that acceptable for microSD longevity?"
- **Feed/sensor names**: "What should I name this in Adafruit IO and Home Assistant?"
- **Temperature compensation**: "Want me to test different compensation factors?"
- **Cron frequency**: "Free tier allows 30/min - current schedule is every 5 min. Change it?"
- **Home Assistant setup**: "Do you have Home Assistant and MQTT broker set up already?"

---

## Project Architecture

### Overview

**Purpose**: Read environmental sensors from a Pimoroni Enviro+ HAT on a Raspberry Pi and publish the data to Adafruit IO and Home Assistant for cloud monitoring and visualization.

**Platform**: Raspberry Pi Zero 2W (works on any Pi)
**Language**: Python 3
**Cloud Services**: Adafruit IO (free tier), Home Assistant (local MQTT)

### Architecture Flow

```
Raspberry Pi + Enviro+ HAT
    ↓
Python Script (publish_to_adafruit.py)
    ↓
Read Sensors → Format Data → Publish via MQTT/HTTP
    ↓
Adafruit IO Cloud + Home Assistant (local)
    ↓
Web Dashboard (io.adafruit.com) + Home Assistant UI
```

### Hardware Components

#### Pimoroni Enviro+ HAT
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

### Software Stack

#### Dependencies
- **enviroplus** - Main library for Enviro+ HAT
- **bme280** - BME280 sensor driver
- **ltr559** - LTR559 sensor driver
- **smbus2** - I2C communication
- **Adafruit_IO** - Adafruit IO client library
- **paho-mqtt** - MQTT client for Home Assistant
- **python-dotenv** - Environment variable management

#### Virtual Environment
Located at: `~/.virtualenvs/pimoroni`

Always activate before running:
```bash
source ~/.virtualenvs/pimoroni/bin/activate
```

### File Structure

```
enviroplus-logger/
├── publish_to_adafruit.py  # Main script (cron-friendly)
├── read_sensors.py          # Simple sensor test script
├── display_temperature.py   # Temperature calibration display tool
├── setup_adafruit.sh        # Dependency installer
├── .env                     # Credentials (NOT in git)
├── .env.example             # Template for credentials
├── .gitignore               # Git exclusions
├── README.md                # User documentation
├── CLAUDE.md                # This file (AI context)
├── .claude/
│   └── skills/
│       └── add-sensor/      # Skill for adding new sensors
└── sensor_log.txt           # Runtime log (NOT in git)
```

### Key Design Decisions

#### 1. Temperature Compensation
The BME280 sensor is heated by the Raspberry Pi CPU, causing temperature readings to be artificially high. The script includes optional CPU temperature compensation:

```python
comp_temp = raw_temp - ((cpu_temp - raw_temp) / factor)
```

- **Factor = 0**: Disabled (use raw reading)
- **Factor = 20**: Light compensation (recommended for Pi Zero 2W)
- **Factor = 2.25**: Heavy compensation (recommended for Pi 4)

For the Pi Zero 2W, raw readings are often most accurate (factor = 0).

#### 2. Gas Sensor Readings
The MICS6814 measures **resistance**, not concentration:
- **Higher resistance (kΩ)** = Cleaner air
- **Lower resistance** = Gas detected

These are **relative measurements**. You must:
1. Establish a baseline in clean air
2. Monitor for changes/drops over time
3. Understand that sensors detect **classes of gases**, not individual gases

Warm-up time: 10-48 hours for stable readings.

#### 3. Feed Auto-Creation
The script automatically creates Adafruit IO feeds on first run if they don't exist. This simplifies setup but means feeds appear with default settings.

#### 4. Cron Scheduling
Designed to run via cron (non-interactive):
- Logs to file: `sensor_log.txt`
- Also outputs to stdout for debugging
- Handles rate limiting (30 data points/min on free tier)
- Recommended interval: Every 5 minutes

#### 5. Stale First Reading Pattern
Both BME280 and MICS6814 sensors return stale data on first read. The code discards the first reading and uses the second reading for both sensor types. This was discovered through testing and is critical for accurate readings.

### Home Assistant Integration Details

**Architecture**:
- **MQTT Broker**: Mosquitto add-on in Home Assistant
- **Discovery Protocol**: Home Assistant MQTT Discovery (automatic sensor detection)
- **Connection**: Direct MQTT connection to homeassistant.local:1883
- **Authentication**: Username/password stored in .env file

**Configuration**:
Both publishing destinations can be independently enabled/disabled via `.env`:
```
ENABLE_ADAFRUIT_IO=true
ENABLE_HOMEASSISTANT=true
```

**MQTT Settings**:
```
MQTT_BROKER=homeassistant.local
MQTT_PORT=1883
MQTT_USERNAME=enviroplus
MQTT_PASSWORD=<stored in .env>
```

**How It Works**:
1. Script reads sensors once
2. Publishes to Adafruit IO (if enabled)
3. Publishes to Home Assistant via MQTT (if enabled)
4. Home Assistant auto-discovers sensors via MQTT Discovery protocol
5. All 8 sensors appear as a single "Enviro+ Sensor" device in Home Assistant

**Sensors in Home Assistant**:
All sensors include proper device classes, units, and icons:
- **Temperature**: °C (device_class: temperature)
- **Pressure**: hPa (device_class: atmospheric_pressure)
- **Humidity**: % (device_class: humidity)
- **Light**: lx (device_class: illuminance)
- **Proximity**: no unit
- **Oxidising**: kΩ (gas resistance)
- **Reducing**: kΩ (gas resistance)
- **NH3**: kΩ (gas resistance)

---

## Troubleshooting Reference

### Quick Sensor Check
```bash
source ~/.virtualenvs/pimoroni/bin/activate
python3 /home/kleinmatic/Code/enviroplus-logger/read_sensors.py
```

### Check Recent Logs
```bash
tail -50 /home/kleinmatic/Code/enviroplus-logger/sensor_log.txt
grep "ERROR\|WARNING" /home/kleinmatic/Code/enviroplus-logger/sensor_log.txt | tail -20
```

### I2C Device Detection
```bash
i2cdetect -y 1
```

Expected devices:
- 0x23 = LTR559 (light/proximity)
- 0x49 = ADC (gas sensors)
- 0x76 = BME280 (temp/pressure/humidity)

### Manual Sensor Test (All Sensors)
```bash
source ~/.virtualenvs/pimoroni/bin/activate
python3 << 'EOF'
import time
from bme280 import BME280
from smbus2 import SMBus
try:
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559
from enviroplus import gas

bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

# Discard first BME280 reading
_ = bme280.get_temperature()
_ = bme280.get_pressure()
_ = bme280.get_humidity()
time.sleep(0.1)

print(f'Temperature: {bme280.get_temperature():.2f} °C')
print(f'Pressure: {bme280.get_pressure():.2f} hPa')
print(f'Humidity: {bme280.get_humidity():.2f} %')
print(f'Light: {ltr559.get_lux():.2f} lux')
print(f'Proximity: {ltr559.get_proximity():.2f}')

# Discard first gas reading
_ = gas.read_all()
time.sleep(0.1)
gas_data = gas.read_all()

print(f'Oxidising: {gas_data.oxidising/1000:.2f} kΩ')
print(f'Reducing: {gas_data.reducing/1000:.2f} kΩ')
print(f'NH3: {gas_data.nh3/1000:.2f} kΩ')
EOF
```

### Test Light Sensor with High Sensitivity
```bash
source ~/.virtualenvs/pimoroni/bin/activate
python3 -c "
from ltr559 import LTR559
import time
sensor = LTR559()
sensor.set_light_options(active=True, gain=96)
sensor.set_light_integration_time_ms(400)
time.sleep(0.5)
ch0, ch1 = sensor.get_raw_als()
lux = sensor.get_lux()
print(f'High sensitivity: {lux:.2f} lux (CH0={ch0}, CH1={ch1})')
"
```

### Check Power Status
```bash
vcgencmd get_throttled
vcgencmd measure_volts
vcgencmd measure_temp
```

### Common Issues

#### Error: "Module not found: enviroplus"
- Virtual environment not activated
- Solution: `source ~/.virtualenvs/pimoroni/bin/activate`

#### Error: "Adafruit IO credentials not configured"
- `.env` file missing or incorrect
- Solution: Check `.env` file exists and has correct credentials

#### Error: "404 Not Found" from Adafruit IO
- This is normal on first run - script auto-creates feeds
- If persists, check username is correct (case-sensitive)

#### Error: "429 Rate Limit" from Adafruit IO
- Publishing too frequently
- Free tier: 30 data points/minute max
- With 8 sensors, run at most every 2 minutes
- Solution: Reduce cron frequency

#### Temperature Readings Too High/Low
- CPU heating the sensor OR over-compensation
- Solution: Adjust `TEMP_COMPENSATION_FACTOR` in `.env`
- For Pi Zero 2W, try factor = 0 (disabled)

#### Gas Sensor Values Seem Wrong
- Gas sensors measure resistance, not concentration
- Need 10-48 hour warm-up for stable readings
- Establish baseline first, then watch for changes
- Affected by temperature and humidity
- **Check if first reading discard is in place** (required as of 2025-11-19)

#### Cron Job Not Running After Changes
- Check crontab: `crontab -l`
- Verify paths are correct (especially after folder renames)
- Test manually first: `source ~/.virtualenvs/pimoroni/bin/activate && python3 /full/path/to/publish_to_adafruit.py`
- Check for errors: `grep CRON /var/log/syslog` or check mail

#### Script Suddenly Stopped Publishing
- Check if `python-dotenv` is installed: `pip list | grep dotenv`
- Check if `paho-mqtt` is installed: `pip list | grep paho`
- Verify `.env` file exists and has credentials
- Run manually to see error messages
- Check Adafruit IO dashboard for service issues

---

## Project History & Important Paths

### Version History

- **v2.2** (2025-12-06): Temperature calibration for vertical wall mounting
  - Created `display_temperature.py` calibration tool with LCD display
  - Displays compensated temperature with rolling average (10 readings, 100s window)
  - Calibrated TEMP_COMPENSATION_FACTOR from 1.71 to 1.43 for vertical wall mount
  - 10-second update interval for stable readings
  - Mounting orientation significantly affects heat dissipation from CPU

- **v2.1** (2025-11-19): Fixed gas sensor stale reading bug
  - Added first reading discard for MICS6814 gas sensors
  - Resolves issue with alternating 6104.0/6788.44 kΩ readings
  - Updated both `publish_to_adafruit.py` and `read_sensors.py`

- **v2.0** (2025-11-16): Home Assistant integration
  - Added Home Assistant MQTT publishing with auto-discovery
  - Dual publishing to both Adafruit IO and Home Assistant
  - Independent enable/disable flags for each service
  - Added paho-mqtt dependency
  - All 8 sensors auto-discovered in Home Assistant as single device
  - Proper device classes, units, and icons for Home Assistant

- **v1.0** (2025-01-11): Initial release
  - Basic sensor reading (BME280, LTR559, MICS6814)
  - Adafruit IO publishing with auto feed creation
  - Temperature compensation (configurable)
  - Cron-friendly logging
  - Secure credential management via .env
  - Standard requirements.txt for pip installation

### Known Issues to Watch For
1. **After folder rename**: Always update crontab paths
2. **Missing python-dotenv**: Script will fail to read `.env` - install with `pip install python-dotenv`
3. **Missing paho-mqtt**: Required for Home Assistant integration - install with `pip install paho-mqtt`
4. **Light sensor unit**: Must use unit 'lx' not 'lux' for Home Assistant illuminance device_class
5. **Stale first readings**: BME280 requires first reading discard (MICS6814 does NOT)
6. **Temperature recalibration**: Required after changing device mounting orientation (horizontal→vertical, wall mount, etc.)
7. **Pi OS version**: Current Pi OS is Debian 13 (as of Aug 2024). Pimoroni officially supports Debian 12 but libraries work fine on Debian 13.

### Important Paths
- **Project location**: `~/Code/enviroplus-logger`
- **Virtual environment**: `~/.virtualenvs/pimoroni`
- **Log file**: `~/Code/enviroplus-logger/sensor_log.txt`
- **Credentials**: `~/Code/enviroplus-logger/.env` (NOT in git)
- **Home Assistant**: `homeassistant.local`

### Cron Job
Current schedule: Every 5 minutes
```
*/5 * * * * /home/kleinmatic/.virtualenvs/pimoroni/bin/python3 /home/kleinmatic/Code/enviroplus-logger/publish_to_adafruit.py
```

---

## Useful References

- [Pimoroni Enviro+ GitHub](https://github.com/pimoroni/enviroplus-python)
- [Adafruit IO Documentation](https://io.adafruit.com/api/docs)
- [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
- [BME280 Datasheet](https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/)
- [MICS6814 Datasheet](https://www.sgxsensortech.com/content/uploads/2015/02/1143_Datasheet-MiCS-6814-rev-8.pdf)
- [Material Design Icons](https://pictogrammers.com/library/mdi/) (for Home Assistant icons)
