
from configs.baseConfigs import CredentialConstraints


class UploadedDocumentTooLarge(Exception):
    def __init__(self, max_size: int | None = None) -> None:
        self.max_size = max_size if max_size is not None else CredentialConstraints().maxUploadSize
        super().__init__(
            f"The uploaded document is too large, max size is {self.max_size}"
        )


class UploadedDocumentNotSupported(Exception):
    def __init__(self, supported_formats: set[str] | None = None) -> None:
        self.supported_formats = supported_formats if supported_formats is not None else CredentialConstraints().supportedCredentialFormats
        super().__init__("Unsupported credential format")