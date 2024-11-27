import os
import time

# Upload blink.py to Pico
os.system("python -m ampy.cli --port COM4 put blink.py")

# Run blink.py on Pico
os.system("python -m ampy.cli --port COM4 run blink.py")