from pathlib import Path
from manager.rtk_manager import RTKManager

if __name__ == "__main__":
    manager = RTKManager(
        yaml_path=Path("./list.yaml"),
        rtklib_path=Path("./lib/rtkrcv")
    )
    
    manager.run()
