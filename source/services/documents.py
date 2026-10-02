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
from pymupdf import pymupdf

from configs.baseConfigs import CredentialConstraints
from models.Models import Document
from validation.documents import DocumentValidation

from errors.documents import UploadedDocumentTooLarge, UploadedDocumentNotSupported


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self, document: UploadFile, constraints: CredentialConstraints | None = None) -> None:
        self.constraints = constraints or CredentialConstraints()
        self.document = document

    async def receive(self, uploadedFile: UploadFile, documentID: int) -> Document:
        "Builds the ``Document`` model from the ``UploadFile``"

        filename = uploadedFile.filename or ""
        fileFormat = Path(filename).suffix.lower()
        content = await self.read()

        document = Document(
            documentTitle="Credential document",
            documentFormat=fileFormat,
            documentContent=content,
            documentContentSize=len(content),
        )

        try:
            documentValidation = DocumentValidation(document=document, constraints=self.constraints)
            documentValidation.validate()
        except (UploadedDocumentTooLarge, UploadedDocumentNotSupported) as error:
            raise ValueError(str(error)) from error
        except ValueError as error:
            raise ValueError(str(error)) from error

        documentHashBuilder = DocumentHashing(document=document, documentID=documentID)
        hashedDocument: Document = documentHashBuilder.hash()

        return hashedDocument



        

    async def read(self) -> bytes:
        "Reads the received document and returns it's content (bytes)."
        if self.document is None:
            return b""

        file_handle = getattr(self.document, "file", None)
        if file_handle is None:
            return b""

        try:
            file_handle.seek(0)
            return file_handle.read()
        finally:
            file_handle.seek(0)

    



class DocumentHashing:
    def __init__(self, document: Document, documentID: int) -> None:
        self.documentID = documentID
        self.document = document

    def hash(self) -> Document:
        payload = self.document.documentContent or b""
        file_format = (self.document.documentFormat or "").encode("utf-8")
        documentHash = hashlib.sha256(
            payload + b":" + file_format + b":" + str(self.documentID).encode("utf-8")
        ).hexdigest()

        self.document.documentHash = documentHash

        return self.document




