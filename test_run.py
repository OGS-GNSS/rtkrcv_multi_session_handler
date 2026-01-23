from pathlib import Path
import sys

print("DEBUG: Starting test_run.py")
try:
    from manager.rtk_manager import RTKManager
    print("DEBUG: Imported RTKManager")
    
    manager = RTKManager(
        yaml_path=Path("./list.yaml"),
        rtklib_path=Path("./rtklib/rtkrcv")
    )
    print("DEBUG: Initialized Manager")
    
    manager.run()
    print("DEBUG: Finished run")
except Exception as e:
    print(f"DEBUG: Exception: {e}")
    import traceback
    traceback.print_exc()
