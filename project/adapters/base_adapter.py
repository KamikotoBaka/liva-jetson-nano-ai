from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AdapterExecutionResult:
	command: str
	payload: dict


class BaseAdapter(ABC):
	@abstractmethod
	def execute(self, intent: str, entity: str | None = None) -> AdapterExecutionResult:
		raise NotImplementedError
