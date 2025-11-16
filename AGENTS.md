# AGENTS.md - Enviroplus Logger Project

AI behavior instructions and workflow rules for this project.

## Hardware Constraints - Raspberry Pi Zero 2W

### MicroSD Card Longevity
- **NEVER add logging to production code** - This project runs on a Raspberry Pi Zero with a microSD card
- Excessive writes reduce microSD card lifespan
- The current logging in `publish_to_adafruit.py` is acceptable but should not be expanded
- If debugging is needed, use temporary print statements and remove them before committing
- Consider suggesting in-memory logging or syslog for any new logging requirements

### Performance Considerations
- Pi Zero 2W has limited CPU and RAM
- Keep sensor reading code lightweight
- Avoid adding heavy dependencies
- Test performance impact of any new libraries

## Sensor Code Modifications

### BME280 (Temperature/Pressure/Humidity)
- **ALWAYS discard first reading** - BME280 returns stale data on first read
- Include 0.1 second delay after discarding first reading for sensor stabilization
- When modifying temperature compensation:
  - Test with factor=0 (disabled), factor=10, and factor=20
  - Document the tested values in commit message
  - RUN `read_sensors.py` manually to verify compensation math

### MICS6814 (Gas Sensors)
- Gas sensors need 10-48 hour warm-up period for stable readings
- **Test any changes over a 10+ minute period** minimum
- Remember: readings are resistance values, not concentrations
- Lower resistance = gas detected, higher resistance = cleaner air
- Never add "concentration" calculations without proper calibration

### General Sensor Rules
- Always test with `read_sensors.py` before modifying `publish_to_adafruit.py`
- Maintain the "discard first reading" pattern for BME280
- Keep sensor reading code in a try/except block
- Log sensor errors but continue execution when possible

## Security Requirements

### Credentials
- **NEVER hardcode credentials** - Always use environment variables
- Always load from `.env` file using python-dotenv
- Verify `.env` is in `.gitignore` before committing
- When adding new credentials, update `.env.example` with placeholder values

### Secrets in Code
- No API keys, tokens, or passwords in any tracked files
- No IP addresses or personal information in comments or documentation
- Check that sensitive files remain in `.gitignore`

## Before Committing

1. **Test hardware**: Run `read_sensors.py` to verify sensors still work
2. **Security check**: Confirm `.env` is still in `.gitignore`
3. **Documentation**: Update SKILLS.md if architecture or design decisions changed
4. **Logging**: Ensure no new excessive logging was added (microSD longevity)
5. **Clean code**: Remove any temporary debug print statements

## Adafruit IO Changes

### Rate Limiting
- Free tier: 30 data points/minute maximum
- With 8 sensors: minimum 16 seconds between publishes
- **NEVER reduce the 0.5 second delay between individual sensor publishes**
- Current cron schedule (every 5 minutes) is safe - warn if user wants more frequent

### Feed Management
- Always include feed auto-creation logic for new sensors
- Use try/except with RequestError for 404 errors
- Include 0.5 second delay after creating new feed before first publish
- Handle 429 rate limit errors with 30 second retry

### Error Handling
- **Log all API errors** - these are important for debugging
- Never fail silently - at minimum log to stderr
- Use RequestError exception from Adafruit_IO library
- Exit with non-zero status on failure (important for cron monitoring)

## Adding New Sensors

When adding a new sensor to the project:

1. **Import**: Add sensor library import at top of file
2. **Initialize**: Add initialization in `read_sensors()` function
3. **Read**: Get sensor value and add to `sensors` dict with clear key name
4. **Publish to Adafruit IO**: Add feed mapping in `publish_to_adafruit()` feed_mapping dict
5. **Publish to Home Assistant**: Add sensor config in `publish_to_homeassistant()` sensor_configs dict
   - Include proper `device_class` if applicable (see Home Assistant docs)
   - Choose correct `unit_of_measurement` (check compatibility with device_class!)
   - Select appropriate icon from Material Design Icons (mdi:)
6. **Document**: Update README.md sensor list and descriptions
7. **Update SKILLS.md**: Add sensor details to hardware section
8. **Test**: Run manually at least 3 times to verify stability
9. **Verify in Home Assistant**: Check sensor appears in States tab and has correct unit/icon
10. **Rate limit check**: Ensure total sensors × 0.5 seconds < 30 seconds (Adafruit IO limit)

## Cron Job Considerations

- Script is designed to be **cron-friendly** (non-interactive)
- Uses absolute paths for `.env` file location
- Logs to both file and stdout
- Exit codes: 0 = success, 1 = failure
- Current schedule: `*/5 * * * * /home/kleinmatic/.virtualenvs/pimoroni/bin/python3 /home/kleinmatic/Code/enviroplus-logger/publish_to_adafruit.py`
- **IMPORTANT**: If user renames folder, remind them to update crontab paths

## Code Style

### Python Conventions
- Follow Python 3 standard library conventions
- Type hints: Not required (keeping code simple)
- Exception handling: Required for all I/O operations
- Logging: Use logging module for important events only (not verbose debug)

### When Suggesting Changes
- Prefer simple solutions over complex ones
- Avoid adding new dependencies unless necessary
- Consider the Pi Zero's limited resources
- Test with the hardware when possible
- Explain trade-offs clearly to the user

## Home Assistant Integration

**Status**: Completed (2025-11-16)

The project now supports dual publishing to both Adafruit IO and Home Assistant.

### MQTT Discovery Configuration
- Each sensor must have proper `device_class` to work correctly in Home Assistant
- **Critical**: Light sensor must use unit 'lx' (not 'lux') for illuminance device_class
- All sensors include icons using 'mdi:' prefix (Material Design Icons)
- Sensors are grouped under single device: "Enviro+ Sensor"
- Discovery configs are published with `retain=True` for persistence

### Testing Home Assistant Changes
1. **Verify MQTT broker connectivity** before publishing
2. **Check Home Assistant logs** for discovery errors (Settings → System → Logs)
3. **Verify sensors in States tab** (Developer Tools → States, filter "enviro")
4. **Check device in MQTT integration** (Settings → Devices & Services → MQTT)
5. **Clear retained messages** if changing sensor configs (use MQTT Developer Tools)

### Publishing Control
- Both services can be enabled/disabled independently via `.env`
- Script succeeds if at least one enabled service publishes successfully
- If both are disabled, script exits with error
- Always log which services are enabled at startup

## Common Mistakes to Avoid

1. **Don't assume feeds exist** - Always include auto-creation logic (Adafruit IO)
2. **Don't ignore rate limits** - This will cause 429 errors (Adafruit IO)
3. **Don't add verbose logging** - Preserves microSD card lifespan
4. **Don't test gas sensors for < 10 minutes** - Warm-up time is real
5. **Don't forget the virtual environment** - All pip installs and python runs need it activated
6. **Don't commit .env file** - Check git status before committing
7. **Don't remove the BME280 first reading discard** - It's essential for accuracy
8. **Don't use 'lux' as unit for illuminance device_class** - Use 'lx' for Home Assistant
9. **Don't forget to test both publishing destinations** - If both enabled, verify both work
10. **Don't skip checking Home Assistant logs** - MQTT discovery errors only appear there

## Questions to Ask User

Before making significant changes, confirm:

- **New sensors**: "Should this publish to Adafruit IO, Home Assistant, or both?"
- **Publishing destinations**: "Do you want to keep publishing to Adafruit IO, or switch to Home Assistant only?"
- **Performance impact**: "This library is 5MB - OK for Pi Zero?"
- **Logging changes**: "This adds logging - is that acceptable for microSD longevity?"
- **Feed/sensor names**: "What should I name this in Adafruit IO and Home Assistant?"
- **Temperature compensation**: "Want me to test different compensation factors?"
- **Cron frequency**: "Free tier allows 30/min - current schedule is every 5 min. Change it?"
- **Home Assistant setup**: "Do you have Home Assistant and MQTT broker set up already?"
