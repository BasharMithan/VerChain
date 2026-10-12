
from __future__ import annotations

import questionary
from typing import Callable

from utils.utility_function import getProjectVersion

from models.Models import Payload, Document
from models.CLIModels import CLICommand
from utils.utility_function import listEnum, enumValue

from services.processor import VerchainProcessor


class CLI:
    """CLI entry point for starting a Verchain node."""

    def __init__(self, processor: VerchainProcessor) -> None:
        self.processor = processor

    def start(self) -> None:
        """Start the peer-to-peer network for CLI use."""
        self.processor.start()


class VerchainCLI:
    def __init__(self) -> None:
        self.welcome()
        self.commands = listEnum(CLICommand)
        self.chooseCommand()


    def welcome(self) -> None:
        welcomeMessage = f"""Welcome to Verchain {getProjectVersion()}\n"""
        questionary.print(text=welcomeMessage)


    def chooseCommand(self) -> CLICommand:
        command = questionary.select(
            "Choose a command", choices=self.commands).ask()

        print(enumValue(enum_class=CLICommand, value=command), type(command))
        return CLICommand.register


class CLICommandRouter:

    @staticmethod
    def route(
        processor: VerchainProcessor,
        command: CLICommand,
        payload: Payload,
        document: Document | None = None,
    ) -> None:
        """Receives the command choosen by the user in the CLI, and decides what to excute.

        Args:
            command (CLICommand): The command to excute.
        """
        commandsMap: dict[CLICommand, Callable] = {
            CLICommand.register: processor.processBlockRegisterationRequest
        }

        excution = commandsMap.get(command, None)

        if excution is None:
            return





        ...



if __name__ == '__main__':
    cli = VerchainCLI()
