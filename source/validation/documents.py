"""
    Model: DocumentValidation:
    Developer: Bashar Mithan
    Date: 2026/10/2
"""

from models.Models import Document
from configs.baseConfigs import CredentialConstraints

from errors.documents import UploadedDocumentNotSupported, UploadedDocumentTooLarge



class DocumentValidation:
    def __init__(self, document: Document, constraints: CredentialConstraints | None = None) -> None:
        self.document = document
        self.constraints = constraints or CredentialConstraints()

    def validate(self) -> None:
        """Checks if the uploaded document is valid (meets the document constraints).
        """

        if self.document.documentContentSize > self.constraints.maxUploadSize:
            raise UploadedDocumentTooLarge()

        if self.document.documentFormat not in self.constraints.supportedCredentialFormats:
            raise UploadedDocumentNotSupported()

        if self.document.documentFormat == ".pdf" and not self.document.documentContent.startswith(b"%PDF-"): # type: ignore
            raise ValueError("Credential file is not a valid PDF.")

        # TODO: Implement a document format-based router.


