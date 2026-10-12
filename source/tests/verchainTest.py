from types import SimpleNamespace

from cli.app import CLI
from core.verchain import Verchain
from core.verchainCommunication import VerchainCommunication


def test_initialization_starts_api_and_start_starts_network(monkeypatch):
    events = []

    class FakeNetwork:
        def __init__(self, *args):
            self.metadata = object()
            self.chainSharing = object()

        def start(self):
            events.append("network")

    monkeypatch.setattr("core.verchain.Ledger", lambda path: SimpleNamespace(shouldRequestChain=False))
    monkeypatch.setattr("core.verchain.BlockManager", lambda *args: object())
    monkeypatch.setattr("core.verchain.NodeStorageManager", lambda *args: object())
    monkeypatch.setattr("core.verchain.Network", FakeNetwork)
    monkeypatch.setattr(
        VerchainCommunication,
        "startAPI",
        lambda self: events.append("api"),
    )

    verchain = Verchain("Test", "localhost", 0)
    assert events == ["api"]

    verchain.start()

    assert events == ["api", "network"]


def test_cli_uses_verchain_start_and_shared_communication():
    events = []
    communication = object()
    verchain = SimpleNamespace(
        communication=communication,
        start=lambda: events.append("started"),
    )

    cli = CLI(verchain)
    cli.start()

    assert cli.communication is communication
    assert events == ["started"]
