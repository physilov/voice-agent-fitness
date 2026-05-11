from dataclasses import dataclass
from enum import StrEnum


class Channel(StrEnum):
    WHATSAPP = "whatsapp"
    VOICE_CALL = "voice_call"
    WEB = "web"
    APP = "app"


@dataclass(frozen=True)
class ChannelCapabilities:
    can_render_ui: bool
    can_stream: bool
    is_voice: bool


CAPABILITIES: dict[Channel, ChannelCapabilities] = {
    Channel.WHATSAPP: ChannelCapabilities(can_render_ui=False, can_stream=False, is_voice=False),
    Channel.VOICE_CALL: ChannelCapabilities(can_render_ui=False, can_stream=True, is_voice=True),
    Channel.WEB: ChannelCapabilities(can_render_ui=True, can_stream=True, is_voice=False),
    Channel.APP: ChannelCapabilities(can_render_ui=True, can_stream=True, is_voice=False),
}
