from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from typing import Annotated

from core.verchain import Verchain
from core.verchainCommunication import VerchainCommunication
from models.APIModels import APIRegisterationRequest, VerificationRequest
from models.Models import Response
from errors.APIErrors import APIError
from configs.handler import configs
from services.documents import DocumentReceiver
from configs.baseConfigs import CredentialConstraints


class VerchainRouter(APIRouter):
    def __init__(
        self,
        verchain: Verchain,
        communication: VerchainCommunication | None = None,
    ) -> None:
        super().__init__()
        self.verchain = verchain
        self.communication = communication or VerchainCommunication(verchain)
        self.settings = configs.load()

        self.add_api_route("/register", self.register, methods=["POST"], status_code=201)
        self.add_api_route("/credential-constraints", self.credentialConstraints, methods=["GET"])
        self.add_api_route("/check", self.check, methods=["POST"])
        self.add_api_route("/chain", self.chain, methods=["GET"])
        self.add_api_route("/status", self.status, methods=["GET"])

    async def register(
        self,
        userName: Annotated[str, Form(alias="user.name")],
        nationalNumber: Annotated[int, Form(alias="user.nationalNumber")],
        phone: Annotated[int, Form(alias="user.phone")],
        age: Annotated[int, Form(alias="user.age")],
        email: Annotated[str, Form(alias="user.email")],
        birth: Annotated[str, Form(alias="user.birth")],
        documentID: Annotated[int, Form(alias="credential.documentID")],
        issuerName: Annotated[str, Form(alias="issuer.name")],
        issuerID: Annotated[int, Form(alias="issuer.issuerID")],
        document: Annotated[UploadFile, File(alias="credential.document")],
    ):
        registerationRequest = APIRegisterationRequest.model_validate({
            "user.name": userName,
            "user.nationalNumber": nationalNumber,
            "user.phone": phone,
            "user.age": age,
            "user.email": email,
            "user.birth": birth,
            "credential.documentID": documentID,
            "issuer.name": issuerName,
            "issuer.issuerID": issuerID,
            "credential.document": document,
        })
        try:
            documentReceiver = DocumentReceiver(constraints=CredentialConstraints())
            receivedDocument = await documentReceiver.receive(uploadedFile=document, documentID=documentID)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error


        result = await run_in_threadpool(
            self.communication.processBlockRegisterationRequest,
            registerationRequest,
            receivedDocument,
        )

        if isinstance(result, APIError):
            raise HTTPException(status_code=409, detail=result.message)
        
        return result

    def credentialConstraints(self):
        return {
            "maxUploadSize": self.settings.credentials.maxUploadSize,
            "supportedFormats": sorted(
                item.lower() for item in self.settings.credentials.supportedCredentialFormats
            ),
        }

    async def check(
        self,
        username: Annotated[str, Form(alias="username")],
        userID: Annotated[int, Form(alias="userID")],
        document: Annotated[UploadFile, File(alias="document")],
        documentID: Annotated[int, Form(alias="documentID")],
        issuer: Annotated[str, Form(alias="issuer")],
        issuerID: Annotated[int, Form(alias="issuerID")],
    ):
              
        try:
            documentReceiver = DocumentReceiver(constraints=CredentialConstraints())
            receivedDocument = await documentReceiver.receive(uploadedFile=document, documentID=documentID)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        payload = VerificationRequest(
            user=username,
            userID=userID,
            document=receivedDocument,
            documentID=documentID,
            issuer=issuer,
            issuerID=issuerID
        )
 

        result: Response | APIError = self.communication.processVerificationRequest(payload)

        if isinstance(result, APIError):
            raise HTTPException(
                status_code=404,
                detail={"error": result.error, "message": result.message},
            )

        return result
        

    def chain(self):
        return self.communication.sendChain(node=self.verchain.me, blockManager=self.verchain.blockManager)

    def status(self):
        return self.communication.sendNodeStatus()