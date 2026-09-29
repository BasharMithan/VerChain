import yaml

from configs.baseConfigs import Settings, defaultSettings
from configs.handler import ConfigurationHandler


def test_load_updates_the_shared_settings_instance(tmp_path, monkeypatch):
    for fieldName in Settings.model_fields:
        monkeypatch.setattr(defaultSettings, fieldName, getattr(defaultSettings, fieldName))

    configurationPath = tmp_path / "settings.yml"
    monkeypatch.setattr(defaultSettings, "configurationFilePath", configurationPath)
    configurationPath.write_text(
        yaml.safe_dump({
            "settings": {
                "configurationFilePath": str(configurationPath),
                "difficulity": 2,
                "performance": "SAFE",
                "ledger": {},
                "connection": {"bootstrapPeers": [["127.0.0.1", 8000]]},
                "credentials": {
                    "maxUploadSize": 2048,
                    "supportedCredentialFormats": [".pdf"],
                },
            },
        }),
        encoding="utf-8",
    )

    loadedSettings = ConfigurationHandler.load()

    assert loadedSettings is defaultSettings
    assert defaultSettings.difficulity == 2
    assert defaultSettings.credentials.maxUploadSize == 2048