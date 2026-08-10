import sys
import os
sys.path.insert(0, ".")

print("Testing imports...")
try:
    from app.routers import enterprise
    print("enterprise router: OK")
except Exception as e:
    print(f"enterprise router ERROR: {e}")

try:
    from app import main
    print("main.py import: OK")
except Exception as e:
    print(f"main.py ERROR: {e}")
    import traceback
    traceback.print_exc()
