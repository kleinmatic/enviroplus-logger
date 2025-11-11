#!/usr/bin/env python3

"""
Read and display all Enviro+ sensor readings
"""

import time
from bme280 import BME280
from smbus2 import SMBus

try:
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

from enviroplus import gas


def get_cpu_temperature():
    """Get CPU temperature for BME280 compensation"""
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
    return temp


def main():
    # Initialize sensors
    bus = SMBus(1)
    bme280 = BME280(i2c_dev=bus)

    # CPU temperature compensation factor
    # Higher factor = less compensation. Set to 0 to disable compensation.
    factor = 0
    cpu_temps = [get_cpu_temperature()] * 5

    print("\n" + "="*60)
    print("ENVIRO+ SENSOR READINGS")
    print("="*60 + "\n")

    # === BME280: Temperature, Pressure, Humidity ===
    print("BME280 (Temperature/Pressure/Humidity)")
    print("-" * 40)

    # Get compensated temperature
    cpu_temp = get_cpu_temperature()
    cpu_temps = cpu_temps[1:] + [cpu_temp]
    avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
    raw_temp = bme280.get_temperature()

    # Calculate compensation
    if factor > 0:
        compensation_amount = (avg_cpu_temp - raw_temp) / factor
        comp_temp = raw_temp - compensation_amount
    else:
        compensation_amount = 0
        comp_temp = raw_temp

    print(f"  Raw Temperature:   {raw_temp:.2f} °C")
    print(f"  CPU Temperature:   {avg_cpu_temp:.2f} °C")
    print(f"  Compensation:      -{compensation_amount:.2f} °C")
    print(f"  Compensated Temp:  {comp_temp:.2f} °C")
    print(f"  Pressure:          {bme280.get_pressure():.2f} hPa")
    print(f"  Humidity:          {bme280.get_humidity():.2f} %")
    print()

    # === LTR559: Light and Proximity ===
    print("LTR559 (Light/Proximity)")
    print("-" * 40)
    lux = ltr559.get_lux()
    proximity = ltr559.get_proximity()
    print(f"  Light:             {lux:.2f} Lux")
    print(f"  Proximity:         {proximity:.2f}")
    print()

    # === MICS6814: Gas Sensor ===
    print("MICS6814 (Gas Sensor)")
    print("-" * 40)
    gas_readings = gas.read_all()
    print(f"  Oxidising:         {gas_readings.oxidising / 1000:.2f} kΩ")
    print(f"  Reducing:          {gas_readings.reducing / 1000:.2f} kΩ")
    print(f"  NH3:               {gas_readings.nh3 / 1000:.2f} kΩ")
    print()

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
