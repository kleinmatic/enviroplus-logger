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
4. **Publish**: Add feed mapping in `publish_to_adafruit()` feed_mapping dict
5. **Document**: Update README.md sensor list and descriptions
6. **Update SKILLS.md**: Add sensor details to hardware section
7. **Test**: Run manually at least 3 times to verify stability
8. **Rate limit check**: Ensure total sensors × 0.5 seconds < 30 seconds

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

## Migration Path

This project is designed for eventual migration to Home Assistant:

- Keep sensor reading code separate from publishing code
- Use standard Python patterns (no Adafruit-specific code in sensor reading)
- Make it easy to swap `publish_to_adafruit()` with MQTT publishing
- Don't tightly couple sensors to Adafruit IO feed structure

## Common Mistakes to Avoid

1. **Don't assume feeds exist** - Always include auto-creation logic
2. **Don't ignore rate limits** - This will cause 429 errors
3. **Don't add verbose logging** - Preserves microSD card lifespan
4. **Don't test gas sensors for < 10 minutes** - Warm-up time is real
5. **Don't forget the virtual environment** - All pip installs and python runs need it activated
6. **Don't commit .env file** - Check git status before committing
7. **Don't remove the BME280 first reading discard** - It's essential for accuracy

## Questions to Ask User

Before making significant changes, confirm:

- **New sensors**: "Should this publish to Adafruit IO or just log locally?"
- **Performance impact**: "This library is 5MB - OK for Pi Zero?"
- **Logging changes**: "This adds logging - is that acceptable for microSD longevity?"
- **Feed names**: "What should I name the new Adafruit IO feed?"
- **Temperature compensation**: "Want me to test different compensation factors?"
- **Cron frequency**: "Free tier allows 30/min - current schedule is every 5 min. Change it?"
