
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field


"""
Date: 9/13/2026
Title: Configs
Description: A file that contains the settings and configs for the project.
Developer: Bashar Mithan
"""

class Performance(Enum):
    """Safety is the the setting class that controls how safe the project is."""

    safe = "SAFE"
    fast = "FAST"



class LedgerCofigs(BaseSettings):
    ...


class ConnectionCofigs(BaseSettings):
    bootstrapPeers: list[tuple[str, int]] = [('127.0.0.1', 8000)]



class CredentialConstraints(BaseModel):
    maxUploadSize: int = 5 * 1024 * 1024
    supportedCredentialFormats: set[str] = {".pdf"}





class Settings(BaseSettings):
    """A configuration class to control how the project behave.

    Args:
        object ()
    """

    
    configurationFilePath: Path = Field(
        default=Path(__file__).resolve().parents[2] / "settings.yml",
        exclude=True
        ) # Excluding the absulute Windows path from the settings.yml file.

    difficulity: int = 4
    performance: Performance = Performance.safe

    ledger: LedgerCofigs
    connection: ConnectionCofigs
    credentials: CredentialConstraints = CredentialConstraints()





defaultSettings = Settings(ledger=LedgerCofigs(), connection=ConnectionCofigs())
