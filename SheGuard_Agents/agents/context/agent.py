from typing import Optional
from datetime import datetime
import asyncio

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import EventBus
from agents.context.config import get_context_config
from agents.context.schemas import (
    ContextConfig, ContextRequest, ContextResult, ContextWeights,
    TimeContext, LocationContext, CameraContext, PeopleContext,
    HistoryContext, IsolationContext, SecurityContext, EnvironmentContext,
    DataStatus
)
from agents.context.analyzers.context_risk import ContextRiskAnalyzer
from agents.context.providers.camera_provider import CameraProvider
from agents.context.providers.location_provider import LocationProvider
from agents.context.providers.user_provider import UserProvider
from agents.context.providers.incident_provider import IncidentProvider
from agents.context.providers.environment_provider import EnvironmentProvider
from agents.context.analyzers.people_analyzer import PeopleAnalyzer
from agents.context.analyzers.proximity_analyzer import ProximityAnalyzer
from agents.context.analyzers.location_analyzer import LocationAnalyzer
from agents.context.analyzers.zone_analyzer import ZoneAnalyzer
from agents.context.analyzers.history_analyzer import HistoryAnalyzer

class ContextAgent(BaseAgent):
    def __init__(self, config: Optional[ContextConfig] = None):
        super().__init__('context_agent', '1.0.0')
        self.config = config or get_context_config()
        self.risk_analyzer = ContextRiskAnalyzer(self.config.weights)
        self.camera_provider = CameraProvider()
        self.location_provider = LocationProvider()
        self.user_provider = UserProvider()
        self.incident_provider = IncidentProvider()
        self.environment_provider = EnvironmentProvider()
        self.people_analyzer = PeopleAnalyzer()
        self.proximity_analyzer = ProximityAnalyzer()
        self.location_analyzer = LocationAnalyzer()
        self.zone_analyzer = ZoneAnalyzer()
        self.history_analyzer = HistoryAnalyzer()
        
    async def _initialize(self) -> None:
        print('[ContextAgent] Initializing providers...')
        print('[ContextAgent] All providers initialized')
    
    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.event_type == 'CONTEXT_REQUEST':
            return await self._process_context_request(message)
        return None
    
    async def _process_context_request(self, message: AgentMessage) -> AgentMessage:
        request = ContextRequest(**message.data)
        
        timestamp = request.timestamp or datetime.now()
        
        time_ctx = self.risk_analyzer.temporal.analyze(timestamp, self.config.timezone)
        
        location_ctx = self.location_provider.get_location(
            explicit_lat=request.latitude,
            explicit_lon=request.longitude,
            explicit_source=request.location_source,
            explicit_ts=request.location_timestamp,
            camera_id=request.camera_id
        )
        
        camera_ctx = self.camera_provider.get_camera(request.camera_id)
        
        people_ctx = self.people_analyzer.analyze(
            person_count=request.person_count,
            tracked_people=request.tracked_people,
            interaction_participants=request.interaction_participants
        )
        
        history_records = self.incident_provider.get_recent(
            lookback_hours=self.config.lookback_hours,
            ref_lat=request.latitude,
            ref_lon=request.longitude,
            radius_meters=self.config.nearby_radius_meters
        )
        
        history_context = HistoryContext(
            recent_incidents=len(history_records),
            weighted_score=0.0,
            status=DataStatus.AVAILABLE if history_records else DataStatus.UNAVAILABLE
        )
        
        isolation_ctx = IsolationContext(status='UNKNOWN', score=0.0, reasons=[])
        
        security_ctx = SecurityContext()
        
        env_ctx = EnvironmentContext(status='NOT_REQUESTED')
        
        result = self.risk_analyzer.compute(
            time_ctx=time_ctx,
            location_ctx=location_ctx,
            people_ctx=people_ctx,
            history_ctx=history_context,
            isolation_ctx=isolation_ctx,
            security_ctx=security_ctx,
            env_ctx=env_ctx
        )
        
        result.incident_id = request.incident_id
        result.trace_id = request.trace_id
        result.timestamp = timestamp
        
        event_type = 'CONTEXT_UPDATED'
        confidence = result.context_confidence
        
        await EventBus.publish_event(
            event_type=event_type,
            data=result.dict(),
            agent=self.name,
            incident_id=request.incident_id,
            trace_id=message.trace_id,
            confidence=confidence
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type=event_type,
            data=result.dict(),
            trace_id=message.trace_id,
            confidence=confidence
        )
    
    async def health(self) -> AgentHealth:
        health = await super().health()
        health.component_status = {
            'risk_analyzer': 'READY',
            'camera_provider': 'READY',
            'location_provider': 'READY',
            'user_provider': 'READY',
            'incident_provider': 'READY',
            'environment_provider': 'READY',
        }
        return health
    
    async def shutdown(self) -> None:
        await super().shutdown()
        print('[ContextAgent] Shutdown complete')
