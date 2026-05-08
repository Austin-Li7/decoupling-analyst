from abc import ABC, abstractmethod

from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.research import ResearchBrief


class ResearchAdapter(ABC):
    @abstractmethod
    def research(self, raw_input: RawInput) -> ResearchBrief:
        raise NotImplementedError
