from pathlib import Path
from manager.rtk_manager import RTKManager

if __name__ == "__main__":
    manager = RTKManager(
        yaml_path=Path("./stations.yaml"),
        rtklib_path=Path("./rtklib/rtkrcv")
    )
    
    manager.run()
