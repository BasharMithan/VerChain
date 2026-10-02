"""
Date: 16/09/2026
Developer: Bashar Mithan
Title: Document.
Description: Contains the document (credential) related services/utils.
1. Validation: Validating the type of the credential ( .pdf, .png, ... ).
2. Hashing: Hashing the document and producing the CID of the document.
3. Chaining: Linking the document to the holder (User) & issuer (Authority) to add to the chain.
4. Verification: Checking the document ownership When the verification input contains a document.
"""



import hashlib
from pathlib import Path
from fastapi import UploadFile
from pymupdf import pymupdf

from configs.baseConfigs import CredentialConstraints
from models.Models import Document

from errors.documents import UploadedDocumentTooLarge, UploadedDocumentNotSupported


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self,document: UploadFile, constraints: CredentialConstraints = CredentialConstraints()) -> None:
        self.constraints = constraints
        self.document = document
        


    async def receive(self, uploadedFile: UploadFile, documentID: int) -> Document:
        "Build the ``Document`` model from the ``UploadFile``"

        filename = uploadedFile.filename or ""
        fileFormat = Path(filename).suffix.lower()

                
        document = Document(
            documentTitle=uploadedFile.filename,
            documentFormat=fileFormat,
            documentContent= await self.read(),
            documentContentSize=uploadedFile.size or 0
            )

        try:
            documentValidation = DocumentValidation(document=document)
            documentValidation.validate()
        except (UploadedDocumentTooLarge, UploadedDocumentNotSupported) as error:
            raise ValueError from error
            
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
        payload = str(self.document.documentContent).encode("utf-8")
        documentHash = hashlib.sha256(payload + b":" + str(self.documentID).encode("utf-8")).hexdigest()

        self.document.documentHash = documentHash

        return self.document




class DocumentValidation:
    def __init__(self, document: Document) -> None:
        self.document = document


    def validate(self) -> None:
        """Checks if the uploaded document is valid (meets the document constraints).

        Args:
            uploadedDocument (UploadFile): The uploaded document from the API

        """

        if self.document.documentContentSize > CredentialConstraints.maxUploadSize:
            raise UploadedDocumentTooLarge
            

        if self.document.documentFormat not in CredentialConstraints.supportedCredentialFormats:
            raise UploadedDocumentNotSupported
            

        
        
