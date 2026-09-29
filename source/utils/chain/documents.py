"""
    Date: 2026, 09, 24
    Developer: Bashar Mithan
    Title: DocumentReceiver
"""

import hashlib
from pathlib import Path
import fitz
from fastapi import UploadFile

from configs.baseConfigs import CredentialConstraints


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self, constraints: CredentialConstraints) -> None:
        self.constraints = constraints

    async def receive(self, uploadedFile: UploadFile, credentialID: int) -> str:
        self.credentialID = credentialID
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
                with fitz.open(stream=content, filetype="pdf"):
                    pass
            except (fitz.FileDataError, ValueError) as error:
                raise ValueError("Credential file is not a valid PDF.") from error

        # Document hash = "content:filetype:credentialID"
        return hashlib.sha256(content + b":" + fileFormat.encode("utf-8") + b":" + str(self.credentialID).encode("utf-8")).hexdigest()



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






