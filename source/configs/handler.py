import yaml
from pathlib import Path
from typing import Any

from configs.baseConfigs import Settings, defaultSettings


class ConfigurationHandler:

    def __init__(self) -> None:
        self.ensureConfigFileExists()


    @staticmethod
    def assign(attribute: Any, value: Any):
        """The setter function for the config class.

        Args:
            attribute (Any): The attibute to assign or update.
            value (Any): The new value to assign to the passed attribute.
        """
        ...


    @staticmethod
    def value(attribute: Any) -> Any:
        """The getter function for the config class.

        Args:
            attribute (Any): The attribute you want get it's value.

        Returns:
            Any: The value of the passed attribute.
        """

        return Any



    @staticmethod
    def load() -> Settings:
        """Reads the configuration file, loads it's current configs,
        applies it.

        Returns:
            Settings: The actual configuration file contents.
        """


        with open(defaultSettings.configurationFilePath, "r") as configFile:
            content: Any = yaml.safe_load(configFile) or {}

         
        # The file stores the settings under the ``settings`` key, while
        # ``Settings`` validates the settings object itself.
        return Settings.model_validate(content.get("settings", content))


    def ensureConfigFileExists(self) -> None:

        if not defaultSettings.configurationFilePath.exists():
            self.initConfig(defaultSettings=defaultSettings)


    def initConfig(self, defaultSettings: Settings) -> None:
        
        with open(defaultSettings.configurationFilePath, "w") as configFile:
            yaml.safe_dump(data={"settings": defaultSettings.model_dump(mode="json")}, stream=configFile, sort_keys=False, allow_unicode=True)


configs = ConfigurationHandler()
configs.load()