"""
    Date: 2026, 09, 24
    Developer: Bashar Mithan
    Title: DocumentReceiver
"""

import hashlib
from pathlib import Path

from fastapi import UploadFile

from configs.baseConfigs import CredentialConstraints


class DocumentReceiver:
    """Validate an uploaded credential and return its content digest."""

    def __init__(self, credentialID: int, uploadedFile: UploadFile, constraints: CredentialConstraints) -> None:
        self.credentialID = credentialID
        self.uploadedFile = uploadedFile
        self.constraints = constraints

    async def receive(self) -> str:
        filename = self.uploadedFile.filename or ""
        fileFormat = Path(filename).suffix.lower()
        supportedFormats = {item.lower() for item in self.constraints.supportedCredentialFormats}

        if fileFormat not in supportedFormats:
            allowed = ", ".join(sorted(supportedFormats))
            raise ValueError(f"Unsupported credential format. Allowed formats: {allowed}")

        content = await self.uploadedFile.read(self.constraints.maxUploadSize + 1)
        if len(content) > self.constraints.maxUploadSize:
            raise ValueError(
                f"Credential exceeds the maximum upload size of {self.constraints.maxUploadSize} bytes."
            )
        if not content:
            raise ValueError("Credential file must not be empty.")

        return hashlib.sha256(bytes(self.credentialID) + b":" + content + b":" + fileFormat.encode("utf-8")).hexdigest()
