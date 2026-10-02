

class ConflictingCredentialError(Exception):
    """Raised when a nationalNumber is already associated with a different
    Credential (name) than the one attempting to register under it."""
    def __init__(self, nationalNumber: int, existingName: str, incomingName: str):
        super().__init__(
            f"National number {nationalNumber} is already registered to "
            f"'{existingName}'; cannot also register it to '{incomingName}'."
        )