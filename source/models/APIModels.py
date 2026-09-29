from pydantic import BaseModel
from enum import Enum
from models.Models import NodeMetadata
from typing import Annotated
from fastapi import Form, UploadFile, File



class UserAPIModel(BaseModel):
    name: str
    nationalNumber: int
    phone: int
    age: int
    email: str
    birth: str



class CredentialAPIModel(BaseModel):
    document: str
    credentialID: int



class IdentityAPIModel(BaseModel):
    image: str
    identityID: int
    # metadata: DocumentMetadata


class IssuerAPIModel(BaseModel):
    name: str
    issuerID: int


class APIRegisterationRequest(BaseModel):
    # user: UserAPIModel
    # credential: CredentialAPIModel
    # issuer: IssuerAPIModel 

    userName: Annotated[str, Form(alias="user.name")]
    nationalNumber: Annotated[int, Form(alias="user.nationalNumber")]
    phone: Annotated[int, Form(alias="user.phone")]
    age: Annotated[int, Form(alias="user.age")]
    email: Annotated[str, Form(alias="user.email")]
    birth: Annotated[str, Form(alias="user.birth")]
    credentialID: Annotated[int, Form(alias="credential.credentialID")]
    issuerName: Annotated[str, Form(alias="issuer.name")]
    issuerID: Annotated[int, Form(alias="issuer.issuerID")]
    document: Annotated[UploadFile, File(alias="credential.document")]

class APIRegisterationResponse(BaseModel):
    response: str


class VerificationRequest(BaseModel):
    user: str # User.name
    UserID: int # User.nationalNumber
    credentialID: int # Identity.IdentityID
    issuer: str # Authority.name
    issuerID: int # Authority.businessID

class VerificationResponse(BaseModel):
    ...

class NodeStatus(BaseModel):
    name: str
    host: str
    port: int
    chainValidity: bool
    blocksCount: int


class ChainModel(BaseModel):
    sender: NodeMetadata
    chain: list


class IDTyping(Enum):
    user = "USER"
    identity = "IDENTITY"
    authority = "AUTHORITY"