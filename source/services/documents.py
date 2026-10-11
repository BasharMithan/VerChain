"""
Date: 16/09/2026
Developer: Bashar Mithan
Title: Document.
Description: Contains the document (credential) related services/utils.
- Receiving: Receives the uploaded document.
- Validation: Validating the type of the credential ( .pdf, .png, ... ) & the size of the document.
- Hashing: Hashing the document and producing the CID of the document.
- Verification: Checking the document ownership When the verification input contains a document.
"""



import hashlib
from pathlib import Path
from fastapi import UploadFile

from configs.baseConfigs import CredentialConstraints
from models.Models import Document
from validation.documents import DocumentValidation

from errors.documents import UploadedDocumentTooLarge, UploadedDocumentNotSupported, InvalidPDFContent


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self, constraints: CredentialConstraints) -> None:
        self.constraints = constraints


    async def receive(self, uploadedFile: UploadFile, documentID: int) -> Document:
        "Builds the ``Document`` model from the ``UploadFile``"

        filename = uploadedFile.filename or ""
        fileFormat = Path(filename).suffix.lower()
        content = await self.read(uploadedFile)

        document = Document(
            documentTitle="Credential document",
            documentFormat=fileFormat,
            documentContentSize=len(content),
        )

        try:
            DocumentValidation(document=document, content=content, constraints=self.constraints).validate()
        except (UploadedDocumentTooLarge, UploadedDocumentNotSupported, InvalidPDFContent, ValueError) as error:
            raise ValueError(str(error)) from error


        documentHashBuilder = DocumentHashing(document=document, content=content, documentID=documentID)
        hashedDocument: Document = documentHashBuilder.hash()

        return hashedDocument

        

    async def read(self, file: UploadFile) -> bytes:
        "Reads the received document and returns it's content (bytes)."
        try:
            await file.seek(0)
            return await file.read(self.constraints.maxUploadSize + 1)
        finally:
            await file.seek(0)

    



class DocumentHashing:
    def __init__(self, document: Document, content: bytes, documentID: int) -> None:
        self.document = document
        self.content = content
        self.ID = str(documentID).encode()

    def hash(self) -> Document:
        file_format = (self.document.documentFormat or "").encode("utf-8")
        documentHash = hashlib.sha256(
            self.content + b":" + file_format + b":" + self.ID
        ).hexdigest()

        self.document.documentHash = documentHash

        return self.document


