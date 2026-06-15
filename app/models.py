from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.constants import PayloadFormat, ProtocolType


@dataclass
class InstrumentConfig:
    alias: str
    type: str = ""
    protocol: str = ProtocolType.SOCKET_SCPI_LINE
    payloadFormat: str = PayloadFormat.TEXT
    proxyHost: str = "127.0.0.1"
    proxyPort: int = 15026
    realHost: str = ""
    realPort: int = 5025
    visaResource: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstrumentConfig":
        return cls(
            alias=data.get("alias", ""),
            type=data.get("type", ""),
            protocol=data.get("protocol", ProtocolType.SOCKET_SCPI_LINE),
            payloadFormat=data.get("payloadFormat", PayloadFormat.TEXT),
            proxyHost=data.get("proxyHost", "127.0.0.1"),
            proxyPort=int(data.get("proxyPort", 0) or 0),
            realHost=data.get("realHost", ""),
            realPort=int(data.get("realPort", 0) or 0),
            visaResource=data.get("visaResource", ""),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "type": self.type,
            "protocol": self.protocol,
            "payloadFormat": self.payloadFormat,
            "proxyHost": self.proxyHost,
            "proxyPort": self.proxyPort,
            "realHost": self.realHost,
            "realPort": self.realPort,
            "visaResource": self.visaResource,
            "enabled": self.enabled,
        }


@dataclass
class AppConfig:
    mode: str = "OFF"
    databasePath: str = "data/recorder.db"
    controlHost: str = "127.0.0.1"
    controlPort: int = 16000
    socketReadTimeoutMs: int = 3000
    queryResponseTimeoutMs: int = 3000
    nonQueryResponseTimeoutMs: int = 100
    appendNewLineWhenReplay: bool = True
    currentProfile: str = "default"
    currentTestItemCode: str = "DEFAULT_TEST"
    currentVariant: str = "normal"
    currentProduct: str = "MM"
    currentProcessStation: str = "FT1-MP1"
    currentProductCode: str = "03020001"
    currentTuName: str = "UNSET"
    instruments: list[InstrumentConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(
            mode=data.get("mode", "OFF"),
            databasePath=data.get("databasePath", "data/recorder.db"),
            controlHost=data.get("controlHost", "127.0.0.1"),
            controlPort=int(data.get("controlPort", 16000)),
            socketReadTimeoutMs=int(data.get("socketReadTimeoutMs", 3000)),
            queryResponseTimeoutMs=int(data.get("queryResponseTimeoutMs", 3000)),
            nonQueryResponseTimeoutMs=int(data.get("nonQueryResponseTimeoutMs", 100)),
            appendNewLineWhenReplay=bool(data.get("appendNewLineWhenReplay", True)),
            currentProfile=data.get("currentProfile", "default"),
            currentTestItemCode=data.get("currentTestItemCode", "DEFAULT_TEST"),
            currentVariant=data.get("currentVariant", "normal"),
            currentProduct=data.get("currentProduct", data.get("productName", "MM")),
            currentProcessStation=data.get("currentProcessStation", data.get("processStation", "FT1-MP1")),
            currentProductCode=data.get("currentProductCode", data.get("productCode", "03020001")),
            currentTuName=data.get("currentTuName", data.get("tuName", "UNSET")),
            instruments=[InstrumentConfig.from_dict(item) for item in data.get("instruments", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "databasePath": self.databasePath,
            "controlHost": self.controlHost,
            "controlPort": self.controlPort,
            "socketReadTimeoutMs": self.socketReadTimeoutMs,
            "queryResponseTimeoutMs": self.queryResponseTimeoutMs,
            "nonQueryResponseTimeoutMs": self.nonQueryResponseTimeoutMs,
            "appendNewLineWhenReplay": self.appendNewLineWhenReplay,
            "currentProfile": self.currentProfile,
            "currentTestItemCode": self.currentTestItemCode,
            "currentVariant": self.currentVariant,
            "currentProduct": self.currentProduct,
            "currentProcessStation": self.currentProcessStation,
            "currentProductCode": self.currentProductCode,
            "currentTuName": self.currentTuName,
            "instruments": [item.to_dict() for item in self.instruments],
        }
