# Document Flow

How a credential document moves through Verchain, from API upload to the ledger and across the P2P network.

## The `Document` record

The `Document` model in `source/models/Models.py` stores the document title, file format, content size, and hash. The uploaded PDF bytes are used for validation and hashing, but are not stored in the model or ledger. As a result, ledger and P2P JSON contain document metadata and the digest, not the uploaded content.

The `documentHash` is SHA-256 over the uploaded bytes, the format suffix, and the credential identifier:

```python
documentHash = sha256(
    content
    + b":"
    + documentFormat.encode("utf-8")
    + b":"
    + str(documentID).encode("utf-8")
)
```

The credential ID (`CID`) is then computed from the document hash and `documentID`.

## Components on the document path

1. `POST /register` and `POST /check` receive the PDF as a multipart `UploadFile`.
2. `DocumentReceiver` reads at most the configured upload limit plus one byte, validates the file, and creates the `Document` record.
3. `DocumentValidation` checks the size and supported format, requires a PDF header at the start of the file, and rejects encrypted PDFs.
4. `DocumentHashing` hashes the file bytes and credential ID before the credential is added to a block.
