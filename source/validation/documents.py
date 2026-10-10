"""
    Model: DocumentValidation:
    Developer: Bashar Mithan
    Date: 2026/10/2
"""

import pymupdf

from models.Models import Document
from configs.baseConfigs import CredentialConstraints

from errors.documents import UploadedDocumentNotSupported, UploadedDocumentTooLarge, InvalidPDFContent



class DocumentValidation:
    """Resposible for validating the input document by checking the document content validity and document size."""
    def __init__(self, document: Document, content: bytes, constraints: CredentialConstraints | None = None) -> None:
        self.document = document
        self.content = content
        self.constraints = constraints or CredentialConstraints()

    def validate(self) -> None:
        """Checks if the uploaded document is valid (meets the document constraints).
        """

        if self.document.documentContentSize > self.constraints.maxUploadSize:
            raise UploadedDocumentTooLarge()

        if self.document.documentFormat not in self.constraints.supportedCredentialFormats:
            raise UploadedDocumentNotSupported()

        # if self.document.documentFormat == ".pdf" and not self.document.documentContent.startswith(b"%PDF-"): # type: ignore
        #     raise ValueError("Credential file is not a valid PDF.")

        # Checking if the file format is .pdf, but dosen't contain a valid .pdf content.
        if self.document.documentFormat == ".pdf":
            try:
                with pymupdf.open(stream=self.content, filetype="pdf") as opened_document:
                    if not getattr(opened_document, "is_pdf", False):
                        raise InvalidPDFContent(filename=self.document.documentTitle)
            except (pymupdf.FileDataError, ValueError) as error:
                raise InvalidPDFContent(filename=self.document.documentTitle) from error

        # TODO: Implement a document format-based router.


