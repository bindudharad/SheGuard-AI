with open('agents/threat/schemas.py', 'r') as f:
    content = f.read()

# Check if EMERGENCY already exists
if "EMERGENCY = 'EMERGENCY'" in content:
    print("EMERGENCY already exists")
else:
    # Add EMERGENCY to ThreatLevel enum
    old = """class ThreatLevel(str, Enum):
    SAFE = 'SAFE'
    WARNING = 'WARNING'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'"""
    
    new = """class ThreatLevel(str, Enum):
    SAFE = 'SAFE'
    WARNING = 'WARNING'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'
    EMERGENCY = 'EMERGENCY'"""
    
    content = content.replace(old, new)
    with open('agents/threat/schemas.py', 'w') as f:
        f.write(content)
    print("Added EMERGENCY to ThreatLevel enum")
