
"""Context risk scoring: weighted combination of contextual factors."""

from __future__ import annotations

from typing import List

from agents.context.schemas import (
    ContextResult,
    ContextFactor,
    ContextWeights,
    TimePeriod,
    LocationContext,
    TimeContext,
    PeopleContext,
    HistoryContext,
    IsolationContext,
    SecurityContext,
    EnvironmentContext,
)
from agents.context.analyzers.temporal_analyzer import TemporalAnalyzer
from agents.context.analyzers.location_analyzer import LocationAnalyzer
from agents.context.analyzers.zone_analyzer import ZoneAnalyzer
from agents.context.analyzers.history_analyzer import HistoryAnalyzer
from agents.context.analyzers.proximity_analyzer import ProximityAnalyzer
from agents.context.analyzers.people_analyzer import PeopleAnalyzer


class ContextRiskAnalyzer:
    """Computes the final context score, confidence, data quality, and explanations."""

    def __init__(self, weights: ContextWeights | None = None):
        self.weights = weights or ContextWeights()
        self.temporal = TemporalAnalyzer()
        self.location = LocationAnalyzer()
        self.zone = ZoneAnalyzer()
        self.history = HistoryAnalyzer()
        self.proximity = ProximityAnalyzer()
        self.people = PeopleAnalyzer()

    def compute(
        self,
        time_ctx: TimeContext,
        location_ctx: LocationContext,
        people_ctx: PeopleContext,
        history_ctx: HistoryContext,
        isolation_ctx: IsolationContext,
        security_ctx: SecurityContext,
        env_ctx: EnvironmentContext,
    ) -> ContextResult:
        factors: List[ContextFactor] = []
        reasons: List[str] = []

        # Time factor
        tf = self.temporal.factor(time_ctx.period)
        factors.append(ContextFactor(name="time", weight=self.weights.time, value=tf, contribution=tf * self.weights.time))
        if time_ctx.period in (TimePeriod.NIGHT, TimePeriod.LATE_NIGHT):
            reasons.append(f"{time_ctx.period.value} period")

        # Location factor
        lf = self.location.factor(location_ctx)
        factors.append(ContextFactor(name="location", weight=self.weights.location, value=lf, contribution=lf * self.weights.location))
        if location_ctx.status.value == "CURRENT":
            reasons.append(f"location: {location_ctx.source} ({location_ctx.confidence:.0%})")

        # Historical factor
        hf = self.history.factor(history_ctx)
        factors.append(ContextFactor(name="historical", weight=self.weights.historical, value=hf, contribution=hf * self.weights.historical))
        if history_ctx.nearby_incidents > 0:
            reasons.append(f"{history_ctx.nearby_incidents} recent nearby incidents")

        # Proximity factor
        pf = self.proximity.factor(security_ctx)
        factors.append(ContextFactor(name="proximity", weight=self.weights.proximity, value=pf, contribution=pf * self.weights.proximity))
        if security_ctx.nearest_security_distance_meters is not None:
            reasons.append(f"nearest security: {security_ctx.nearest_security_distance_meters:.0f}m")

        # Isolation factor
        if_ = isolation_ctx.score
        factors.append(ContextFactor(name="isolation", weight=self.weights.isolation, value=if_, contribution=if_ * self.weights.isolation))
        if isolation_ctx.status.value in ("ELEVATED", "HIGH"):
            reasons.append("elevated isolation")

        # Environment factor
        ef = 0.0
        if env_ctx.status.value == "AVAILABLE" and env_ctx.data:
            # Could add weather logic here
            pass
        factors.append(ContextFactor(name="environment", weight=self.weights.environment, value=ef, contribution=ef * self.weights.environment))

        # Sum contributions
        total_weight = sum(f.weight for f in factors)
        if total_weight <= 0:
            score = 0.0
        else:
            score = sum(f.contribution for f in factors) / total_weight
        score = max(0.0, min(1.0, score))

        # Data quality = fraction of available sub-contexts
        available = 0
        total = 6
        if location_ctx.status != "UNKNOWN":
            available += 1
        if time_ctx.period != TimePeriod.UNKNOWN:
            available += 1
        if history_ctx.available:
            available += 1
        if security_ctx.nearest_security_distance_meters is not None:
            available += 1
        if isolation_ctx.status != "UNKNOWN":
            available += 1
        if env_ctx.status != "UNAVAILABLE":
            available += 1
        data_quality = available / total

        # Confidence = weighted data quality
        confidence = data_quality * (1.0 - 0.2 * score)  # slightly lower confidence when score is high
        confidence = max(0.0, min(1.0, confidence))

        degraded = not (data_quality >= 0.83)

        return ContextResult(
            time=time_ctx,
            location=location_ctx,
            people=people_ctx,
            history=history_ctx,
            isolation=isolation_ctx,
            security=security_ctx,
            environment=env_ctx,
            context_score=round(score, 4),
            context_confidence=round(confidence, 4),
            data_quality=round(data_quality, 4),
            factors=factors,
            reasons=reasons,
            degraded=degraded,
        )
