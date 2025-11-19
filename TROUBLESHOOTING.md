# LTR-559 Light Sensor Troubleshooting Plan

**Objective**: To definitively diagnose the LTR-559 light sensor issue and implement robust software workarounds.

**Background**: The LTR-559 light sensor is reporting lux values that are ~1/15th of the expected value. The current diagnosis is a hardware failure of the visible light photodiode, based on the `CH1 (IR) >= CH0 (Visible+IR)` reading.

This plan provides steps to confirm this diagnosis beyond any doubt and to implement code that can gracefully handle this specific hardware failure mode.

---

### Part 1: Deeper Diagnostic Steps

These steps are intended to rule out any possibility of a software or configuration issue. Execute these using temporary, standalone Python scripts.

1.  **Perform a Software Reset:**
    *   **Goal:** Clear any potentially stuck configuration within the LTR-559 chip.
    *   **Action:** Write and execute a script that accesses the LTR-559's `ALS_CONTR` register (address `0x80`) and sets the `SW_Reset` bit (bit 1). After the reset, re-read the `CH0` and `CH1` values to observe any change in behavior.

2.  **Conduct an Exhaustive Gain & Integration Test:**
    *   **Goal:** Confirm that the failure is present across all sensor operating modes.
    *   **Action:** Create a test script that iterates through all possible gain settings (`1x`, `2x`, `4x`, `8x`, `48x`, `96x`) and a range of integration times (`50ms`, `100ms`, `200ms`, `400ms`). Log the raw `CH0`, `CH1`, and calculated `lux` for each combination.
    *   **Success Criteria:** If `CH1 >= CH0` persists across all valid configurations, a hardware fault is confirmed.

3.  **Run a Minimal Standalone Test:**
    *   **Goal:** Rule out I2C bus conflicts or interference from other libraries (`bme280`, `gas`, etc.).
    *   **Action:** Write a new script (`minimal_light_test.py`) that imports **only** `ltr559` and `time`. Use this script to initialize the sensor and read its values. This isolates the sensor interaction from the rest of the application.

4.  **Read Registers Directly via I2C (Ultimate Test):**
    *   **Goal:** Bypass the `ltr559` Python library to test the hardware directly.
    *   **Action:** Use a library like `smbus2` to write a script that communicates with the sensor at I2C address `0x23`. Manually read the four data bytes from the data registers (`0x88` to `0x8B`). Assemble the raw integer values for `CH0` and `CH1` and print them. This will prove whether the hardware itself is providing faulty data.

---

### Part 2: Recommended Software Mitigation

This is the most valuable long-term fix. Instead of knowingly publishing incorrect data, the code should be made aware of the hardware failure.

1.  **Implement "Hardware Error State" Detection:**
    *   **Goal:** Prevent misleading data from being published and make the system resilient to this specific failure.
    *   **Action:** In `publish_to_adafruit.py`, after reading the sensor, implement a check for the known failure signature.

    *   **Proposed Logic:**
        ```python
        # In publish_to_adafruit.py, after reading from the LTR559
        try:
            ch0, ch1 = ltr559.get_raw_als(backlight_compensation=False)
            lux = ltr559.get_lux()

            # Hardware failure signature: CH1 (IR) is greater than or equal to 
            # CH0 (Visible+IR) under non-zero light conditions, resulting in an abnormally low lux value.
            # The lux < 20 check helps avoid false positives in complete darkness.
            is_hardware_failed = ch1 > 0 and ch0 <= ch1 and lux < 20

            if is_hardware_failed:
                # Option 1 (Recommended): Publish a sentinel value to indicate failure.
                lux_to_publish = -1
                log.warning("Light sensor hardware failure detected. Publishing sentinel value (-1).")

                # Option 2: Skip publishing for this sensor entirely.
                # log.warning("Light sensor hardware failure detected. Skipping light sensor publish.")
                # continue # Or otherwise skip the publishing logic for this sensor
            else:
                lux_to_publish = lux
            
            # ... proceed to publish `lux_to_publish` ...

        except Exception as e:
            log.error(f"Failed to read light sensor: {e}")

        ```
    *   **Benefit:** This makes the system robust. It correctly identifies the fault, prevents data pollution, creates a clear log of the failure, and will automatically handle the situation if it ever reoccurs.

### Summary for the Agent

The hardware failure diagnosis is very likely correct. The primary recommendation is to implement **Part 2, Step 1: "Hardware Error State" Detection**. This provides a significant improvement in software robustness while awaiting hardware replacement. The diagnostic steps in Part 1 are for absolute, final confirmation if needed.
