from __future__ import annotations

import time
from typing import TYPE_CHECKING

from configs.baseConfigs import CredentialConstraints
from errors import InvalidChainError
from errors.APIErrors import APIError
from errors.blockErrors import DuplicateBlockError
from errors.credentialErrors import DuplicateCredentialIDError
from errors.holderValidationErrors import ConflictingCredentialError
from models.APIModels import APIRegisterationRequest, ChainModel, NodeStatus, VerificationRequest
from models.Models import Authority, Block, CHID, Credential, Document, Query, Response, User
from pydantic_core import ValidationError
from fastapi import UploadFile
from services.documents import DocumentReceiver
from services.verifier import Verifier
from validation.chain_validation import ChainValidation
from validation.inputValidation import InputValidation

if TYPE_CHECKING:
    from core.verchain import Verchain


class VerchainProcessor:
    """Processes API and CLI operations for a Verchain node."""

    def __init__(self, verchain: Verchain) -> None:
        self.verchain = verchain
        self.verifier = Verifier()
        self.inputValidation = InputValidation(verchain.ledger)
        self.documentReceiver = DocumentReceiver(constraints=CredentialConstraints())

    async def receiveDocument(self, uploadedFile: UploadFile, documentID: int) -> Document:
        return await self.documentReceiver.receive(uploadedFile=uploadedFile, documentID=documentID)

    def start(self) -> None:
        """Start the node's peer-to-peer network."""
        self.verchain.start()

    def registerBlock(self, block: Block) -> Block | None | Exception:
        """Register a block, synchronize and retry once on an invalid chain, then broadcast it."""
        try:
            resultBlock: Block = self.verchain.blockManager.registerBlock(block)
        except InvalidChainError:
            self.verchain.chainSync.requestChainSync()
            time.sleep(0.2)
            resultBlock = self.verchain.blockManager.registerBlock(block)
        except DuplicateBlockError:
            return DuplicateBlockError(block.data.chid)
        except DuplicateCredentialIDError:
            return DuplicateCredentialIDError(block.data.credential.documentID)
        except ConflictingCredentialError:
            return ConflictingCredentialError(
                nationalNumber=block.data.user.nationalNumber,
                existingName="",
                incomingName="",
            )
        except ValidationError:
            return ValidationError()

        if self.verchain.network.broadcastBlock(block):
            return resultBlock

    def processVerificationRequest(
        self,
        verificationRequest: VerificationRequest,
    ) -> Response | APIError:
        user = self.verchain.ledger.findUser(verificationRequest.userID, verificationRequest.user)
        credential = self.verchain.ledger.findCredential(verificationRequest.document.documentHash)
        issuer = self.verchain.ledger.findIssuer(verificationRequest.issuerID, verificationRequest.issuer)

        if not user:
            return APIError(error="User-not-found", message="The input user is not registered.")
        if not credential:
            return APIError(error="Credential-not-found", message="The input credential is not registered.")
        if not issuer:
            return APIError(error="Issuer-not-found", message="The input issuer is not registered.")

        query = Query(user=user, credential=credential, issuer=issuer)
        return self.verifier.check(query, self.verchain.ledger.blocks)

    def processBlockRegisterationRequest(
        self,
        registerationRequest: APIRegisterationRequest,
        document: Document,
    ) -> Block | APIError:
        """Validate a registration request and register its block."""
        try:
            user = User(
                name=registerationRequest.userName,
                age=registerationRequest.age,
                nationalNumber=registerationRequest.nationalNumber,
                phone=registerationRequest.phone,
                email=registerationRequest.email,
                birth=registerationRequest.birth,
                HID="",
            )
            issuer = Authority(
                name=registerationRequest.issuerName,
                businessID=registerationRequest.issuerID,
                AUTHID="",
            )
            credential = Credential(
                documentID=registerationRequest.documentID,
                document=document,
                CID="",
            )
        except ValidationError:
            return APIError(error="Validation-error", message="Input data is not valid.")

        if not self.inputValidation.holderValidation(user=user):
            return APIError(error="Validation-Error", message="User input is invalid")
        if not self.inputValidation.credentialValidation(credential=credential):
            return APIError(error="Validation-Error", message="Credential input is invalid")
        if not self.inputValidation.issuerValidation(issuer=issuer):
            return APIError(error="Validation-Error", message="Issuer input is invalid")

        block = Block(data=CHID(user=user, credential=credential, issuer=issuer, chid=""))

        try:
            result: Block | Exception | None = self.registerBlock(block)
        except (
            DuplicateBlockError,
            DuplicateCredentialIDError,
            InvalidChainError,
            ConflictingCredentialError,
            ValidationError,
        ) as error:
            result = error

        if result is None:
            return APIError(error="Block-building-fail", message="Cannor build the block.")
        if isinstance(result, DuplicateBlockError):
            return APIError(error="Block-duplication-error", message="Block already exists.")
        if isinstance(result, DuplicateCredentialIDError):
            return APIError(error="Duplicate-Credential-ID", message=str(result))
        if isinstance(result, InvalidChainError):
            return APIError(error="Invalid-Chain", message="Chain integrity failed; chain sync requested.")
        if isinstance(result, ConflictingCredentialError):
            return APIError(error="Conflict-Credential", message="Check if the input is valid.")
        if isinstance(result, ValidationError):
            return APIError(error="Validation-error", message="Input is invalid")
        if isinstance(result, Exception):
            return APIError(error="Internal-Error", message="Internal node error. Try again.")

        return result

    def sendNodeStatus(self) -> NodeStatus:
        """Build the node status response for the HTTP API."""
        ledger = self.verchain.ledger.blocks
        return NodeStatus(
            name=self.verchain.title,
            host=self.verchain.host,
            port=self.verchain.port,
            chainValidity=ChainValidation(ledger).validate(),
            blocksCount=len(ledger),
        )

    def sendChain(self) -> ChainModel:
        """Build the chain response for the HTTP API."""
        return ChainModel(sender=self.verchain.me, chain=self.verchain.blockManager.ledger.blocks)
