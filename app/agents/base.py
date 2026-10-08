from typing import Protocol, TypeVar

T = TypeVar("T")


class Agent(Protocol[T]):
    name: str

    def run(self, state: dict) -> T:
        ...
