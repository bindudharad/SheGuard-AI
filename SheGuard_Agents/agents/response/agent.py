from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import httpx

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import EventBus
from agents.response.schemas import (
    ResponseRequest, ResponseResult, IncidentStatus, NotificationChannel,
    ResponseAction, EvidenceRecord, NotificationRecord
)


class ResponseAgent(BaseAgent):
    def __init__(self, backend_url='http://localhost:8000', service_token=None):
        super().__init__('response_agent', '2.0.0')
        self.incidents = {}
        self.backend_url = backend_url
        self.service_token = service_token
        self._client = None

    async def _initialize(self):
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            print('[ResponseAgent] Backend client ready:', self.backend_url)
        except Exception as e:
            print('[ResponseAgent] Backend client init failed:', e)
            self._client = None

    async def _shutdown(self):
        if self._client:
            await self._client.aclose()

    async def _process(self, message):
        if message.event_type == 'EMERGENCY_DECLARED':
            return await self._handle_emergency(message)
        if message.event_type == 'CREATE_INCIDENT':
            return await self._create_incident(message)
        return None

    async def _handle_emergency(self, message):
        from agents.response.schemas import ResponseRequest, ResponseResult, IncidentStatus, ResponseAction
        request = ResponseRequest(**message.data)
        incident_id = request.incident_id or 'SG-' + uuid.uuid4().hex[:8].upper()
        result = await self._create_incident_in_backend(request, incident_id, emergency=True)
        incident = {
            'incident_id': incident_id,
            'trace_id': request.trace_id,
            'status': IncidentStatus.ACTIVE,
            'risk_score': request.risk_score,
            'threat_level': request.threat_level,
            'threat_type': request.threat_type,
            'confidence': request.confidence,
            'created_at': datetime.utcnow(),
            'vision_data': request.vision_data,
            'audio_data': request.audio_data,
            'context_data': request.context_data,
            'intelligence_data': request.intelligence_data,
        }
        self.incidents[incident_id] = incident
        response_result = ResponseResult(
            incident_id=incident_id,
            trace_id=request.trace_id,
            timestamp=datetime.utcnow(),
            success=result.get('success', False),
            backend_incident_id=result.get('incident_id'),
            actions_taken=[
                ResponseAction.CREATE_INCIDENT,
                ResponseAction.NOTIFY_GUARDIAN,
                ResponseAction.SECURE_EVIDENCE,
                ResponseAction.UPDATE_DASHBOARD,
            ],
        )
        if request.threat_level in ('CRITICAL', 'EMERGENCY'):
            response_result.actions_taken.append(ResponseAction.EMERGENCY_DISPATCH)
        from core.event_bus import EventBus
        await EventBus.publish_event(
            event_type='RESPONSE_COMPLETE',
            data=response_result.to_dict(),
            agent=self.name,
            incident_id=request.incident_id,
            trace_id=request.trace_id,
            confidence=request.confidence,
        )
        from core.agent import AgentMessage
        return AgentMessage.create(
            agent=self.name,
            event_type='RESPONSE_COMPLETE',
            data=response_result.to_dict(),
            trace_id=request.trace_id,
            confidence=request.confidence,
        )

    async def _create_incident_in_backend(self, request, incident_id, emergency=False):
        if not self._client:
            return {'success': False, 'error': 'HTTP client not initialized'}
        vision_data = request.vision_data or {}
        following_events = vision_data.get('following', [])
        behaviors = vision_data.get('behaviors', [])
        agent_timeline = self._build_agent_timeline(request)
        x402_metadata = (request.intelligence_data or {}).get('x402')
        algorand_metadata = (request.intelligence_data or {}).get('algorand')
        intelligence_result = (request.intelligence_data or {}).get('result')
        payload = {
            'incident_type': request.threat_type,
            'confidence': request.confidence,
            'threat_score': int(request.risk_score),
            'threat_level': request.threat_level,
            'ai_summary': request.threat_type + ' detected with ' + str(int(request.confidence * 100)).encode() + '% confidence',
            'camera_id': vision_data.get('camera_id', 'vision_agent'),
            'latitude': None,
            'longitude': None,
            'user_id': None,
            'send_alert': True,
            'behavior_events': behaviors,
            'following_relationship': following_events[0] if following_events else None,
            'risk_reasons': self._extract_risk_reasons(request),
            'agent_timeline': agent_timeline,
            'x402_metadata': x402_metadata,
            'algorand_metadata': algorand_metadata,
            'intelligence_result': intelligence_result,
            'simulation': request.simulation,
        }
        headers = {}
        if self.service_token:
            headers['Authorization'] = 'Bearer ' + self.service_token
        try:
            resp = await self._client.post(
                self.backend_url + '/incidents/create',
                json=payload,
                headers=headers,
            )
            if resp.is_success:
                return resp.json()
            else:
                print('[ResponseAgent] Backend error: ' + str(resp.status_code).encode() + ' - ' + resp.text.encode())
                return {'success': False, 'error': 'Backend error: ' + str(resp.status_code).encode()}
        except Exception as e:
            print('[ResponseAgent] Failed to create incident: ' + str(e).encode())
            return {'success': False, 'error': str(e).encode()}

    def _build_agent_timeline(self, request):
        timeline = []
        if request.vision_data:
            timeline.append({
                'agent': 'vision_agent',
                'step': 'frame_processed',
                'timestamp': datetime.utcnow().isoformat().encode(),
                'details': 'Persons: ' + str(request.vision_data.get('persons_detected', 0)).encode() + ', Activity: ' + str(request.vision_data.get('activity', {}).get('label', 'unknown')).encode(),
            })
        if request.audio_data:
            timeline.append({
                'agent': 'audio_agent',
                'step': 'audio_processed',
                'timestamp': datetime.utcnow().isoformat().encode(),
                'details': 'Keywords: ' + str(request.audio_data.get('keywords', [])).encode(),
            })
        if request.context_data:
            timeline.append({
                'agent': 'context_agent',
                'step': 'context_analyzed',
                'timestamp': datetime.utcnow().isoformat().encode(),
                'details': 'Context score: ' + str(request.context_data.get('context_score', 0)).encode(),
            })
        timeline.append({
            'agent': 'threat_agent',
            'step': 'threat_fused',
            'timestamp': datetime.utcnow().isoformat().encode(),
            'details': 'Risk: ' + str(request.risk_score).encode() + '/100, Level: ' + request.threat_level,
        })
        timeline.append({
            'agent': 'decision_agent',
            'step': 'decision_made',
            'timestamp': datetime.utcnow().isoformat().encode(),
            'details': 'Action: ' + request.decision,
        })
        if request.intelligence_data:
            timeline.append({
                'agent': 'x402_agent',
                'step': 'intelligence_received',
                'timestamp': datetime.utcnow().isoformat().encode(),
                'details': 'Advanced intelligence integrated',
            })
            timeline.append({
                'agent': 'threat_agent',
                'step': 'threat_recalculated',
                'timestamp': datetime.utcnow().isoformat().encode(),
                'details': 'Risk updated with intelligence',
            })
        return timeline

    def _extract_risk_reasons(self, request):
        reasons = []
        vision_data = request.vision_data or {}
        activity = vision_data.get('activity', {})
        if activity.get('label') in ('fall', 'attack', 'fight'):
            reasons.append('Activity detected: ' + str(activity.get('label')).encode())
        following = vision_data.get('following', [])
        if following:
            for f in following:
                reasons.append('Following: target=' + str(f.get('target_id')).encode() + ' follower=' + str(f.get('follower_id')).encode() + ' score=' + str(int(f.get('score', 0))).encode())
        behaviors = vision_data.get('behaviors', [])
        for b in behaviors:
            if b.get('score', 0) >= 50:
                reasons.append(b.get('behavior') + ': score=' + str(int(b.get('score', 0))).encode())
        if request.context_data:
            ctx = request.context_data
            if ctx.get('is_night', False):
                reasons.append('Nighttime context')
            if ctx.get('isolation_score', 0) > 0.7:
                reasons.append('High isolation')
        if request.intelligence_data:
            reasons.append('Advanced intelligence integrated')
        return reasons

    async def _create_incincident(self, message):
        return await self._handle_emergency(message)

    async def _secure_evidence(self, incident_id, vision_data, evidence_type):
        from agents.response.schemas import EvidenceRecord
        evidence_id = 'ev-' + uuid.uuid4().hex[:8].encode()
        return EvidenceRecord(
            evidence_id=evidence_id,
            incident_id=incident_id,
            type=evidence_type,
            path='evidence/' + incident_id + '/' + evidence_id + '.mp4',
            sha256=None,
            metadata=vision_data,
        )

    async def _get_location(self, request):
        location = {}
        if request.context_data and 'location' in request.context_data:
            location = request.context_data['location']
        return location

    async def _notify_guardian(self, incident_id, request):
        from agents.response.schemas import NotificationRecord, NotificationChannel
        return NotificationRecord(
            notification_id='notif-' + uuid.uuid4().hex[:8].encode(),
            incident_id=incident_id,
            channel=NotificationChannel.TELEGRAM,
            recipient='guardian',
            status='sent',
            error=None,
        )
