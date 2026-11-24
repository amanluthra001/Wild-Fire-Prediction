"""
Wildfire Multi-Agent Autonomous System (Agentic AI)
===================================================
Architecture:
1. SentinelAgent: Continuous telemetry & ML prediction monitoring, anomaly detection.
2. FireSpreadAgent: Spatial wind propagation physics on the 6x6 grid, downwind sector projection.
3. AutonomousDispatcherAgent: Autonomous resource allocation (air tankers, ground crews, drones) & evacuation management.
4. IncidentCommanderCopilot: Interactive Tool-Calling Conversational Agent for commanders/rangers.
5. MultiAgentOrchestrator: Coordinates agent execution cycles, telemetry synchronization, and incident audit logging.
"""

import os
import json
import time
import math
import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import joblib

# -------------------------------------------------------------------------
# Data Structures
# -------------------------------------------------------------------------

@dataclass
class SectorTelemetry:
    region_id: int
    temperature: float
    relative_humidity: float
    wind_speed: float
    wind_direction: float
    precipitation: float
    prev_burn: float = 0.0
    prev_fire: int = 0
    roll2_sum: float = 0.0
    roll4_sum: float = 0.0
    ml_probability: float = 0.0
    severity: str = "LOW"  # LOW, MODERATE, HIGH, CRITICAL

@dataclass
class SpreadVector:
    origin_region: int
    target_regions: List[int]
    wind_direction_deg: float
    wind_speed_kmh: float
    compass_direction: str
    estimated_rate_of_spread_kmh: float
    urgency: str

@dataclass
class ResourceAllocation:
    squadron_id: str
    resource_type: str  # "Air Tanker", "Helitack", "Ground Crew", "Bulldozer", "Drone"
    assigned_region: int
    status: str  # "DISPATCHED", "EN_ROUTE", "ON_SCENE", "STANDBY"
    eta_minutes: int
    objective: str

@dataclass
class EvacuationOrder:
    region_id: int
    order_type: str  # "ORDER" (Immediate), "ALERT" (Get Ready), "ALL_CLEAR"
    threat_level: str
    designated_shelter: str
    downwind_affected: List[int]
    timestamp: str

@dataclass
class AgentLogEntry:
    timestamp: str
    agent_name: str
    action_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------------------------------
# Helper Functions: 6x6 Grid Spatial Reasoning & Wind Physics
# -------------------------------------------------------------------------

GRID_ROWS = 6
GRID_COLS = 6

def region_to_grid(region_id: int) -> Tuple[int, int]:
    """Convert region_id (1-36) to 0-indexed (row, col)."""
    idx = region_id - 1
    return idx // GRID_COLS, idx % GRID_COLS

def grid_to_region(row: int, col: int) -> Optional[int]:
    """Convert 0-indexed (row, col) to region_id (1-36), or None if out of bounds."""
    if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
        return row * GRID_COLS + col + 1
    return None

def get_compass_bearing(deg: float) -> str:
    """Convert meteorological wind degree (direction from which wind blows) to compass string."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round((deg % 360) / 22.5) % 16
    return dirs[idx]

def calculate_downwind_sectors(origin_region: int, wind_direction_deg: float) -> List[int]:
    """
    In meteorology, wind direction is where the wind comes FROM.
    Fire propagates TOWARDS the opposite direction: (wind_direction_deg + 180) % 360.
    Identifies primary and flank sectors on the 6x6 grid.
    """
    row, col = region_to_grid(origin_region)
    spread_deg = (wind_direction_deg + 180.0) % 360.0
    
    # Calculate step in row (North/South) and col (West/East)
    # Math angle: 0 = East, 90 = North, 180 = West, 270 = South
    # Compass angle: 0 = North, 90 = East, 180 = South, 270 = West
    rad = math.radians(spread_deg)
    # delta_y: North is row decrease (-), South is row increase (+)
    # delta_x: East is col increase (+), West is col decrease (-)
    dx = math.sin(rad)
    dy = -math.cos(rad)
    
    primary_drow = int(round(dy))
    primary_dcol = int(round(dx))
    
    downwind_sectors = []
    
    # Primary line of fire
    r1, c1 = row + primary_drow, col + primary_dcol
    sec1 = grid_to_region(r1, c1)
    if sec1:
        downwind_sectors.append(sec1)
        
    # Secondary reach (2 sectors away if wind is strong)
    r2, c2 = row + 2 * primary_drow, col + 2 * primary_dcol
    sec2 = grid_to_region(r2, c2)
    if sec2 and sec2 not in downwind_sectors:
        downwind_sectors.append(sec2)
        
    # Flanks (lateral spread)
    if primary_drow != 0 and primary_dcol == 0:
        # Blowing strictly N/S -> flanks are E/W
        for dc in [-1, 1]:
            s = grid_to_region(r1, col + dc)
            if s and s not in downwind_sectors:
                downwind_sectors.append(s)
    elif primary_dcol != 0 and primary_drow == 0:
        # Blowing strictly E/W -> flanks are N/S
        for dr in [-1, 1]:
            s = grid_to_region(row + dr, c1)
            if s and s not in downwind_sectors:
                downwind_sectors.append(s)
                
    return downwind_sectors


# -------------------------------------------------------------------------
# 1. Sentinel Agent (Perception & Anomaly Detection)
# -------------------------------------------------------------------------

class SentinelAgent:
    """
    Monitors live weather telemetry, calculates compound fire weather index,
    and runs the trained Stacking ML model to compute risk probabilities.
    """
    def __init__(self, high_threshold: float = 0.70, moderate_threshold: float = 0.40):
        self.name = "Sentinel Perception Agent"
        self.high_threshold = high_threshold
        self.moderate_threshold = moderate_threshold
        self.telemetry_cache: Dict[int, SectorTelemetry] = {}
        
    def evaluate_sector(self, row: Dict[str, Any], ml_prob: float) -> SectorTelemetry:
        rid = int(row.get("region_id", 0))
        temp = float(row.get("temperature", 20.0))
        hum = float(row.get("relative_humidity", 40.0))
        ws = float(row.get("wind_speed", 10.0))
        wd = float(row.get("wind_direction", 0.0))
        precip = float(row.get("precipitation", 0.0))
        
        # Determine Severity based on ML probability + meteorological compounding
        if ml_prob >= self.high_threshold or (temp > 32 and ws > 25 and hum < 20):
            severity = "CRITICAL"
        elif ml_prob >= self.moderate_threshold:
            severity = "HIGH"
        elif ml_prob >= 0.20:
            severity = "MODERATE"
        else:
            severity = "LOW"
            
        telemetry = SectorTelemetry(
            region_id=rid,
            temperature=temp,
            relative_humidity=hum,
            wind_speed=ws,
            wind_direction=wd,
            precipitation=precip,
            prev_burn=float(row.get("prev_burn", 0.0)),
            prev_fire=int(row.get("prev_fire", 0)),
            roll2_sum=float(row.get("roll2_sum", 0.0)),
            roll4_sum=float(row.get("roll4_sum", 0.0)),
            ml_probability=ml_prob,
            severity=severity
        )
        self.telemetry_cache[rid] = telemetry
        return telemetry

    def scan_all_sectors(self, telemetry_list: List[Dict[str, Any]], ml_probabilities: Dict[int, float]) -> List[SectorTelemetry]:
        results = []
        for row in telemetry_list:
            rid = int(row.get("region_id", 0))
            prob = ml_probabilities.get(rid, 0.0)
            st = self.evaluate_sector(row, prob)
            results.append(st)
        return results

    def get_anomalies(self) -> List[SectorTelemetry]:
        """Returns sectors with HIGH or CRITICAL risk."""
        return [s for s in self.telemetry_cache.values() if s.severity in ["HIGH", "CRITICAL"]]


# -------------------------------------------------------------------------
# 2. Fire Spread & Risk Strategist Agent
# -------------------------------------------------------------------------

class FireSpreadAgent:
    """
    Analyzes physical wind vectors, predicts flame propagation paths across
    neighboring sectors, and calculates Rate of Spread (ROS).
    """
    def __init__(self):
        self.name = "Fire Spread & Risk Strategist"
        
    def estimate_rate_of_spread(self, wind_speed_ms: float, temp: float, humidity: float) -> float:
        """
        Estimates Rate of Spread in km/h using simplified Rothermel/Byram formula.
        Base spread + wind amplification factor modulated by fuel dryness.
        """
        wind_kmh = wind_speed_ms * 3.6
        dryness_factor = max(0.5, (temp / max(1.0, humidity)))
        ros = (0.2 + 0.05 * (wind_kmh ** 1.3)) * dryness_factor
        return round(min(ros, 18.0), 2)  # Cap at realistic extreme 18 km/h

    def analyze_spread(self, telemetry: SectorTelemetry) -> SpreadVector:
        downwind = calculate_downwind_sectors(telemetry.region_id, telemetry.wind_direction)
        ros = self.estimate_rate_of_spread(telemetry.wind_speed, telemetry.temperature, telemetry.relative_humidity)
        bearing = get_compass_bearing(telemetry.wind_direction)
        
        # Opposite direction is the propagation direction
        spread_deg = (telemetry.wind_direction + 180.0) % 360.0
        spread_bearing = get_compass_bearing(spread_deg)
        
        if telemetry.severity == "CRITICAL":
            urgency = "IMMEDIATE_THREAT"
        elif telemetry.severity == "HIGH":
            urgency = "ELEVATED_WATCH"
        else:
            urgency = "NORMAL_MONITOR"
            
        return SpreadVector(
            origin_region=telemetry.region_id,
            target_regions=downwind,
            wind_direction_deg=telemetry.wind_direction,
            wind_speed_kmh=round(telemetry.wind_speed * 3.6, 1),
            compass_direction=f"{bearing} -> {spread_bearing}",
            estimated_rate_of_spread_kmh=ros,
            urgency=urgency
        )

    def generate_tactical_briefing(self, telemetry: SectorTelemetry, spread: SpreadVector) -> str:
        """Generates chain-of-thought tactical summary for human commanders."""
        downwind_str = ", ".join(f"Sector {r}" for r in spread.target_regions) if spread.target_regions else "Boundary / Perimeter Edge"
        return (
            f"Sector {telemetry.region_id} is at {telemetry.severity} danger level (ML Risk: {telemetry.ml_probability:.1%}). "
            f"Prevailing wind from {get_compass_bearing(telemetry.wind_direction)} at {spread.wind_speed_kmh} km/h "
            f"is driving projected fire propagation towards {downwind_str}. "
            f"Projected Rate of Spread is {spread.estimated_rate_of_spread_kmh} km/h. "
            f"Immediate containment or pre-emptive perimeter wetting required."
        )


# -------------------------------------------------------------------------
# 3. Autonomous Dispatcher & Resource Agent
# -------------------------------------------------------------------------

class AutonomousDispatcherAgent:
    """
    Decides resource allocation, issues evacuation protocols, and dispatches
    alerts to emergency responders without requiring human micro-management.
    """
    def __init__(self):
        self.name = "Autonomous Dispatcher Agent"
        self.active_dispatches: List[ResourceAllocation] = []
        self.active_evacuations: List[EvacuationOrder] = []
        self.incident_log: List[AgentLogEntry] = []
        
    def dispatch_for_sector(self, telemetry: SectorTelemetry, spread: SpreadVector) -> List[ResourceAllocation]:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dispatches = []
        
        if telemetry.severity == "CRITICAL":
            # Air Tanker Squadron
            tanker = ResourceAllocation(
                squadron_id=f"AT-{telemetry.region_id}-A",
                resource_type="Conair CL-415 Water Bomber",
                assigned_region=telemetry.region_id,
                status="DISPATCHED",
                eta_minutes=12,
                objective="Deliver retardant drops along head of fire"
            )
            # Helitack for Spot fires
            heli = ResourceAllocation(
                squadron_id=f"HELI-{telemetry.region_id}",
                resource_type="Bell 412 Helitack Crew",
                assigned_region=telemetry.region_id,
                status="EN_ROUTE",
                eta_minutes=8,
                objective="Precision bucket drops & spot fire suppression"
            )
            # Heavy Bulldozers for firebreak
            dozer = ResourceAllocation(
                squadron_id=f"BULLDOZER-CAT9",
                resource_type="Heavy Earthmoving Unit",
                assigned_region=spread.target_regions[0] if spread.target_regions else telemetry.region_id,
                status="DISPATCHED",
                eta_minutes=25,
                objective="Cut 50-meter perimeter firebreak to halt downwind advance"
            )
            dispatches.extend([tanker, heli, dozer])
            
            # Evacuation Order
            evac = EvacuationOrder(
                region_id=telemetry.region_id,
                order_type="TACTICAL_EVACUATION_ORDER",
                threat_level="EXTREME_IMMEDIATE",
                designated_shelter=f"Kelowna Community Centre West (Sector {(telemetry.region_id % 6) + 30})",
                downwind_affected=spread.target_regions,
                timestamp=now
            )
            self.active_evacuations.append(evac)
            
        elif telemetry.severity == "HIGH":
            # Ground Crew + Drone Patrol
            ground = ResourceAllocation(
                squadron_id=f"GC-UNIT-{telemetry.region_id}",
                resource_type="Type-1 Initial Attack Fire Crew (20 Personnel)",
                assigned_region=telemetry.region_id,
                status="DISPATCHED",
                eta_minutes=18,
                objective="Establish wet hose line and structure protection"
            )
            drone = ResourceAllocation(
                squadron_id=f"DRONE-RECON-{telemetry.region_id}",
                resource_type="Autonomous FLIR Thermal Drone",
                assigned_region=telemetry.region_id,
                status="ON_SCENE",
                eta_minutes=3,
                objective="Continuous 4K thermal telemetry & hotspot identification"
            )
            dispatches.extend([ground, drone])
            
            # Evacuation Alert
            evac = EvacuationOrder(
                region_id=telemetry.region_id,
                order_type="EVACUATION_ALERT",
                threat_level="HIGH_PREPAREDNESS",
                designated_shelter=f"Okanagan Regional Hub",
                downwind_affected=spread.target_regions,
                timestamp=now
            )
            self.active_evacuations.append(evac)
            
        self.active_dispatches.extend(dispatches)
        
        # Log to immutable audit trail
        self.incident_log.append(AgentLogEntry(
            timestamp=now,
            agent_name=self.name,
            action_type="EMERGENCY_DISPATCH",
            message=f"Autonomous response activated for Sector {telemetry.region_id}. Dispatched {len(dispatches)} tactical units.",
            details={
                "region_id": telemetry.region_id,
                "dispatches": [asdict(d) for d in dispatches],
                "downwind": spread.target_regions
            }
        ))
        
        return dispatches


# -------------------------------------------------------------------------
# 4. Incident Commander Copilot (Interactive Tool-Calling Agent)
# -------------------------------------------------------------------------

class IncidentCommanderCopilot:
    """
    Conversational Agent equipped with function tools. Can be queried by human
    rangers/commanders in natural language (English/Hinglish).
    Uses registered tools to retrieve real-time state, simulate conditions, and run orders.
    """
    def __init__(self, orchestrator: "MultiAgentWildfireSystem"):
        self.name = "Incident Commander AI Copilot"
        self.orchestrator = orchestrator
        self.tools = {
            "get_critical_sectors": self.tool_get_critical_sectors,
            "get_sector_status": self.tool_get_sector_status,
            "simulate_wind_shift": self.tool_simulate_wind_shift,
            "dispatch_custom_unit": self.tool_dispatch_custom_unit,
            "generate_incident_summary": self.tool_generate_incident_summary
        }

    def tool_get_critical_sectors(self) -> str:
        """Tool: Returns all sectors currently under HIGH or CRITICAL alert."""
        anomalies = self.orchestrator.sentinel.get_anomalies()
        if not anomalies:
            return "✅ Status Green: No sectors currently exceed critical fire risk thresholds."
        lines = ["🚨 **Active Threat Sectors:**"]
        for a in anomalies:
            lines.append(f"- **Sector {a.region_id}**: Risk={a.ml_probability:.1%}, Severity={a.severity}, Temp={a.temperature}°C, Wind={a.wind_speed*3.6:.1f} km/h")
        return "\n".join(lines)

    def tool_get_sector_status(self, sector_id: int) -> str:
        """Tool: Retrieves deep operational breakdown of a specific sector."""
        if sector_id not in self.orchestrator.sentinel.telemetry_cache:
            return f"❌ Sector {sector_id} not found in active telemetry grid (Valid: 1-36)."
        st = self.orchestrator.sentinel.telemetry_cache[sector_id]
        spread = self.orchestrator.spread_agent.analyze_spread(st)
        briefing = self.orchestrator.spread_agent.generate_tactical_briefing(st, spread)
        return (
            f"### 📍 Sector {sector_id} Tactical Profile\n"
            f"- **ML Fire Risk:** `{st.ml_probability:.1%}` ({st.severity})\n"
            f"- **Telemetry:** Temp: `{st.temperature}°C` | Humidity: `{st.relative_humidity}%` | Wind: `{st.wind_speed*3.6:.1f} km/h` @ `{st.wind_direction}°` | Rain: `{st.precipitation} mm`\n"
            f"- **Fire History:** Prev Burn Index: `{st.prev_burn}` | Rolling 2-Qtr Fire: `{st.roll2_sum}`\n"
            f"- **Propagation Path:** {spread.compass_direction} -> Projected Spread: `{spread.estimated_rate_of_spread_kmh} km/h`\n"
            f"- **Tactical Assessment:** {briefing}"
        )

    def tool_simulate_wind_shift(self, sector_id: int, new_wind_speed_kmh: float, new_wind_dir_deg: float) -> str:
        """Tool: Simulates 'what-if' weather scenario to evaluate new fire spread paths."""
        if sector_id not in self.orchestrator.sentinel.telemetry_cache:
            return f"❌ Sector {sector_id} not found in telemetry grid."
        current = self.orchestrator.sentinel.telemetry_cache[sector_id]
        
        # Create simulated clone
        simulated = SectorTelemetry(
            region_id=sector_id,
            temperature=current.temperature,
            relative_humidity=current.relative_humidity,
            wind_speed=new_wind_speed_kmh / 3.6,
            wind_direction=new_wind_dir_deg,
            precipitation=current.precipitation,
            prev_burn=current.prev_burn,
            prev_fire=current.prev_fire,
            roll2_sum=current.roll2_sum,
            roll4_sum=current.roll4_sum,
            ml_probability=min(0.99, current.ml_probability * 1.15 if new_wind_speed_kmh > 25 else current.ml_probability),
            severity="CRITICAL" if new_wind_speed_kmh > 30 else current.severity
        )
        sim_spread = self.orchestrator.spread_agent.analyze_spread(simulated)
        downwind_str = ", ".join(f"Sector {r}" for r in sim_spread.target_regions) if sim_spread.target_regions else "Outside Perimeter"
        
        return (
            f"🧪 **Simulation Results for Sector {sector_id}**\n"
            f"- **Simulated Wind:** `{new_wind_speed_kmh} km/h` from `{get_compass_bearing(new_wind_dir_deg)}` ({new_wind_dir_deg}°)\n"
            f"- **New Rate of Spread:** `{sim_spread.estimated_rate_of_spread_kmh} km/h`\n"
            f"- **Vulnerable Sectors in Direct Path:** `{downwind_str}`\n"
            f"- **Advisory:** Immediately alert emergency management in `{downwind_str}` if wind shifts to {new_wind_dir_deg}°."
        )

    def tool_dispatch_custom_unit(self, sector_id: int, unit_type: str) -> str:
        """Tool: Manually dispatches a squadron via agent authorization."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alloc = ResourceAllocation(
            squadron_id=f"MANUAL-{unit_type[:3].upper()}-{sector_id}",
            resource_type=unit_type,
            assigned_region=sector_id,
            status="DISPATCHED",
            eta_minutes=15,
            objective="Commander Directed Intercept"
        )
        self.orchestrator.dispatcher.active_dispatches.append(alloc)
        self.orchestrator.dispatcher.incident_log.append(AgentLogEntry(
            timestamp=now,
            agent_name=self.name,
            action_type="COMMANDER_DIRECTED_DISPATCH",
            message=f"Manual order executed: Dispatched {unit_type} to Sector {sector_id}."
        ))
        return f"🚀 **Order Executed:** Dispatched `{unit_type}` to Sector `{sector_id}` (ETA: 15 mins). Log entry recorded."

    def tool_generate_incident_summary(self) -> str:
        """Tool: Generates executive operational brief."""
        total_sectors = len(self.orchestrator.sentinel.telemetry_cache)
        anomalies = self.orchestrator.sentinel.get_anomalies()
        dispatches = self.orchestrator.dispatcher.active_dispatches
        evacuations = self.orchestrator.dispatcher.active_evacuations
        
        return (
            f"📋 **Wildfire Operations Incident Command Summary**\n"
            f"- **Monitored Sectors:** `{total_sectors}`\n"
            f"- **Active High/Critical Threats:** `{len(anomalies)}`\n"
            f"- **Active Tactical Units Dispatched:** `{len(dispatches)}`\n"
            f"- **Evacuation Orders / Alerts in Effect:** `{len(evacuations)}`\n"
            f"- **System Posture:** `{'DEFCON 1 - CRITICAL' if any(a.severity == 'CRITICAL' for a in anomalies) else 'STANDBY / ACTIVE PATROL'}`"
        )

    def process_query(self, user_text: str) -> str:
        """
        Processes natural language query using autonomous reasoning & tool execution.
        Handles Hinglish / English inputs naturally.
        """
        import re
        text_lower = user_text.lower()
        
        # Robust Sector ID extraction (1 to 36)
        sector_mentioned = None
        match = re.search(r'\b(?:sector|region|sec|zone|cell|r)?[-_\s]*([1-9]|[1-2][0-9]|3[0-6])\b', text_lower)
        if match:
            try:
                sector_mentioned = int(match.group(1))
            except:
                sector_mentioned = None

        # PRIORITY 1: Specific Sector Targeted Actions
        if sector_mentioned is not None:
            # If user asks for wind/fire simulation on this sector
            if any(w in text_lower for w in ["simulate", "simulation", "what if", "agar hawa", "wind shift"]):
                return self.tool_simulate_wind_shift(sector_mentioned, new_wind_speed_kmh=45.0, new_wind_dir_deg=270.0)
            
            # If user asks to dispatch resources to this sector
            elif any(w in text_lower for w in ["dispatch", "bhejo", "tanker", "crew", "send", "deploy", "resource"]):
                return self.tool_dispatch_custom_unit(sector_mentioned, "CL-415 Water Bomber Squadron")
            
            # All other sector-specific queries (status, risk, temp, detail, batao, kya hai, etc.)
            else:
                return self.tool_get_sector_status(sector_mentioned)

        # PRIORITY 2: General / System-Wide Queries (No specific sector mentioned)
        if any(w in text_lower for w in ["critical", "khatarnak", "high risk", "danger", "khatra", "overview", "threats", "anomalies"]):
            return self.tool_get_critical_sectors()
            
        elif any(w in text_lower for w in ["summary", "report", "briefing", "overall", "status", "system"]):
            return self.tool_generate_incident_summary()
            
        elif any(w in text_lower for w in ["simulate", "what if", "agar hawa", "wind shift"]):
            return self.tool_simulate_wind_shift(14, new_wind_speed_kmh=45.0, new_wind_dir_deg=270.0)
            
        elif any(w in text_lower for w in ["dispatch", "bhejo", "tanker", "crew", "send", "deploy"]):
            return self.tool_dispatch_custom_unit(14, "CL-415 Water Bomber Squadron")
            
        else:
            summary = self.tool_generate_incident_summary()
            critical = self.tool_get_critical_sectors()
            return (
                f"🤖 **Incident Commander AI Copilot**\n\n"
                f"Operational Command System ready. You can query sector-specific tactical telemetry, flame physics simulation, or deploy tactical response units across Sectors 1 through 36.\n\n"
                f"{summary}\n\n"
                f"{critical}\n\n"
                f"💡 *Recommended Directives:* \n"
                f"- `What is the risk and status of Sector 14?`\n"
                f"- `Show overview of critical threat sectors`\n"
                f"- `Simulate severe wind shift for Sector 14`\n"
                f"- `Dispatch CL-415 aerial tanker to Sector 14`"
            )


# -------------------------------------------------------------------------
# 5. Multi-Agent Orchestrator
# -------------------------------------------------------------------------

class MultiAgentWildfireSystem:
    """
    Central Orchestrator that binds Sentinel, Spread, Dispatcher, and Copilot
    agents into a unified reactive autonomous loop.
    """
    def __init__(self, high_threshold: float = 0.70):
        self.sentinel = SentinelAgent(high_threshold=high_threshold)
        self.spread_agent = FireSpreadAgent()
        self.dispatcher = AutonomousDispatcherAgent()
        self.copilot = IncidentCommanderCopilot(self)
        self.last_cycle_timestamp: Optional[str] = None
        
    def run_autonomous_cycle(self, telemetry_data: List[Dict[str, Any]], ml_probabilities: Dict[int, float]) -> Dict[str, Any]:
        """
        Executes one full autonomous cycle:
        1. Perception (Sentinel evaluates all 36 sectors).
        2. Threat Detection (Identifies critical breaches).
        3. Spread Forecasting (Calculates wind trajectories for threats).
        4. Autonomous Action (Dispatches firefighting units & evacuation orders).
        """
        cycle_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_cycle_timestamp = cycle_start
        
        # 1. Perception
        telemetry_results = self.sentinel.scan_all_sectors(telemetry_data, ml_probabilities)
        
        # 2. Anomaly Detection
        anomalies = self.sentinel.get_anomalies()
        
        # 3. Strategy & Spread Reasoning
        spread_results = {}
        briefings = {}
        for a in anomalies:
            spread = self.spread_agent.analyze_spread(a)
            spread_results[a.region_id] = spread
            briefings[a.region_id] = self.spread_agent.generate_tactical_briefing(a, spread)
            
            # 4. Autonomous Action & Dispatch
            self.dispatcher.dispatch_for_sector(a, spread)
            
        return {
            "cycle_timestamp": cycle_start,
            "total_sectors_scanned": len(telemetry_results),
            "anomalies_detected": len(anomalies),
            "anomalous_sectors": [a.region_id for a in anomalies],
            "spread_predictions": {k: asdict(v) for k, v in spread_results.items()},
            "tactical_briefings": briefings,
            "active_dispatches": [asdict(d) for d in self.dispatcher.active_dispatches],
            "active_evacuations": [asdict(e) for e in self.dispatcher.active_evacuations]
        }
