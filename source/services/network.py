from p2pnetwork.node import Node
from typing import Callable
import time

from models.Models import NodeMetadata, Payload

from utils.nodeStorageManager import NodeStorageManager
from utils.networkUtils import NetworkCallbacks, buildNodeInformation
from utils.interaction import Interaction
from models.events import InteractionContext
from utils.blocks.blockManager import BlockManager
from utils.chain.chainSync import ChainSync
from services.ledger import Ledger
from models.network import NetworkContext
from models.Models import NodeConnectionType, DiscoverMessage, Action
from configs.baseConfigs import defaultSettings



class Network(Node):
    "Manages the netowrking functionalities."
    def __init__(self, title: str, host: str, port: int,
                 nodeManager: NodeStorageManager, blockManager: BlockManager,
                 ledgerInstance: Ledger,
                 networkContext: NetworkContext) -> None:
        
        self.title = title
        self.host = host
        self.port = port

        if self.host == "localhost": self.host = "127.0.0.1"

        self.nodeManager = nodeManager
        self.blockManager = blockManager
        self.ledger = ledgerInstance
        self.networkContext = networkContext

        super(Network, self).__init__(host=self.host, port=int(self.port), callback=None)

        self.metadata: NodeMetadata = buildNodeInformation(self.title, self)
        self.networkCallbacks = NetworkCallbacks(self.nodeManager)

        self.chainSharing = ChainSync(self.ledger, self, self.networkContext.receivedLedgers,
                                      self.networkContext.receivedLengths, self.metadata)
        


    def start(self) -> None:
        super().start()
        time.sleep(0.1)
        self.bootstrapConnection()


    def sendDiscover(self, toAll: bool = True) -> None:
        self.broadcast(
            message=Payload(action=Action.discover.value, data=DiscoverMessage(sender=self.metadata, toAll=toAll)),
            exclude=[]
        )



    def isConnected(self, node: NodeMetadata) -> bool:
        """Return True when the given node is already connected to this node."""
        if not node:
            return False

        for connection in self.all_nodes:
            if connection.host == node.host and int(connection.port) == int(node.port):
                return True

        return False




    def isSelf(self, node: NodeMetadata | None = None, host: str = "", port: int = 0) -> bool:
        """Return True when the target appears to be this node."""
        if node is not None:
            return node.host == self.host and int(node.port) == int(self.port)

        return host == self.host and int(port) == int(self.port)




    def connect(self, node: NodeMetadata | None = None, host: str = "", port: int = 0) -> bool: 

        "Tiggers a connection to another node."
        if node is not None:
            if self.isSelf(node=node):
                return False 

            if self.isConnected(node):
                return False

            targetNode = NodeStorageManager.metadataToNodeConnection(node, self.all_nodes)

            if targetNode:
                self.connect_with_node(targetNode.host, targetNode.port)
                return True
            
            return False

        if host and port:
            if self.isSelf(host=host, port=port):
                return False

            candidateNode = NodeMetadata(
                name="Unknown",
                nodeID="",
                host=host,
                port=port,
                connectionType=NodeConnectionType.outbound,
            )
            if self.isConnected(candidateNode):
                return False

            self.connect_with_node(host=host, port=port)
            return True
        return False


    def broadcast(self, message: Payload, exclude: list[NodeMetadata]) -> bool:
        "Broadcasts a certain message to the peer-to-peer network."

        excludedNodes = [NodeStorageManager.metadataToNodeConnection(node, self.all_nodes) for node in exclude]

        try:
            validPayload: dict = message.model_dump(mode="json")

            self.send_to_nodes(data=validPayload, exclude=excludedNodes)

            return True
        except Exception as error:
            return False




    def send(self, to: NodeMetadata, message: Payload) -> None:
        "Sends a message to a specific node."

        targetNode = NodeStorageManager.metadataToNodeConnection(to, self.all_nodes)
        if targetNode is None:
            return
        self.send_to_node(targetNode, message.model_dump(mode="json"))


    def node_message(self, node, data):
        interactionContext = InteractionContext(
            network=self,
            blockManager=self.blockManager,
            chainSync=self.chainSharing,
            nodeManager=self.nodeManager,
            seenBlocks=self.networkContext.seenBlocks,
            receivedLengths=self.networkContext.receivedLengths,
            receivedLedgers=self.networkContext.receivedLedgers,
            me=self.metadata,
            connections=self.all_nodes,
            sender=node
        )


        interaction = Interaction(interactionContext)

        payload = Payload.model_validate(data)

        
        interaction.handle(payload=payload,
                           sender=NodeStorageManager.nodeConnectionToMetadata(node, NodeConnectionType.outbound))


    def bootstrapConnection(self) -> None:
        for host, port in defaultSettings.connection.bootstrapPeers:
            self.connect(host=host, port=port)



    def outbound_node_connected(self, node):
        self.chainSharing.hasSynced = False

        self.networkCallbacks.outboundConnectionCallback(self.nodes_outbound)
        self.sendDiscover(toAll=True)

        if not self.chainSharing.hasSynced:
            self.chainSharing.request()
        return super().outbound_node_connected(node)


    def inbound_node_connected(self, node):
        self.networkCallbacks.inboundConnectionCallback(self.nodes_inbound)
        return super().inbound_node_connected(node)



