
from models import User, Credential, Authority
from services.ledger import Ledger

from validation.document import DocumentValidation


class InputValidation:
    """Checks the validity of the user, credential, and issuer input values before
    building the Block data model."""

    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger


    def holderValidation(self, user: User) -> bool:
        """Chekcs if the national number passed to the user is already associated with 
        another stored user.

        Args:
            user (User): User

        Returns:
            bool: True if the national number is associated with a user.
        """

        if self.ledger.findUser(user.nationalNumber, user.name) is not None:
            return False
        
        else: return True
            

    
    def credentialValidation(self, credential: Credential) -> bool:
        if self.ledger.findCredential(credential.documentID) is not None:
            return False

        # DocumentValidation()
        
        return True


    
    def issuerValidation(self, issuer: Authority) -> bool:

        if self.ledger.findIssuer(issuer.businessID, issuer.name) is not None:
            return False
        else: return True
        
