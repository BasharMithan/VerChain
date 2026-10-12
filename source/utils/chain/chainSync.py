from p2pnetwork.node import Node

from services.ledger import Ledger
from validation.chain_validation import ChainValidation
from validation.blockValidation import BlockValidator
from utils.nodeStorageManager import NodeStorageManager
from models.Models import (ChainSyncResponse, ChainSyncRequest, Action, NodeMetadata
                                  )

from errors import BlockHashMismatchError, BlockPreviousHashError, GenesisBlockError



class ChainSync:
    """The ledger sharing mechanism, shares the local ledger with the new nodes,
    and receives the ledger sharing requests if it's the new node."""

    def __init__(self, ledger: Ledger, network: Node, receivedLedgers: list, receivedLengths: list, me: NodeMetadata) -> None:
        self.ledger = ledger
        self.network = network # Node object to have the ability to send payloads to the network.
        self.receivedLedgers: list = receivedLedgers
        self.receivedLengths = receivedLengths
        self.me: NodeMetadata = me
        self.hasSynced = False
    

        self.expectedResponses: int = 0 # Keeps track of the number of connected nodes. 

    def request(self) -> None:
        """Requests the ledger from all the connected nodes. If the current node
           is a new node, or the ledger seems to be invalid or the whole ledger
           is missing.
           """

        self.ledger.shouldRequestChain = True

        self.hasSynced = True

        self.expectedResponses = len(self.network.all_nodes)

        message = ChainSyncRequest(sender=self.me)

        # Requsting the ledger to all connected nodes.
        self.network.send_to_nodes({
            "action": Action.chainSyncRequest.value,
            "data": message.model_dump(mode="json")
        }, exclude=[NodeStorageManager.metadataToNodeConnection(self.me, self.network.all_nodes)]) 


    def requestChainSync(self) -> None:
        """Mark the local chain for synchronization, clear stale responses, and request peers."""
        self.ledger.shouldRequestChain = True
        self.receivedLedgers.clear()
        self.request()


    def receive(self, response: ChainSyncResponse) -> None:
        """Reads the chain sync response message, saves the received ledger with all other
        received ledger, the chooses the best ledger among all the received ledger to be set
        as the ledger of the current node."""

        if not self.ledger.shouldRequestChain:
            return

        if not self.checkChainValidation(response.ledger):
            return
        
        if len(response.ledger) < len(self.ledger.blocks):
            return

        # Store the received ledger.
        self.receivedLedgers.append(response.ledger)

        # Check if the main contidion to say that the request has been sent to all nodes.
        if (len(self.receivedLedgers) >= self.expectedResponses):

            choosenChain = self.__chooseBestLedger(self.receivedLedgers) 

            self.ledger.shouldRequestChain = False
            self.ledger.updateLedger(choosenChain)
            self.receivedLedgers.clear()




    def send(self, request: ChainSyncRequest) -> None:
        """Reads the received request, and responds to it."""

        copiedLedger: list = self.copyChain()

        response: ChainSyncResponse = ChainSyncResponse(sender=self.me, ledger=copiedLedger, length=len(copiedLedger))

        # Checks the validity of the local ledger before sending it.
        if self.checkChainValidation(copiedLedger):

            # The given node is a NodeMetadata, converting it to NodeConnection
            targetNode = NodeStorageManager.metadataToNodeConnection(request.sender, self.network.all_nodes)

            # Sending a copy of the local ledger to the node requested it.
            self.network.send_to_node(targetNode, {
                "action": Action.chainSyncResponse.value,
                "data": response.model_dump(mode="json")
                })

        else:
            # The local chain is ivalid. So the dosen't send it.
            pass

            

    def compareReceivedChain(self, receivedChain: list) -> bool:
        """Compares the received (choosen chain) chain with the local chain,
        if the received chain is more valid than the local chain we replace it.
        Else, nothing happens."""

        localChain = self.ledger.blocks

        chainValidator = ChainValidation(receivedChain)

        if (chainValidator.validate()) and len(receivedChain) > len(localChain):
            return True
        return False
            


    def __chooseBestLedger(self, ledgers: list) -> list:
        """Takes the collection of chains, and returns what it calls **the best chain**.
           The best chain is the chain that is valid, and is the longest (Contains more nodes).
           If all the chains are equl, it chooses any
           (Only if all the received chains are equl and all valid)."""

        # Loop through the received ledgers and extract the valid ones.
        validLedgers = [vl for vl in ledgers if self.checkChainValidation(vl)]

        if not validLedgers:
            return self.ledger.blocks # Keep the local ledger if the validLedgers list is empty.

        return max(validLedgers, key=len) # Longest valid chain wins.
    

    def copyChain(self) -> list:
        """Returns a deep copy of the current stored ledger `ledger.nodes`."""
        import copy

        local = self.ledger.blocks
        return copy.deepcopy(local)


    def checkChainValidation(self, ledger: list) -> bool:
        """Last step in the chain sync response. Checks the validity of the chain before
        sending to the node that requested it, and the received chain, if it's not valid, we dont send it. 
        # TODO: Implenent the message that must be sent if the local ledger is not valid."""

        try:
            # `ChainValidation.validate()` returns a boolean and may also
            # raise specific block/chain exceptions. Return the boolean
            # result, and treat any raised validation exceptions as invalid.
            return ChainValidation(ledger).validate()
        except (BlockHashMismatchError, BlockPreviousHashError, GenesisBlockError):
            return False
