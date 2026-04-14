from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ControllerState, RecoveryDecision


class RecoveryController(ABC):
    @abstractmethod
    def decide(self, state: ControllerState) -> RecoveryDecision:
        raise NotImplementedError
