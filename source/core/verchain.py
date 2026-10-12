
import time
from pathlib import Path
from pydantic_core import ValidationError

from errors.blockErrors import DuplicateBlockError

from models.constants import BOOTSTRAP_NODES
from models.Models import Action, Block, Payload

from utils.nodeStorageManager import NodeStorageManager
from utils.blocks.blockManager import BlockManager
from errors.holderValidationErrors import ConflictingCredentialError
from errors.credentialErrors import DuplicateCredentialIDError
from services.ledger import Ledger
from services.network import Network
from models.network import NetworkContext
from core.verchainCommunication import VerchainCommunication
from cli.app import CLI

from errors import (
    LedgerCorruptError, InvalidChainError
)



class Verchain:
    def __init__(self, title: str, host: str, port: int, isBootstrap: bool = False) -> None:
        self.title = title
        self.host = host
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

        # The p2pnetwork only uses the local host: "127.0.0.1".
        if self.host == "localhost":
            self.host = "127.0.0.1"

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
                self.chainSync.request()
            except Exception:
                # Network may not be started yet; outbound connections will
                # call chain sync when they connect.
                pass

        # A bootstrap node is a node that all nodes should connect to it on the start.
        if isBootstrap:
            BOOTSTRAP_NODES.append((self.host, self.port))

        self.communication = VerchainCommunication(self)
        self.cli = CLI(self)
        self.communication.startAPI()

    def start(self) -> None:
        """Join the peer-to-peer network after API startup during initialization."""
        self.network.start()

    def requestChainSync(self) -> None:
        "Triggers the chain sync request, cleans the local current local chain."
        self.ledger.shouldRequestChain = True
        self.receivedLedgers.clear()
        self.chainSync.request()

    def registerBlock(self, block: Block) -> Block | None | Exception:
        "Registers a block on-chain."

        try:
            resultBlock: Block = self.blockManager.registerBlock(block)

        except InvalidChainError:
            # Request a chain sync and retry once. If the chain is still
            # invalid after the retry, return an InvalidChainError instance
            # so the caller can respond appropriately instead of letting
            # the exception bubble up to the ASGI server.
            self.requestChainSync()
            time.sleep(0.2)
            
            resultBlock: Block = self.blockManager.registerBlock(block)

        except DuplicateBlockError:
            return DuplicateBlockError(block.data.chid)

        except DuplicateCredentialIDError:
            return DuplicateCredentialIDError(block.data.credential.documentID)

        except ConflictingCredentialError:
            return ConflictingCredentialError(
                nationalNumber=block.data.user.nationalNumber,
                existingName="",
                incomingName=""
            )

        except ValidationError:
            return ValidationError()

        if self.blockManager.shouldBoradcast(block):
            # Broadcasting a block to all connecting nodes.
            self.network.broadcast(Payload(action=Action.BlockBroadcast.value, data=block), [])

            # Adding the block to the seenBlocks set to prevent broadcast loop.
            self.seenBlocks.add(block.data.chid)
            return resultBlock

        


if __name__ == "__main__":
    from models import Authority, User, Credential, CHID, Document

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
