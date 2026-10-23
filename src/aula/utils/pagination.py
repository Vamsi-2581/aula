"""Track pagination progress without guessing additional provider flags."""

import json

from ..models.pagination import PaginationResult, TerminationReason


class PaginationState:
    def __init__(self):
        self.items: list[dict] = []
        self.seen_ids: set[str] = set()
        self.seen_pages: set[str] = set()
        self.total: int | None = None
        self.inconsistent = False

    def observe_total(self, data: dict) -> None:
        # totalSize is optional. Missing totals never mean zero results.
        total = data.get("totalSize")
        if total is None:
            return
        if (
            not isinstance(total, int)
            or isinstance(total, bool)
            or total < 0
            or self.total is not None
            and total != self.total
        ):
            self.inconsistent = True
        else:
            self.total = total

    def add(self, rows: list[dict]) -> bool:
        signature = json.dumps(rows, sort_keys=True, default=str)
        if signature in self.seen_pages:
            return False
        self.seen_pages.add(signature)
        before = len(self.items)
        for row in rows:
            identifier = row.get("id")
            if identifier is None:
                search_message = row.get("searchMessage")
                if isinstance(search_message, dict):
                    identifier = search_message.get("id")
            if isinstance(identifier, (str, int)) and str(identifier):
                key = str(identifier)
                if key in self.seen_ids:
                    continue
                self.seen_ids.add(key)
            # Without identity, retain distinct rows instead of merging them
            # all under the same missing-ID key.
            self.items.append(row)
        return len(self.items) > before

    def result(self, reason: TerminationReason) -> PaginationResult[dict]:
        if reason == "exhausted" and (
            self.inconsistent or (self.total is not None and len(self.items) != self.total)
        ):
            reason = "inconsistent_total"
        return PaginationResult(self.items, reason in ("exhausted", "cutoff"), reason)
