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

from errors.documents import UploadedDocumentTooLarge, UploadedDocumentNotSupported, InvalidPDFContent


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self, document: UploadFile, constraints: CredentialConstraints | None = None) -> None:
        self.constraints = constraints or CredentialConstraints()
        self.document = document

    async def receive(self, uploadedFile: UploadFile) -> Document:
        "Builds the ``Document`` model from the ``UploadFile``"

        filename = uploadedFile.filename or ""
        fileFormat = Path(filename).suffix.lower()
        content = await self.read()

        document = Document(
            documentTitle="Credential document",
            documentFormat=fileFormat,
            documentContentSize=len(content),
        )

        try:
            DocumentValidation(document=document, content=content, constraints=self.constraints).validate()
        except (UploadedDocumentTooLarge, UploadedDocumentNotSupported, InvalidPDFContent, ValueError) as error:
            raise ValueError(str(error)) from error


        

        documentHashBuilder = DocumentHashing(document=document, content=content)
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
    def __init__(self, document: Document, content: bytes) -> None:
        self.document = document
        self.content = content

    def hash(self) -> Document:
        # payload = self.document.documentContent or b""
        file_format = (self.document.documentFormat or "").encode("utf-8")
        documentHash = hashlib.sha256(
            self.content + b":" + file_format
        ).hexdigest()

        self.document.documentHash = documentHash

        return self.document




