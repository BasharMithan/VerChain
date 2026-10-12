from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.verchain import Verchain
    from core.verchainCommunication import VerchainCommunication


class CLI:
    """CLI entry point sharing a Verchain instance's communication services."""

    def __init__(self, verchain: Verchain) -> None:
        self.verchain = verchain
        self.communication: VerchainCommunication = verchain.communication

    def start(self) -> None:
        """Start Verchain's API and peer-to-peer network for CLI use."""
        self.verchain.start()
