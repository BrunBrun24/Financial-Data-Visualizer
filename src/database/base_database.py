from abc import ABC, abstractmethod


class BaseDatabase(ABC):
    @abstractmethod
    def _create_database():
        pass
