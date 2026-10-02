"""
    Date: 2026, 09, 24
    Developer: Bashar Mithan
    Title: DocumentReceiver
"""

import hashlib
from pathlib import Path
from fastapi import UploadFile
from pymupdf import pymupdf

from configs.baseConfigs import CredentialConstraints
from models.Models import Document


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self, constraints: CredentialConstraints) -> None:
        self.constraints = constraints



    async def receive(self, uploadedFile: UploadFile, documentID: int) -> Document:
        self.documentID = documentID
        filename = uploadedFile.filename or ""
        fileFormat = Path(filename).suffix.lower()

        if not self.isInputDocumentValid(uploadedFile):
            if (uploadedFile.size or 0) > self.constraints.maxUploadSize:
                raise ValueError(
                    f"Credential exceeds the maximum upload size of {self.constraints.maxUploadSize} bytes."
                )
            supportedFormats = {item.lower() for item in self.constraints.supportedCredentialFormats}
            allowed = ", ".join(sorted(supportedFormats))
            raise ValueError(f"Unsupported credential format. Allowed formats: {allowed}")

        content = await uploadedFile.read(self.constraints.maxUploadSize + 1)
        if len(content) > self.constraints.maxUploadSize:
            raise ValueError(
                f"Credential exceeds the maximum upload size of {self.constraints.maxUploadSize} bytes."
            )
        if not content:
            raise ValueError("Credential file must not be empty.")

        if fileFormat == ".pdf":
            try:
                with pymupdf.open(stream=content, filetype="pdf"):
                    ...


            except (pymupdf.FileDataError, ValueError) as error:
                raise ValueError("Credential file is not a valid PDF.") from error

        return Document(
            documentTitle="Credential document", documentType=uploadedFile.content_type,
            documentContentSize=uploadedFile.size or 0,
            documentHash=hashlib.sha256(
                content + b":" + fileFormat.encode("utf-8") + b":" + str(self.documentID).encode("utf-8")
            ).hexdigest(),
            )



    def isInputDocumentValid(self, uploadedDocument: UploadFile) -> bool:
        """Checks if the uploaded document is valid (meets the document constraints).

        Args:
            uploadedDocument (UploadFile): The uploaded document from the API

        Returns:
            bool: True if the document is valid.
        """
        if uploadedDocument.size is None:
            uploadedDocument.size = 0

        if uploadedDocument.size > self.constraints.maxUploadSize:
            return False

        supportedFormats = {item.lower() for item in self.constraints.supportedCredentialFormats}
        if Path(uploadedDocument.filename or "").suffix.lower() not in supportedFormats:
            return False

        return True






