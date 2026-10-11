class DuplicateCredentialIDError(Exception):
    def __init__(self, documentID: int) -> None:
        self.documentID = documentID
        super().__init__(f"Credential documentID {documentID} is already registered.")
