"""
fcan/utils.py
=============

provides utility functions.
"""

import threading

def wait_for_servers():   
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n! shutting down all servers")
