from abc import ABC, abstractmethod


class BaseTTSClient(ABC):
    """Metinden sese (TTS) servisleri için temel soyut arayüz."""

    @abstractmethod
    def is_available(self) -> bool:
        """Servisin erişilebilir olup olmadığını döner."""
        pass

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Metni ses baytlarına (WAV / MP3) dönüştürür."""
        pass
