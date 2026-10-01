from datetime import datetime
from pathlib import Path
from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, model_validator, Field, EmailStr
from p2pnetwork.nodeconnection import NodeConnection
from typing import Any

from utils.generators import IDGenerator
from models.constants import TARGET


   

class User(BaseModel):
    name: str
    nationalNumber: int
    phone: int
    age: int
    email: EmailStr
    birth: str
    HID: str = ""

    @model_validator(mode="after")
    def __post_init__(self) -> "User":
        if (self.HID == ""):
            self.HID = IDGenerator.generateID(f"{self.name}:{self.nationalNumber}{self.birth}")
        return self

    class Confing:
        frozen = True

    def __hash__(self) -> int:
        return hash((self.name, self.nationalNumber))




class Authority(BaseModel):
    name: str
    businessID: int
    AUTHID: str = ""

    @model_validator(mode="after")
    def __post_init__(self) -> "Authority":

        

        if (self.AUTHID == ""):
            self.AUTHID = IDGenerator.generateID(f"{self.name}:{self.businessID}")
        return self



class Document(BaseModel):
    documentTitle: str | None = None
    documentType: str | None = None
    documentFormat: str | None = None
    documentContentSize: int = 0
    documentContent: bytes | None = None
    documentHash: str = ""

    @model_validator(mode="after")
    def __post_init__(self) -> "Document":
        if self.documentHash == "":
            self.documentHash = f"{self.documentTitle}:{self.documentContent}:{self.documentContentSize}"

        return self


class Identity(BaseModel):
    # user: User
    # issuer: Authority
    image: str
    credentialID: int
    CID: str = ""

    document: Document = Document()
    


    @model_validator(mode="after")
    def __post_init__(self) -> "Identity":
        if (self.CID == ""):
            self.CID = IDGenerator.generateID(f"{self.document.documentTitle}:{self.credentialID}:{self.document.documentContentSize}") 

        return self


class CHID(BaseModel):
    user: User
    credential: Identity
    issuer: Authority
    chid: str = ""

    @model_validator(mode="after")
    def __post_init__(self) -> "CHID":
        self.chid = IDGenerator.generateCHID(
            self.user.HID,
            self.credential.CID, 
            self.issuer.AUTHID
            )
        return self


class Block(BaseModel):
    """The standard schema that the user will fill,
    and prcessed and inserted to the ledger."""
    data: CHID

    index: int = 0
    nonce: int = 0
    previousHash: str = ""
    date: str = Field(default_factory=lambda: str(datetime.now()))
    hash: str = ""

    @model_validator(mode="after")
    def __post_init__(self) -> "Block":

        # Do not mutate persisted block indexes during model validation.
        # Index assignment for new blocks is handled explicitly by the
        # Block creator (BlockManager / Ledger) before mining/insertion.
        return self

    def computeHash(self) -> str:
        """Recomputable hash that includes nonce."""
        content = f"{self.index}{self.data.chid}{self.nonce}{self.previousHash}"
        return IDGenerator.generateID(content)

    # In Block (Models.py)

    def isHashValid(self) -> bool:
        """Hash matches a recomputation of this block's contents."""
        return self.hash == self.computeHash()

    def isMined(self) -> bool:
        """Hash satisfies the proof-of-work target."""
        return self.hash.startswith(TARGET)



class Response(Enum):
    appove = "APPROVED"
    decline = "DECLINED"


class Action(Enum):
    registeration = "REGISTERATION"
    query = "QWERY"
    hold = "HOLD"
    BlockBroadcast = "BLOCK-BROADCAST"
    discover = "DISCOVER"
    syncPeer = "SYNC-PEER"

    chainSyncRequest = "CHAIN-SYNC-REQUEST"
    chainSyncResponse = "CHAIN-SYNC-RESPONSE"

    chainLenghRequest = "CHAIN-LEDGTH-REQUEST"
    chainLenghResponse = "CHAIN-LENGTH-RESPONSE"

    @staticmethod
    def getactionsaslist() -> list:
        "Get all actions as list"
        return [action.value for action in Action]


class Query(BaseModel):
    user: User
    credential: Identity
    issuer: Authority
       

class NodeConnectionType(Enum):
    inbound = "INBOUND"
    outbound = "OUTBOUND"

class NodeMetadata(BaseModel):
    name: str
    nodeID: str
    host: str
    port: int
    connectionType: NodeConnectionType
    discoverDate: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PeerRecord(BaseModel):
    title: str
    metadata: NodeMetadata
    ledgerLocation: Path
    knownPeers: list
    status: str



class DiscoverMessage(BaseModel):
    sender: NodeMetadata
    toAll: bool = False


class PeerSyncResponse(BaseModel):
    sender: NodeMetadata
    connectedPeers: list[NodeMetadata]
    to: NodeMetadata
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


    
class ChainSyncRequest(BaseModel):
    sender: NodeMetadata


class ChainSyncResponse(BaseModel):
    sender: NodeMetadata
    ledger: list
    length: int




class Payload(BaseModel):
    action: str | Action
    data: Any