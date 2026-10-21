"""Results of exhaustive reads, including why pagination stopped."""

from dataclasses import dataclass
from typing import Literal

TerminationReason = Literal["exhausted", "cutoff", "max_pages", "no_progress", "inconsistent_total"]


@dataclass
class PaginationResult[T]:
    """Items in first-seen order and completeness relative to the requested scope.

    ``exhausted`` confirms exhaustion; ``cutoff`` satisfies a requested date
    cutoff. ``max_pages``, ``no_progress`` and ``inconsistent_total`` describe
    incomplete reads. Request failures still raise rather than returning results.
    """

    items: list[T]
    complete: bool
    termination_reason: TerminationReason
