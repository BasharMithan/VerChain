import pymupdf
from pathlib import Path
from models import Credential
from configs.baseConfigs import defaultSettings



class DocumentValidation:
    def __init__(self, document: Credential) -> None:
        self.document = document

    def isValid(self) -> bool:
        ...


    def extractFormat(self) -> str:
        ...


     

