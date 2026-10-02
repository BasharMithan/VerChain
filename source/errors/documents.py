
from configs.baseConfigs import CredentialConstraints


class UploadedDocumentTooLarge(Exception):
    def __initt__(self) -> None:
        return super().__init__(
            f"The uploaded document is too large, max size is {CredentialConstraints.maxUploadSize}"
            )


class UploadedDocumentNotSupported(Exception):
    def __init__(self) -> None:
        return super().__init__(
            f"The uploaded dcoument format is not supported, supported formats: ({CredentialConstraints.supportedCredentialFormats})"
        )