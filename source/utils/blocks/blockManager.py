from p2pnetwork.node import Node

from models.Models import Block, Action
from services.ledger import Ledger
from utils.logger import Logger
from utils.blocks.miner import Miner
from validation.chain_validation import ChainValidation
from validation.blockValidation import BlockValidator
from validation.inputValidation import InputValidation
from errors.holderValidationErrors import ConflictingCredentialError

from errors import DuplicateBlockError, BlockPreviousHashError


class BlockManager:
    """Manages the block functionalities and validates if the inserted block is valid."""

    def __init__(self, ledgerInstance: Ledger, seenBlocks: set) -> None:
        # BlockManager expects a Ledger instance. The Ledger object encapsulates
        # the file path and persistence details; callers should create the
        # Ledger and pass it here.
        self.ledger = ledgerInstance
        self.miner = Miner()
        self.seenBlocks = seenBlocks
        self.inputValidation = InputValidation(ledger=self.ledger)
        

    def registerBlock(self, block: Block) -> Block:

        with self.ledger._lock:
            block.index = len(self.ledger.blocks)
            block.previousHash = self.ledger.getLatestHash()

            if not self.inputValidation.holderValidation(user=block.data.user):
                raise ConflictingCredentialError(nationalNumber=block.data.user.nationalNumber, existingName="", incomingName="")

            if self.checkIfBlockExists(block.data.chid, self.ledger.blocks):
                Logger.warning(f"[Block validation] The block {block.index} already in the ledger!")
                raise DuplicateBlockError(block.data.chid)

            minedBlock = self.miner.mine(block)

            self.ledger.insertBlock(minedBlock)

        return minedBlock

    def receiveBlock(self, block: Block) -> Block | None:

        """
        Receives the block from the network and the API,
        checks it's validity and adds it to the chain.
        """

        if self.checkIfBlockExists(block.data.chid, self.ledger.blocks):
            raise DuplicateBlockError(block.data.chid)

        blockValidation = BlockValidator()
        try:
            blockValidation.validate(block, self.ledger.blocks[-1]["hash"])
        except BlockPreviousHashError:
            return

        self.ledger.insertBlock(block)
        Logger.info(f"[Block Validation] Received block {block.index} inserted.")
        return block




    @classmethod  
    def checkIfBlockExists(cls, targetCHID: str, blocks: list) -> bool:
        return any(targetCHID == b.get("data", {}).get("chid") for b in blocks)
        
    def shouldBoradcast(self, block: Block) -> bool:

        if block.data.chid in self.seenBlocks:
            return False
        else:
            self.seenBlocks.add(block.data.chid)
            return True


    """
    def broadcastBlock(self, block: Block) -> None:

        self.network.send_to_nodes(
            {
                "action": Action.BlockBroadcast.value,
                "data": block.model_dump(mode="json")
            }
        )"""