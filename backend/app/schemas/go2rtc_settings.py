from pydantic import BaseModel, Field


class Go2RtcStatusOut(BaseModel):
    enabled: bool
    connected: bool
    embedded_runner: bool
    has_embedded_binary: bool
    api_url: str
    rtsp_url: str
    webrtc_candidates: list[str] = Field(default_factory=list)


class Go2RtcSettingsUpdate(BaseModel):
    enabled: bool | None = None
    webrtc_candidates: list[str] | None = None
