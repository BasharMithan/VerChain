from models.APIModels import (VerificationRequest, NodeStatus,
                                     ChainModel, APIRegisterationRequest,
                                     )

from pydantic_core import ValidationError

from services.peer import Peer
from models.Models import NodeMetadata, Credential, Authority, Block, CHID, Query, Response, User, Document
from services.verifier import Verifier
from utils.blocks.blockManager import BlockManager
from utils.chain.documents import DocumentReceiver
from validation.chain_validation import ChainValidation
from errors import DuplicateBlockError, InvalidChainError
from errors.holderValidationErrors import ConflictingCredentialError
from errors.APIErrors import APIError
from validation.inputValidation import InputValidation
from configs.baseConfigs import CredentialConstraints



class APICommunication:
    "Responsable for responding to API messages and nalysing the incoming data from the API"
    def __init__(self, peer: Peer) -> None:
        self.peer = peer
        self.verifier = Verifier()
        self.inputValidation = InputValidation(self.peer.ledger)
        self.documentReceiver = DocumentReceiver(constraints=CredentialConstraints())
        


    
    def processVerificationRequest(self, verificationRequest: VerificationRequest) -> Response | APIError:


        # Looping over the local chain to locate the block that contains all the information.
        user = self.peer.ledger.findUser(verificationRequest.UserID, verificationRequest.user)
        credential = self.peer.ledger.findCredential(verificationRequest.documentID)
        issuer = self.peer.ledger.findIssuer(verificationRequest.issuerID, verificationRequest.issuer)


        if not user:
            return APIError(error="User-not-found", message="The input user is not registered.")

        if not credential:
            
            return APIError(error="Credential-not-found", message="The input credential is not registered.")

        if not issuer:
            return APIError(error="Issuer-not-found", message="The input issuer is not registered.")

        

        # execute only if the User, Credential, and the Authority are stored on-chain.
        query = Query(user=user, credential=credential, issuer=issuer)
        return self.verifier.check(query, self.peer.ledger.blocks)
        



    def processBlockRegisterationRequest(self, registerationRequest: APIRegisterationRequest, document: Document) -> Block | APIError:
        "Takes the `RegisterationRequest` received from the API, builds the block and registers it on the chain."



        # Converting the data models from API models to the data models that are recognized by the network.
        try:
            user = User(
                name=registerationRequest.userName,
                age=registerationRequest.age,
                nationalNumber=registerationRequest.nationalNumber,
                phone=registerationRequest.phone,
                email=registerationRequest.email,
                birth=registerationRequest.birth,
                HID=""
                )

            issuer = Authority(
                name=registerationRequest.issuerName,
                businessID=registerationRequest.issuerID,
                AUTHID=""
            )


            doc = Credential(
                documentID=registerationRequest.documentID,
                document=document, CID="" )



        except ValidationError:
            return APIError(error = "Validation-error", message = "Input data is not valid.")

        if not self.inputValidation.holderValidation(user=user):
            return APIError(error = "Validation-Error", message = "User input is invalid")

        if not self.inputValidation.credentialValidation(credential=doc):
            return APIError(error = "Validation-Error", message = "Credential input is invalid")

        if not self.inputValidation.issuerValidation(issuer=issuer):
            return APIError(error = "Validation-Error", message = "Issuer input is invalid")
        

        block = Block(
            data=CHID(
                user=user,
                credential=doc,
                issuer=issuer,
                chid=""
            )
        )

        
        try:
            result: Block | Exception | None = self.peer.registerBlock(block)
        except (DuplicateBlockError, InvalidChainError, ConflictingCredentialError, ValidationError) as error:
            result = error
        if result is None:
            return APIError(error = "Block-building-fail", message = "Cannor build the block.")
        
        if isinstance(result, DuplicateBlockError):
            return APIError(error="Block-duplication-error", message="Block already exists.")

        elif isinstance(result, InvalidChainError):
            return APIError(error = "Invalid-Chain", message = "Chain integrity failed; chain sync requested.")

        elif isinstance(result, ConflictingCredentialError):
            return APIError(error = "Conflict-Credential", message = "Check if the input is valid.")

        elif isinstance(result, ValidationError):
            return APIError(error = "Validation-error", message =  "Input is invalid")
        
        elif isinstance(result, Exception):
            return APIError(error =  "Internal-Error", message = "Internal node error. Try again.")

        return result

    
    def sendNodeStatus(self) -> NodeStatus:
        "Returns the NodeStatus model to the API router."

        name: str = self.peer.title
        host, port = self.peer.host, self.peer.port

        ledger: list = self.peer.ledger.blocks
        cv = ChainValidation(ledger)

        chainValidity: bool = cv.validate()

        blocksCount: int = len(ledger)

        return NodeStatus(
            name=name,
            host=host,
            port=port,
            chainValidity=chainValidity,
            blocksCount=blocksCount
        )


    @staticmethod
    def sendChain(node: NodeMetadata, blockManager: BlockManager) -> ChainModel:
        return ChainModel(sender=node, chain=blockManager.ledger.blocks)



