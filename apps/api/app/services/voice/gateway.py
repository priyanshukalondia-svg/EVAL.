# apps/api/app/services/voice/gateway.py
from typing import Protocol, AsyncIterator

class VoiceGateway(Protocol):
    async def start_session(self, session_id: str) -> None: ...
    async def send_audio_chunk(self, session_id: str, chunk: bytes) -> None: ...
    async def on_transcript(self, session_id: str) -> AsyncIterator[str]: ...
    async def speak(self, session_id: str, text: str) -> None: ...
    async def end_session(self, session_id: str) -> None: ...

class TextOnlyVoiceGateway:
    """Phase 1 stub: no-op for audio, transcript == text input directly."""
    async def start_session(self, session_id: str) -> None:
        pass
        
    async def send_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        raise NotImplementedError("Voice not enabled in Phase 1 — use text endpoint")
        
    async def on_transcript(self, session_id: str):
        yield "" # placeholder generator
        
    async def speak(self, session_id: str, text: str) -> None:
        pass  # text UI renders `text` directly, no TTS call
        
    async def end_session(self, session_id: str) -> None:
        pass
