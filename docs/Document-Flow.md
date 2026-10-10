# Document Flow

How a credential `Document` moves through Verchain, from the API upload to the ledger and across the P2P network.

## The `Document` data model

Defined in `source/models/Models.py`

```Python
class Document(BaseModel):
    model_config = ConfigDict(ser_json_bytes="base64", val_json_bytes="base64")

    documentTitle: str | None = None
    documentFormat: str | None = None
    documentContentSize: int = 0
    documentHash: str = ""

    @model_validator(mode="before")
    @classmethod
    def validateLegacyDocumentContent(cls, value: Any) -> Any:
        if isinstance(value, dict):
            content = value.get("documentContent")
            if isinstance(content, str):
                try:
                    base64.b64decode(content, altchars=b"-_", validate=True)
                except ValueError as error:
                    raise ValueError("Stored document content is not valid base64.") from error
        return value
```

- `Document` uses `ser_json_bytes="base64"` / `val_json_bytes="base64"`, so raw bytes become base64 whenever a block is dumped in JOSN (ledger file, gossip, chain sync, `GET /chain`).
- A `before` validator rejects stored content that is not valid base64 (represented as ledger corruption on load).
- The `documentHash` is computed by `DocumentHashing` class (`services/documents.py`). The `CID` is computed in `Credential.__post_init__`.

## Components on the document path

1. API router (`POST /register`) - The entry point of a document, the document is represented as `FastAPI.UploadFile`.
2. `DocumentReceiveer` - It takes the `UploadFile` model that contains info about the document, converts it into `Document` model (`source/models/Models.py`).
3. `DocumentValidation` - Takes the generated `Document`, checks if it meets the `CredentialConstraints` configs.
4. `DocumentHashing` - If the document meets the document constraints configs, the `DocumentHashing` hashes the document so it is ready to be assigned to a `Block`.
