
import json, time, threading, uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic_core import ValidationError

from errors.blockErrors import DuplicateBlockError

from models.constants import BOOTSTRAP_NODES
from models.Models import (Action, Block, NodeMetadata,Payload)

from utils.nodeStorageManager import NodeStorageManager
from utils.blocks.blockManager import BlockManager
from errors.holderValidationErrors import ConflictingIdentityError
from services.ledger import Ledger
from services.network import Network
from models.network import NetworkContext
from configs.baseConfigs import defaultSettings

from errors import (
    LedgerCorruptError, LedgerNotFoundError, InvalidChainError
    )



class Peer:
    def __init__(self, title: str, host: str, port: int, bootstrap: bool = False) -> None:
        self.title = title
        self.host = host
        self.port = port
        ledgerFilePath = Path(__file__).resolve().parents[2] / "storage" / f".ledger-{self.title}.json"
        # Packing the storage lists and sets to share it across the services and tools.
        self.receivedLedgers: list = []
        self.receivedLengths: list = []
        self.seenBlocks = set()

        # Use the instance's shared lists so Network/ChainSync update the
        # same collections that Peer methods reference.
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

        # Creating an identity for the current node
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
        if bootstrap:
            BOOTSTRAP_NODES.append((self.host, self.port))

        self.startAPI()

    def startNetwork(self) -> None:
        self.network.start()

    def stopNetwork(self) -> None:
        self.network.stop()

    def connect(self, node: NodeMetadata, host: str = "", port: int = 0) -> None:
        "Connects to a specific node by NodeMetadata, or host and port."

        self.network.connect(node=node, host=host, port=port)


    def requestChainSync(self) -> None:
        "Triggers the chain sync request, cleans the local current local chain."
        self.ledger.shouldRequestChain = True
        self.receivedLedgers.clear()
        self.chainSync.request()

    
    def startAPI(self) -> None:
            app = self.buildAPI()
            thread = threading.Thread(
                target=uvicorn.run,
                args=(app,),
                kwargs={
                    "host": self.host,
                    "port": self.port + 10000,
                    "log_level": "warning"
                },
                daemon=True
            )

            thread.start()



    def buildAPI(self) -> FastAPI:
        from API.router import buildRouter
        app = FastAPI(title=f"Peer Node - {self.title}")
        # Allow the console UI (and other local origins) to call the API.
        # Permit the exact API origin and localhost variants so browser hostname
        # mismatches (localhost vs 127.0.0.1) don't cause CORS failures.
        api_origin = f"http://{self.host}:{self.port + 10000}"
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[api_origin, "http://localhost:" + str(self.port + 10000), "http://127.0.0.1:" + str(self.port + 10000), "*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.include_router(buildRouter(self))

        staticDir = Path(__file__).resolve().parents[1] / "API" / "static"
        app.mount("/console", StaticFiles(directory=staticDir, html=True), name="Console")
        return app

    

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

        except ConflictingIdentityError:
            return ConflictingIdentityError(
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
    from models import Authority, User, Identity, CHID

    issuer = Authority(name="JPUF", businessID=3423)

    user1  = User(name="Local", nationalNumber=1111, phone=1, age=30, email="", birth="")
    doc1   = Identity(image="", credentialID=1)
    block1 = Block(data=CHID(user=user1, credential=doc1, issuer=issuer))


    time.sleep(0.1)
    bashar     = Peer("Bashar",     "localhost", 5001)
    bilal      = Peer("Bilal",      "localhost", 5005)
   

    time.sleep(0.3)

    bashar.startNetwork()        
    bilal.startNetwork()
