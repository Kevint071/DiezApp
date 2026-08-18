from dataclasses import dataclass


@dataclass
class NavigationState:
    selected_index: int = 0

    def select(self, index: int) -> None:
        self.selected_index = index
