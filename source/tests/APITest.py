import pytest
import pymupdf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from API.router import buildRouter
from services.ledger import Ledger
from utils.blocks.blockManager import BlockManager
from models.Models import Block, NodeMetadata, NodeConnectionType, User
from errors import DuplicateBlockError, InvalidChainError


class FakePeer:
    """Stand-in for Peer with a real Ledger/BlockManager but no p2p networking,
    so the API layer can be tested in isolation."""

    def __init__(self, title: str, host: str, port: int, ledgerPath):
        self.title = title
        self.host = host
        self.port = port
        self.ledger = Ledger(filePath=ledgerPath)
        self.blockManager = BlockManager(self.ledger, set())
        self.me = NodeMetadata(
            name=title, nodeID="", host=host, port=port,
            connectionType=NodeConnectionType.outbound,
        )

    def registerBlock(self, block: Block):
        try:
            return self.blockManager.registerBlock(block)
        except (DuplicateBlockError, InvalidChainError):
            return None


@pytest.fixture
def apiClient(tmp_path):
    fakePeer = FakePeer("APITestNode", "127.0.0.1", 9999, tmp_path / ".ledger-api-test.json")
    app = FastAPI()
    app.include_router(buildRouter(fakePeer)) # type: ignore
    return TestClient(app), fakePeer


def _registerPayload(nationalNumber, documentID, issuerID, name="Alice", issuerName="JPUF"):
    return {
        "user": {"name": name, "nationalNumber": nationalNumber, "phone": 1, "age": 30, "email": "a@x.com", "birth": "1995-01-01"},
        "credential": {"document": "", "documentID": documentID},
        "issuer": {"name": issuerName, "issuerID": issuerID},
    }


def _postRegister(client, payload, filename="credential.pdf", content=None):
    user = payload["user"]
    credential = payload["credential"]
    issuer = payload["issuer"]
    data = {
        "user.name": user["name"],
        "user.nationalNumber": str(user["nationalNumber"]),
        "user.phone": str(user["phone"]),
        "user.age": str(user["age"]),
        "user.email": user["email"],
        "user.birth": user["birth"],
        "credential.documentID": str(credential["documentID"]),
        "issuer.name": issuer["name"],
        "issuer.issuerID": str(issuer["issuerID"]),
    }
    if content is None:
        content = _validPdf()
    return client.post("/register", data=data, files={"credential.document": (filename, content)})


def _validPdf():
    with pymupdf.open() as document:
        document.new_page()
        return document.tobytes()



def test_register_success_returns_201_and_mined_block(apiClient):
    client, _ = apiClient
    res = _postRegister(client, _registerPayload(1001, 1, 10))

    assert res.status_code == 201
    body = res.json()
    assert body["index"] == 1  # genesis is index 0
    assert body["hash"].startswith("0000")
    assert body["data"]["user"]["name"] == "Alice"


def test_register_openapi_uses_multipart_form(apiClient):
    client, _ = apiClient
    openapi = client.get("/openapi.json").json()

    request_body = openapi["paths"]["/register"]["post"]["requestBody"]
    form_schema = request_body["content"]["multipart/form-data"]["schema"]
    schema_name = form_schema["$ref"].rsplit("/", 1)[-1]
    properties = openapi["components"]["schemas"][schema_name]["properties"]

    assert "user.name" in properties
    assert "credential.documentID" in properties
    assert properties["credential.document"]["contentMediaType"] == "application/octet-stream"


def test_credential_constraints_reflect_server_settings(apiClient):
    client, _ = apiClient
    response = client.get("/credential-constraints")

    assert response.status_code == 200
    assert response.json() == {"maxUploadSize": 5 * 1024 * 1024, "supportedFormats": [".pdf"]}


def test_register_duplicate_returns_409(apiClient):
    client, _ = apiClient
    payload = _registerPayload(1002, 2, 11)

    first = _postRegister(client, payload)
    assert first.status_code == 201

    second = _postRegister(client, payload)
    assert second.status_code == 409


def test_register_missing_field_returns_422(apiClient):
    client, _ = apiClient
    res = client.post("/register", data={"user.name": "Bob"})
    assert res.status_code == 422


def test_register_rejects_unsupported_file_format(apiClient):
    client, _ = apiClient
    res = _postRegister(client, _registerPayload(1003, 3, 12), filename="credential.txt")

    assert res.status_code == 400
    assert "Unsupported credential format" in res.json()["detail"]


def test_register_stores_hash_of_content_and_extension(apiClient):
    import hashlib

    client, _ = apiClient
    content = _validPdf()
    res = _postRegister(client, _registerPayload(1004, 4, 13), content=content)

    assert res.status_code == 201
    expected = hashlib.sha256(content + b":.pdf:4").hexdigest()
    assert res.json()["data"]["credential"]["document"]["documentHash"] == expected


def test_register_rejects_non_pdf_content_with_pdf_filename(apiClient):
    client, _ = apiClient
    response = _postRegister(
        client,
        _registerPayload(1005, 5, 14),
        content=b"not a PDF",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Credential file is not a valid PDF."


def test_registered_block_does_not_include_uploaded_filename(apiClient):
    client, _ = apiClient
    response = _postRegister(
        client,
        _registerPayload(1006, 6, 15),
        filename="private-name.pdf",
        content=_validPdf(),
    )

    assert response.status_code == 201
    credential = response.json()["data"]["credential"]
    assert credential["document"]["documentTitle"] == "Credential document"
    assert "private-name.pdf" not in response.text



def test_check_approves_registered_Credential(apiClient):
    client, peer = apiClient
    _postRegister(client, _registerPayload(2002, 2, 20, name="Carol", issuerName="GovAuth"))

    res = client.post("/check", json={
        "user": "Carol", "UserID": 2002, "documentID": 2,
        "issuer": "GovAuth", "issuerID": 20,
    })


    assert res.status_code == 200
    assert res.json() == "APPROVED"


def test_check_declines_for_mismatched_combination(apiClient):
    """Legit user, legit credential, legit issuer — but never registered together."""
    client, _ = apiClient
    _postRegister(client, _registerPayload(3003, 30, 300, name="Dave", issuerName="AuthX"))
    _postRegister(client, _registerPayload(3004, 31, 301, name="Eve", issuerName="AuthY"))

    res = client.post("/check", json={
        "user": "Dave", "UserID": 3003, "documentID": 31,  # Eve's credential
        "issuer": "AuthY", "issuerID": 301,                   # Eve's issuer
    })
    assert res.status_code == 200
    assert res.json() == "DECLINED"


def test_check_returns_error_when_identifiers_unknown(apiClient):
    client, _ = apiClient
    res = client.post("/check", json={
        "user": "Nobody", "UserID": 999999, "documentID": 999999,
        "issuer": "Nobody", "issuerID": 999999,
    })
    assert res.status_code == 200
    assert res.json()["error"] == "User-not-found"



def test_chain_returns_full_ledger_including_genesis(apiClient):
    client, fakePeer = apiClient
    _postRegister(client, _registerPayload(4004, 40, 400, name="Frank", issuerName="AuthZ"))

    res = client.get("/chain")
    assert res.status_code == 200
    body = res.json()
    assert body["sender"]["name"] == fakePeer.title
    assert len(body["chain"]) == 2  # genesis + Frank's block
    assert body["chain"][0]["index"] == 0
    assert body["chain"][1]["index"] == 1


# ---------------- /status ----------------

def test_status_reports_name_host_port_and_validity(apiClient):
    client, fakePeer = apiClient
    res = client.get("/status")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == fakePeer.title
    assert body["host"] == fakePeer.host
    assert body["port"] == fakePeer.port
    assert body["chainValidity"] is True
    assert body["blocksCount"] == 1  # just genesis so far