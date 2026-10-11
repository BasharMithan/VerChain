from pathlib import Path
import logging as Logger

# Make sure the storage folder next to the project root exists.
logFile = Path(__file__).resolve().parents[2] / "storage" / "log.log"
logFile.parent.mkdir(parents=True, exist_ok=True)

Logger.basicConfig(
    filename=str(logFile),
    filemode="a",
    level=Logger.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)