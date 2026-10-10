import json
import threading
from pathlib import Path
from typing import Any 
from pydantic import ValidationError

from utils.logger import Logger
from validation.chain_validation import ChainValidation
from utils.blocks.miner import Miner
from models.Models import Block, CHID, Authority, User, Credential, Document

from errors import (
    BlockNotMinedError,
    BlockHashMismatchError,
    BlockPreviousHashError,
    LedgerNotFoundError,
    LedgerCorruptError,
    InvalidChainError,
    GenesisBlockError,
    DuplicateBlockError,
    )

from errors.blockErrors import BlockIntegrationError

from configs import settings, Performance



class Ledger():

    def __init__(self, filePath: Path) -> None:
        # store Block instances (or loaded dicts); start empty
        self.blocks: list[dict[str, Any]] = []
        self.filePath: Path = filePath
        self._lock = threading.RLock() # A lock to prevent concurrent insert/write race in the same ledger instance.

        self.chainValidation = ChainValidation(chain=self.blocks)

        self.users: dict[int, User] = {}
        self.usersByNationalNumber: dict[int, User] = {}
        self.usersByUsername: dict[str, User] = {}

        self.credentials: dict[str, Credential] = {}
        self.issuers: dict[int, Authority] = {}

        self.miner = Miner()

        self.shouldRequestChain = False

        self.__initLedger()
        self.__loadLedger()
        self.__ensureGenesis()

        self.loadFromLedger()


        if not self.chainValidation.validate():
            self.shouldRequestChain = True
            raise InvalidChainError(reason="The local chain is invalid.")
        


    def __initLedger(self) -> None:
        if not self.filePath.is_file():
            self.__createFileIfnotExist()
            self.__generateGensisBlock()


    def __ensureGenesis(self) -> None:
        if len(self.blocks) == 0:
            self.__generateGensisBlock()



    def __loadLedger(self) -> None:
        """Reads the values from the json file and loads them into `self.blocks`.

        Currently loads raw JSON structures (dicts/lists). Reconstructing
        dataclass `Block` objects could be added later if needed.
        """
        try:
            text = self.filePath.read_text(encoding='utf-8').strip()
           
            if not text:
                Logger.warning("[Ledger] The ledger is empty !")
                return

            data = json.loads(text)
            if isinstance(data, list):
                self.blocks.clear()
                self.blocks.extend(data)
            else:
                self.shouldRequestChain = True
                raise LedgerCorruptError(str(self.filePath))
            
        except json.JSONDecodeError as error:
            self.shouldRequestChain = True
            raise LedgerCorruptError(str(self.filePath)) from error


    def __createFileIfnotExist(self) -> None:
            try:
                # ensure parent exists
                self.filePath.parent.mkdir(parents=True, exist_ok=True)
                self.filePath.write_text('', encoding='utf-8')
            except OSError as error:
                self.shouldRequestChain = True
                raise LedgerNotFoundError(str(self.filePath)) from error


    def insertBlock(self, block: Block) -> Block:
        with self._lock:

            blockAsDict = json.loads(Block.model_dump_json(block))
            blockChid = blockAsDict.get("data", {}).get("chid")

            if any(existing.get("data", {}).get("chid") == blockChid for existing in self.blocks):
                Logger.warning(f"[Ledger] Block with CHID {blockChid} already exists; refusing duplicate insert.")
                raise DuplicateBlockError(blockChid)


            if (settings.performance == Performance.safe):
                try:
                    self.chainValidation.chain = self.blocks
                    self.chainValidation.validate()
                except (BlockNotMinedError, BlockHashMismatchError, BlockPreviousHashError) as reason:
                    raise BlockIntegrationError(block=block, reason=reason) from reason

            


            self.blocks.append(blockAsDict)

            self.users[block.data.user.nationalNumber] = block.data.user
            self.credentials[block.data.credential.document.documentHash] = block.data.credential
            self.issuers[block.data.issuer.businessID] = block.data.issuer

            self.__writeBlockToLedger(blockAsDict)

            return block


    def __writeBlockToLedger(self, block: dict) -> None:
        with open(self.filePath, "w", encoding="utf-8") as ledgerFile:
            json.dump(self.blocks, ledgerFile, indent=4)
        Logger.info(f"Block with CHID {block['data']} inserted successfully. ")


    def allBlocks(self) -> list:
        return self.blocks
      



    def getLatestHash(self) -> str:
        "Return the latest block's hash."
        return self.blocks[-1]["hash"]
            

    
    def __generateGensisBlock(self) -> None:
        user=User(name="Gensis-Block", nationalNumber=0, phone=0, age=0, email="gensis@blockchain.io", birth="")
        auth = Authority(name="", businessID=0)
        doc = Credential(
            document=Document(documentFormat="text/plain", documentTitle="", documentHash=""),
            documentID=0,
        )
        chid = CHID(user=user, credential=doc, issuer=auth)

        block = Block(data=chid)
        # Ensure genesis block has correct index and previousHash before mining
        block.index = 0
        block.previousHash = "0"*64

        try:

            mined = self.miner.mine(block)
            self.insertBlock(mined)
        except Exception as error:
            self.shouldRequestChain = True
            raise GenesisBlockError(str(error)) from error


    def loadFromLedger(self) -> None:
        """Reads the local ledger and stores the user, credentials, and issuers' indecies
        to build the index tables."""

        self.users.clear()
        self.usersByNationalNumber.clear()
        self.usersByUsername.clear()
        self.credentials.clear()
        self.issuers.clear()

        try:
            for block in self.blocks:
                self.users[block["data"]["user"]["nationalNumber"]] = User.model_validate(block["data"]["user"])
                self.usersByNationalNumber[block["data"]["user"]["nationalNumber"]] = User.model_validate(block["data"]["user"])

                documentHash = block["data"]["credential"]["document"]["documentHash"]
                self.credentials[documentHash] = Credential.model_validate(block["data"]["credential"])
                self.issuers[block["data"]["issuer"]["businessID"]] = Authority.model_validate(block["data"]["issuer"])
        except ValidationError as error:
            raise LedgerCorruptError(str(self.filePath)) from error

    def updateLedger(self, newLedger: list) -> None:
        """Defined to meet the requirements of the `ChainSync` class, where it replaces
        the current ledger, with a ledger that has been choosen by the `ChainSync` class.
        """
        replacement = list(newLedger)
        self.blocks.clear()
        self.blocks.extend(replacement)

        with open(self.filePath, "w", encoding="utf-8") as ledgerFile:
            json.dump(newLedger, ledgerFile, indent=4)

        self.shouldRequestChain = False
        
        self.users: dict[int, User] = {}
        self.credentials: dict[str, Credential] = {}
        self.issuers: dict[int, Authority] = {}

        self.loadFromLedger()




    def findUser(self, nationalNumber: int, username: str) -> User | None:
        userByNA =  self.users.get(nationalNumber, None)

        if userByNA:
            if userByNA.name == username:
                return userByNA
        return None


    def findCredential(self, documentHash: str) -> Credential | None:
        return self.credentials.get(documentHash, None)

    def findIssuer(self, issuerID: int, issuerName: str) -> Authority | None:
        issuer = self.issuers.get(issuerID, None)

        if issuer is None:
            return None

        if issuer.name == issuerName:
            return issuer
        
        else: return None





