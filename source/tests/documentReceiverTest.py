import asyncio
import hashlib
from io import BytesIO

import pymupdf
import pytest
from fastapi import UploadFile

from configs.baseConfigs import CredentialConstraints
from services.documents import DocumentReceiver


def _pdf(encryption: int = pymupdf.PDF_ENCRYPT_NONE) -> bytes:
    with pymupdf.open() as document:
        document.new_page()
        if encryption == pymupdf.PDF_ENCRYPT_NONE:
            return document.tobytes()
        return document.tobytes(
            encryption=encryption,
            owner_pw="owner-password",
            user_pw="user-password",
        )


def _receive(content: bytes, documentID: int = 1):
    receiver = DocumentReceiver(constraints=CredentialConstraints())
    uploaded_file = UploadFile(file=BytesIO(content), filename="credential.pdf")
    return asyncio.run(receiver.receive(uploadedFile=uploaded_file, documentID=documentID))


def test_receiver_hash_includes_document_id():
    content = _pdf()

    first = _receive(content, documentID=1)
    second = _receive(content, documentID=2)

    assert first.documentHash == hashlib.sha256(
        content + b":.pdf:1"
    ).hexdigest()
    assert first.documentHash != second.documentHash


def test_receiver_rejects_pdf_with_junk_before_header():
    with pytest.raises(ValueError, match="invalid content"):
        _receive(b"junk before header" + _pdf())


def test_receiver_rejects_encrypted_pdf():
    with pytest.raises(ValueError, match="invalid content"):
        _receive(_pdf(encryption=pymupdf.PDF_ENCRYPT_AES_256))


def test_receiver_reads_no_more_than_limit_plus_one_byte():
    class TrackingUploadFile(UploadFile):
        def __init__(self, content: bytes):
            super().__init__(file=BytesIO(content), filename="credential.pdf")
            self.requested_size = None

        async def read(self, size: int = -1) -> bytes:
            self.requested_size = size
            return await super().read(size)

    constraints = CredentialConstraints(maxUploadSize=10)
    uploaded_file = TrackingUploadFile(b"x" * 100)
    receiver = DocumentReceiver(constraints=constraints)

    with pytest.raises(ValueError, match="too large"):
        asyncio.run(receiver.receive(uploadedFile=uploaded_file, documentID=3))

    assert uploaded_file.requested_size == 11
