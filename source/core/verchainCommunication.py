from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models.APIModels import (VerificationRequest, NodeStatus,
                                     ChainModel, APIRegisterationRequest,
                                     )

from pydantic_core import ValidationError

from models.Models import NodeMetadata, Credential, Authority, Block, CHID, Query, Response, User, Document
from services.verifier import Verifier
from utils.blocks.blockManager import BlockManager
from services.documents import DocumentReceiver
from validation.chain_validation import ChainValidation
from errors import DuplicateBlockError, InvalidChainError
from errors.holderValidationErrors import ConflictingCredentialError
from errors.APIErrors import APIError
from errors.credentialErrors import DuplicateCredentialIDError
from validation.inputValidation import InputValidation
from configs.baseConfigs import CredentialConstraints

if TYPE_CHECKING:
    from core.verchain import Verchain


class VerchainCommunication:
    "Handles communication requests from API endpoints and CLI commands."
    def __init__(self, verchain: Verchain) -> None:
        self.verchain = verchain
        self.verifier = Verifier()
        self.inputValidation = InputValidation(self.verchain.ledger)
        self.documentReceiver = DocumentReceiver(constraints=CredentialConstraints())

    def startAPI(self) -> None:
        app = self.buildAPI()
        thread = threading.Thread(
            target=uvicorn.run,
            args=(app,),
            kwargs={
                "host": self.verchain.host,
                "port": self.verchain.port + 10000,
                "log_level": "warning",
            },
            daemon=True,
        )
        thread.start()

    def buildAPI(self) -> FastAPI:
        from API.router import VerchainRouter

        app = FastAPI(title=f"Verchain - {self.verchain.title}")
        apiPort = self.verchain.port + 10000
        apiOrigin = f"http://{self.verchain.host}:{apiPort}"
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                apiOrigin,
                f"http://localhost:{apiPort}",
                f"http://127.0.0.1:{apiPort}",
                "*",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.include_router(VerchainRouter(self.verchain, self))
        staticDir = Path(__file__).resolve().parents[1] / "API" / "static"
        app.mount("/console", StaticFiles(directory=staticDir, html=True), name="Console")
        return app

    def processVerificationRequest(self, verificationRequest: VerificationRequest) -> Response | APIError:
        # Looping over the local chain to locate the block that contains all the information.
        user = self.verchain.ledger.findUser(verificationRequest.userID, verificationRequest.user)
        credential = self.verchain.ledger.findCredential(verificationRequest.document.documentHash)
        issuer = self.verchain.ledger.findIssuer(verificationRequest.issuerID, verificationRequest.issuer)


        if not user:
            return APIError(error="User-not-found", message="The input user is not registered.")

        if not credential:
            return APIError(error="Credential-not-found", message="The input credential is not registered.")

        if not issuer:
            return APIError(error="Issuer-not-found", message="The input issuer is not registered.")

        

        # execute only if the User, Credential, and the Authority are stored on-chain.
        query = Query(user=user, credential=credential, issuer=issuer)
        return self.verifier.check(query, self.verchain.ledger.blocks)
        


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
            result: Block | Exception | None = self.verchain.registerBlock(block)
        except (DuplicateBlockError, DuplicateCredentialIDError, InvalidChainError, ConflictingCredentialError, ValidationError) as error:
            result = error
        if result is None:
            return APIError(error = "Block-building-fail", message = "Cannor build the block.")
        
        if isinstance(result, DuplicateBlockError):
            return APIError(error="Block-duplication-error", message="Block already exists.")

        elif isinstance(result, DuplicateCredentialIDError):
            return APIError(error="Duplicate-Credential-ID", message=str(result))

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

        name: str = self.verchain.title
        host, port = self.verchain.host, self.verchain.port

        ledger: list = self.verchain.ledger.blocks
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
