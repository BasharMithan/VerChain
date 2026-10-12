
import time
from pathlib import Path

from core.communication import VerchainAPI
from services.ledger import Ledger
from services.network import Network
from services.processor import VerchainProcessor
from utils.blocks.blockManager import BlockManager
from utils.nodeStorageManager import NodeStorageManager
from models.constants import BOOTSTRAP_NODES
from models.network import NetworkContext
from models.Models import Document
from cli.app import CLI
from errors import LedgerCorruptError
from utils.utility_function import normalizeLocalHost


class Verchain:
    def __init__(self, title: str, host: str, port: int, isBootstrap: bool = False) -> None:
        self.title = title
        self.host = normalizeLocalHost(host)
        self.port = port
        ledgerFilePath = Path(__file__).resolve().parents[2] / "storage" / f".ledger-{self.title}.json"
        # Packing the storage lists and sets to share it across the services and tools.
        self.receivedLedgers: list = []
        self.receivedLengths: list = []
        self.seenBlocks = set()

        # Share the collections used by Network and ChainSync with Verchain.
        networkContext = NetworkContext(
            seenBlocks=self.seenBlocks,
            receivedLengths=self.receivedLengths,
            receivedLedgers=self.receivedLedgers,
        )

        ledger_corrupt = False
        try:
            self.ledger = Ledger(ledgerFilePath)
        except LedgerCorruptError:
            # Ledger file is unreadable/corrupt. Reset the file so we can
            # initialize a fresh ledger instance and request a chain sync
            # from peers to recover the correct ledger state.
            print("Ledger-Corruption-Error: resetting ledger file and requesting chain sync")
            ledger_corrupt = True
            ledgerFilePath.parent.mkdir(parents=True, exist_ok=True)
            ledgerFilePath.write_text('', encoding='utf-8')
            self.ledger = Ledger(ledgerFilePath)
            # Ensure chain sync will run to recover ledger contents from peers.
            self.ledger.shouldRequestChain = True


        self.blockManager = BlockManager(self.ledger, self.seenBlocks)
        self.nodeManager = NodeStorageManager(self.title)
        self.network = Network(self.title, self.host, self.port, self.nodeManager, self.blockManager, self.ledger, networkContext)

        # Creating an Credential for the current node
        self.me = self.network.metadata

        self.chainSync = self.network.chainSharing

        # If ledger was corrupt or ledger indicated a need to sync, request chain sync.
        if ledger_corrupt or self.ledger.shouldRequestChain == True:
            try:
                self.chainSync.requestChainSync()
            except Exception:
                # Network may not be started yet; outbound connections will
                # call chain sync when they connect.
                pass

        # A bootstrap node is a node that all nodes should connect to it on the start.
        if isBootstrap:
            BOOTSTRAP_NODES.append((self.host, self.port))

        self.processor = VerchainProcessor(self)
        self.api = VerchainAPI(self)
        self.cli = CLI(self.processor)
        self.api.startAPI()

    def start(self) -> None:
        """Join the peer-to-peer network after API startup during initialization."""
        self.network.start()

if __name__ == "__main__":
    from models import Authority, User, Credential, CHID
    from models.Models import Action, Block, Payload

    issuer = Authority(name="JPUF", businessID=3423)

    user1  = User(name="Local", nationalNumber=1111, phone=1, age=30, email="", birth="")
    doc1   = Credential(
        document=Document(documentFormat="text/plain", documentTitle="", documentContentSize=0, documentHash=""),
        documentID=1,
    )
    block1 = Block(data=CHID(user=user1, credential=doc1, issuer=issuer))


    time.sleep(0.1)
    bashar     = Verchain("Bashar",     "localhost", 5001)
    bilal      = Verchain("Bilal",      "localhost", 5005)
   

    time.sleep(0.3)

    bashar.start()
    bilal.start()
