# Enviro+ Sensor Logger to Adafruit IO

Publish sensor readings from your Pimoroni Enviro+ HAT to Adafruit IO for monitoring and visualization. This project was vibe-coded with Claude Code.

## Hardware Requirements

- Raspberry Pi (tested on Pi Zero 2W, should work on any model)
- Pimoroni Enviro+ HAT
- MicroSD card with Raspberry Pi OS

## Prerequisites

Before using this project, you need to install the Pimoroni Enviro+ software and dependencies.

### 1. Install Pimoroni Enviro+ Library

```bash
# Clone the Pimoroni enviroplus-python repository
git clone https://github.com/pimoroni/enviroplus-python
cd enviroplus-python

# Run the installer
sudo ./install.sh
```

This installs the required libraries:
- `enviroplus` - Main library for the Enviro+ HAT
- `bme280` - Temperature, pressure, humidity sensor
- `ltr559` - Light and proximity sensor
- `st7735` - LCD display (if you want to use the display)
- `smbus2` - I2C communication

### 2. Set Up Python Virtual Environment (Optional but Recommended)

The Pimoroni installer can create a virtual environment for you:

```bash
# The installer creates: /home/your_username/.virtualenvs/pimoroni
# To activate it:
source ~/.virtualenvs/pimoroni/bin/activate
```

Or follow the instructions in the Pimoroni installer output.

### 3. Test Your Sensors

Verify your Enviro+ is working:

```bash
# Navigate to the examples directory
cd ~/enviroplus-python/examples

# Test basic sensors
python3 weather.py  # Temperature, pressure, humidity
python3 light.py    # Light and proximity
python3 gas.py      # Gas sensors
```

Press Ctrl+C to exit each test.

## Setup

### 1. Install Dependencies

You can either use the setup script or install manually:

**Option A: Use the setup script (recommended)**
```bash
cd ~/Code/enviroplus-logger
chmod +x setup_adafruit.sh
./setup_adafruit.sh
```

**Option B: Manual installation**
```bash
cd ~/Code/enviroplus-logger
source ~/.virtualenvs/pimoroni/bin/activate
pip install -r requirements.txt
```

### 2. Get Adafruit IO Credentials

1. Go to https://io.adafruit.com
2. Create a free account (if you don't have one)
3. Click the yellow **key icon (🔑)** in the top right
4. Copy your **Username** and **Active Key**

### 3. Configure Your Credentials

Create a `.env` file from the example template:

```bash
cd ~/Code/enviroplus-logger
cp .env.example .env
```

Edit `.env` and add your Adafruit IO credentials:

```bash
ADAFRUIT_IO_USERNAME=yourusername
ADAFRUIT_IO_KEY=aio_abc123yourkeyhere
TEMP_COMPENSATION_FACTOR=0
```

**Important**: The `.env` file is excluded from git (via `.gitignore`) to keep your credentials safe.

### 4. Test the Script

```bash
source ~/.virtualenvs/pimoroni/bin/activate
cd ~/Code/enviroplus-logger
./publish_to_adafruit.py
```

Check the output and verify data appears in your Adafruit IO feeds.

### 5. Set Up Cron Job

To run every 5 minutes:

```bash
crontab -e
```

Add this line:

```cron
*/5 * * * * ${HOME}/.virtualenvs/pimoroni/bin/python3 ${HOME}/Code/enviroplus-logger/publish_to_adafruit.py
```

To run every 2 minutes:

```cron
*/2 * * * * ${HOME}/.virtualenvs/pimoroni/bin/python3 ${HOME}/Code/enviroplus-logger/publish_to_adafruit.py
```

Save and exit. The script will now run automatically.

### 6. View Your Data

1. Go to https://io.adafruit.com
2. Click **Feeds** to see your data streams
3. Click **Dashboards** to create visualizations

The script creates these feeds:
- `enviro-temperature` (°C)
- `enviro-pressure` (hPa)
- `enviro-humidity` (%)
- `enviro-light` (Lux)
- `enviro-proximity`
- `enviro-oxidising` (kΩ)
- `enviro-reducing` (kΩ)
- `enviro-nh3` (kΩ)

## Understanding the Sensors

### Environmental Sensors (BME280)

**Temperature (°C)**
- Measures ambient air temperature
- Note: The BME280 can be heated by the Raspberry Pi CPU
- The script includes optional compensation (adjust `TEMP_COMPENSATION_FACTOR` in the script)
- Set factor to `0` to disable compensation and use raw readings

**Pressure (hPa)**
- Atmospheric pressure in hectopascals
- Normal range: 950-1050 hPa (depends on altitude and weather)
- Rising pressure = improving weather, falling pressure = worsening weather

**Humidity (%)**
- Relative humidity as a percentage
- Comfortable indoor range: 30-60%

### Light and Proximity (LTR559)

**Light (Lux)**
- Ambient light level
- Scale: 0 (complete darkness) to 64,000+ (bright sunlight)
- Typical values: 0.1 (moonlight), 100 (dim room), 400 (office), 10,000+ (outdoors)

**Proximity**
- Infrared proximity detection (0-65535)
- 0-10: Nothing nearby
- 1500+: Object very close (hand hovering, tap detection)
- Used to detect when object is blocking light sensor

### Gas Sensors (MICS6814)

The MICS6814 has three separate sensing elements that measure resistance. **Lower resistance = higher gas concentration**. These sensors detect **classes of gases**, not individual specific gases.

**Oxidising (kΩ)**
- Detects oxidising gases by measuring resistance
- Primary: NO2 (Nitrogen Dioxide) from vehicle exhaust, industrial emissions
- Also detects: O3 (Ozone), Cl2 (Chlorine from cleaning products)
- Higher values = cleaner air
- Lower values = oxidising gases detected

**Reducing (kΩ)**
- Detects reducing gases by measuring resistance
- Primary: CO (Carbon Monoxide) from incomplete combustion
- Also detects: H2 (Hydrogen), CH4 (Methane), H2S (Hydrogen Sulfide), Ethanol
- Higher values = cleaner air
- Lower values = reducing gases detected

**NH3 (kΩ)**
- Detects ammonia-type gases by measuring resistance
- Primary: NH3 (Ammonia) from cleaning products, fertilizers
- Also detects: H2S (Hydrogen Sulfide - rotten egg smell), Alcohol vapors
- Higher values = cleaner air
- Lower values = ammonia-type gases detected

#### Typical Baseline Values (Clean Indoor Air)

After a 10-48 hour warmup period, you should see values in these ranges:

| Sensor | Clean Air Baseline | Alert Threshold | Investigation Needed |
|--------|-------------------|-----------------|---------------------|
| **Oxidising** | 100-600 kΩ | < 100 kΩ | < 50 kΩ |
| **Reducing** | 1,000-10,000 kΩ | < 1,000 kΩ | < 500 kΩ |
| **NH3** | 100-2,000 kΩ | < 200 kΩ | < 100 kΩ |

**What to Watch For:**

**Oxidising drops significantly:**
- Vehicle exhaust nearby (NO2)
- Outdoor pollution entering building
- Strong cleaning products with bleach/chlorine

**Reducing drops significantly:**
- Cooking on gas stove
- Incomplete combustion (check furnace/water heater)
- Alcohol or solvent vapors
- Potential CO hazard

**NH3 drops significantly:**
- Ammonia-based cleaning products in use
- Fertilizers or pet waste nearby
- Strong alcohol vapors

**Important Notes About Gas Sensors:**
- These sensors measure **resistance**, not concentration (e.g., not "50 ppm CO")
- Readings are **relative** - establish YOUR baseline over 24-48 hours in normal conditions
- Sensors cannot distinguish between different gases in the same category
- Warm-up time required for stable readings (10-48 hours recommended)
- Affected by temperature and humidity - normalize comparisons to similar conditions
- Watch for drops of 20-50% from your baseline - this indicates gas detection
- Each sensor unit has unique baseline values - don't compare across different devices

**Example Scenarios:**
- Wave isopropyl alcohol near sensor → Reducing resistance drops dramatically
- Near busy road with traffic → Oxidising resistance drops (NO2)
- Open ammonia-based cleaner → NH3 resistance drops sharply
- Natural gas leak (methane) → Reducing resistance drops
- Cooking with gas stove → Reducing resistance temporarily decreases

## Monitoring

View logs:

```bash
cat ~/Code/claude-enviroplus/sensor_log.txt
tail -f ~/Code/claude-enviroplus/sensor_log.txt  # Follow live
```

## Troubleshooting

**Rate limiting**: Free tier allows 30 data points/minute. With 8 sensors, don't run more often than every 2 minutes.

**Credentials error**: Make sure you've replaced `YOUR_USERNAME_HERE` and `YOUR_KEY_HERE` in the script.

**Sensor errors**: Check that all hardware is properly connected and the virtual environment is activated.
