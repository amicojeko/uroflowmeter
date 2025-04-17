# listen_serial.py

import serial
import time
import os
from datetime import datetime
from uroflowmeter import load_data, analyze_flow, generate_pdf

HEADER = """
========================================
      UROFLUSSOMETRO - SERIAL LISTENER
========================================
"""

BEGIN_MARKER = "BEGIN DATA"
END_MARKER = "END DATA"
TIMEOUT_SECONDS = 3


def listen_serial(port="/dev/cu.usbmodem21101", baudrate=115200, output_dir="output"):
    print(HEADER)
    print(f"[*] Listening on {port} at {baudrate} baud...")

    while True:
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            lines = []
            recording = False
            last_data_time = None

            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                print(f"> {line}")  # Debug

                if line == BEGIN_MARKER:
                    print("[+] BEGIN DATA received. Recording started.")
                    lines = []
                    recording = True
                    last_data_time = time.time()
                    continue

                if recording:
                    if line == END_MARKER:
                        print("[+] END DATA received. Recording finished.")
                        break

                    lines.append(line)
                    last_data_time = time.time()

                    if last_data_time and (time.time() - last_data_time > TIMEOUT_SECONDS):
                        print("[!] Timeout: data transmission interrupted. Resetting...")
                        break

            ser.close()

            if lines:
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(output_dir, f"uroflow_{timestamp}.csv")
                with open(filename, "w") as f:
                    f.write("\n".join(lines))

                print(f"[✓] Data saved to {filename}")

                # Process and generate report
                df = load_data(filename)
                df, metrics = analyze_flow(df)
                pdf_path = filename.replace(".csv", ".pdf")
                generate_pdf(df, metrics, pdf_path=pdf_path)

                print("[✓] Report generated.")
                print("[*] Waiting for next transmission...\n")

        except serial.SerialException as e:
            print(f"[ERROR] Serial error: {e}")
            time.sleep(3)
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    listen_serial(port="/dev/cu.usbmodem21101", baudrate=115200)
