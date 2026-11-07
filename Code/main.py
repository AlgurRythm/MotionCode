"""Launcher. The app lives in features.py; `python main.py` and `python features.py` both start it."""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "features.py"),
               run_name="__main__")
