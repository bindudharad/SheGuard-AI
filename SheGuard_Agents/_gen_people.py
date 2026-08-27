import base64, os

content = r'''
"""People analysis: count of detected persons as a *contextual* factor only.

The Context Agent does NOT infer danger from the number of people. A crowded
campus event is normal. This analyzer produces a neutral/explained factor.
"""

from __future__ import annotations

from typing import Optional

from agents.context.schemas import PeopleContext


class PeopleAnalyzer:
    """Analyzes people count as context, not as a danger signal."""

    def analyze(
        self,
        person_count: Optional[int] = None,
        tracked_people: Optional[int] = None,
        interaction_participants: Optional[int] = None,
    ) -> PeopleContext:
        count = person_count if person_count is not None else 0
        return PeopleContext(
            count=count,
            tracked=tracked_people,
            interaction_participants=interaction_participants,
        )

    def factor(self, context: PeopleContext) -> float:
        """People count is intentionally low-weight context.

        The presence of people alone is neither safe nor dangerous. We use a very
        mild curve: an isolated single person late at night slightly raises context
        because fewer bystanders are available to help, but this is a small effect.
        """
        if context.count == 0:
            return 0.3  # unknown / alone
        if context.count == 1:
            return 0.25
        if context.count == 2:
            return 0.15
        return 0.05  # more people -> more potential bystanders
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\analyzers\people_analyzer.py'
encoded = base64.b64encode(content.encode("utf-8"))
decoded = base64.b64decode(encoded)
with open(target, "wb") as f:
    f.write(decoded)
print("written", len(decoded), "bytes")