import pymupdf
from pathlib import Path
from models import Identity
from configs.baseConfigs import defaultSettings



class DocumentValidation:
    def __init__(self, document: Identity) -> None:
        self.document = document

    def isValid(self) -> bool:
        ...


    def extractFormat(self) -> str:
        ...


     

