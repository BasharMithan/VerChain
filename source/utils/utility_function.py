



import json
from pathlib import Path



class LedgerUtilities:
    def __init__(self) -> None:
        ...
    


    @staticmethod
    def readLedger(filePath: Path ) -> list:
        path = filePath 
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []   # corrupt file — treat as empty
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    
    @staticmethod
    def getLedgerLength(filePath: Path ) -> int:
        """Returns how many blocks are in the /storage/.ledger.json file."""
        return len(LedgerUtilities.readLedger(filePath))

    @staticmethod
    def getLatestHash(filePath: Path ) -> str:
            """
            Return the latest block's hash as a hex string.
            Falls back to 64 zeros when no blocks or an error occurs.
            Handles both dict-shaped blocks and dataclass/objects with a 'hash' attribute.
            """

            blocks = LedgerUtilities.readLedger(filePath)

            zero_hash = "0" * 64
            try:
                # Prefer in-memory ledger
                if blocks:
                    latest = blocks[-1]
                else:
                    latest = LedgerUtilities.getLatestBlock(filePath)
                    if not latest:
                        return zero_hash
                if isinstance(latest, dict):
                    return latest.get("hash", zero_hash)
                return getattr(latest, "hash", zero_hash)
            except Exception:
                return zero_hash
        
    @staticmethod
    def getLatestBlock(filePath: Path):
        blocks: list = []
        try:
            with open(filePath, "r", encoding='utf-8') as ledgerFile:
                data = json.load(ledgerFile)
                for block in data:
                    blocks.append(block)
            return blocks[-1]
        except json.JSONDecodeError:
            return None
    

    @staticmethod
    def getCHIDList(filePath: Path) -> list:
        """Return a list of unique CHIDs found in the ledger.
        Scans each block in the ledger. For dict-shaped blocks it looks for a
        top-level 'chid' key and for nested actions (a list under 'actions' or
        'txs') it also collects any 'chid' values. For object blocks it will
        attempt to read the 'chid' attribute and any actions attribute that is
        iterable. The returned list preserves discovery order and contains no
        duplicates.
        """
        chid_set = set()
        chid_list = []
        blocks = LedgerUtilities.readLedger(filePath)
        for blk in blocks:
            # handle dict-like blocks
            if isinstance(blk, dict):
                # top-level chid
                chid = blk.get("chid")
                if chid and chid not in chid_set:
                    chid_set.add(chid)
                    chid_list.append(chid)
                # look into common action containers
                for container_key in ("actions", "txs", "transactions"):
                    items = blk.get(container_key)
                    if isinstance(items, list):
                        for it in items:
                            if isinstance(it, dict):
                                c = it.get("chid")
                                if c and c not in chid_set:
                                    chid_set.add(c)
                                    chid_list.append(c)
            else:
                # handle object-like blocks
                try:
                    chid = getattr(blk, "chid", None)
                    if chid and chid not in chid_set:
                        chid_set.add(chid)
                        chid_list.append(chid)
                    # try to inspect actions attribute if present
                    for attr in ("actions", "txs", "transactions"):
                        items = getattr(blk, attr, None)
                        if items and hasattr(items, "__iter__"):
                            for it in items:
                                c = None
                                if isinstance(it, dict):
                                    c = it.get("chid")
                                else:
                                    c = getattr(it, "chid", None)
                                if c and c not in chid_set:
                                    chid_set.add(c)
                                    chid_list.append(c)
                except Exception:
                    # ignore malformed block entries
                    continue
        return chid_list




def getProjectVersion() -> str:
    """Gets the current version of the project by excuting the command `git describe --tags --abbrev=0`
    to associate it with the performance report.
    Returns:
        str: The current version.
    """

    import subprocess
    versions = subprocess.run("git describe --tags --abbrev=0", capture_output=True, text=True)
    return versions.stdout.strip()



from enum import Enum
from typing import Any, Type, TypeVar

E = TypeVar("E", bound=Enum)


def listEnum(enum_class: Type[E]) -> list[Any]:
    """Return the raw values of the Enum's members."""
    return [member.value for member in enum_class]


def enumValue(enum_class: Type[E], value: Any) -> E:
    """Return the Enum member matching the given value."""
    return enum_class(value)


def normalizeLocalHost(host: str) -> str:
    """Replace the local hostname alias with its IPv4 loopback address."""
    return "127.0.0.1" if host == "localhost" else host