from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from typing import Annotated

from services.peer import Peer
from models.APIModels import APIRegisterationRequest, VerificationRequest
from models.Models import Response
from API.APIServices import APICommunication
from errors.APIErrors import APIError
from configs.handler import configs
from utils.chain.documents import DocumentReceiver


def buildRouter(peer: Peer) -> APIRouter:
    router = APIRouter()
    communication = APICommunication(peer)
    settings = configs.load()

    @router.post("/register", status_code=201)
    async def register(
        userName: Annotated[str, Form(alias="user.name")],
        nationalNumber: Annotated[int, Form(alias="user.nationalNumber")],
        phone: Annotated[int, Form(alias="user.phone")],
        age: Annotated[int, Form(alias="user.age")],
        email: Annotated[str, Form(alias="user.email")],
        birth: Annotated[str, Form(alias="user.birth")],
        credentialID: Annotated[int, Form(alias="credential.credentialID")],
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
            "credential.credentialID": credentialID,
            "issuer.name": issuerName,
            "issuer.issuerID": issuerID,
            "credential.document": document,
        })
        try:
            documentReceiver = DocumentReceiver(settings.credentials)
            documentHash = await documentReceiver.receive(uploadedFile=registerationRequest.document, credentialID=registerationRequest.credentialID)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error


        result = await run_in_threadpool(
            communication.processBlockRegisterationRequest,
            registerationRequest,
            documentHash,
        )

        if isinstance(result, APIError):
            raise HTTPException(status_code=409, detail=result.message)
        
        return result

    @router.get("/credential-constraints")
    def credentialConstraints():
        return {
            "maxUploadSize": settings.credentials.maxUploadSize,
            "supportedFormats": sorted(
                item.lower() for item in settings.credentials.supportedCredentialFormats
            ),
        }

    @router.post("/check")
    def check(payload: VerificationRequest):

        result: Response | APIError = communication.processVerificationRequest(payload)

        if isinstance(result, APIError):
            return result

        return result
        

    @router.get("/chain")
    def chain():
        return communication.sendChain(node=peer.me, blockManager=peer.blockManager)

    @router.get("/status")
    def status():
        return communication.sendNodeStatus()



    return router