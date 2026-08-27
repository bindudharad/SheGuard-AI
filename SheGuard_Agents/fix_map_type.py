with open('agents/threat/agent.py', 'r') as f:
    content = f.read()

old = '''    def _map_type(self, behaviors: List[str]) -> ThreatType:
        if not behaviors:
            return ThreatType.NONE
        # Priority order
        for b in ["chasing", "following", "confrontation", "fleeing", "approaching"]:
            if b in behaviors:
                return ThreatType(f"possible_{b}" if b != "chasing" else "possible_physical_aggression")
        if "fall" in behaviors:
            return ThreatType.POSSIBLE_FALL
        if "distress" in behaviors:
            return ThreatType.DISTRESS_KEYWORD
        return ThreatType.ABNORMAL_MOVEMENT'''

new = '''    def _map_type(self, behaviors: List[str]) -> ThreatType:
        if not behaviors:
            return ThreatType.NONE
        # Priority order - map to valid ThreatType enums
        if "chasing" in behaviors:
            return ThreatType.POSSIBLE_PHYSICAL_AGGRESSION
        if "following" in behaviors:
            return ThreatType.POSSIBLE_CONFRONTATION
        if "confrontation" in behaviors:
            return ThreatType.POSSIBLE_CONFRONTATION
        if "fleeing" in behaviors:
            return ThreatType.ABNORMAL_MOVEMENT
        if "approaching" in behaviors:
            return ThreatType.POSSIBLE_CONFRONTATION
        if "fall" in behaviors:
            return ThreatType.POSSIBLE_FALL
        if "distress" in behaviors:
            return ThreatType.DISTRESS_KEYWORD
        return ThreatType.ABNORMAL_MOVEMENT'''

if 'possible_' in content and 'ThreatType(f' in content:
    content = content.replace(old, new)
    with open('agents/threat/agent.py', 'w') as f:
        f.write(content)
    print('Fixed _map_type')
else:
    print('Pattern not found or already fixed')
