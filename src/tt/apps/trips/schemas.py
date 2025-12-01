from dataclasses import dataclass
from typing import List

from .models import Trip


@dataclass
class TripCategorizedDisplayData:

    current_trips  : List[Trip]
    shared_trips   : List[Trip]
    past_trips     : List[Trip]

    @property
    def total_trips(self) -> int:
        return len(self.current_trips) + len(self.shared_trips) + len(self.past_trips)
