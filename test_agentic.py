"""
Verification script for Agentic AI Wildfire System
"""
import sys
from wildfire_agents import (
    MultiAgentWildfireSystem,
    region_to_grid,
    grid_to_region,
    calculate_downwind_sectors,
    get_compass_bearing
)

def main():
    print("Testing 6x6 spatial wind physics...")
    # Region 14 is Row 2, Col 1
    r, c = region_to_grid(14)
    assert (r, c) == (2, 1), f"Expected (2, 1), got ({r}, {c})"
    assert grid_to_region(r, c) == 14
    
    # Wind FROM West (270°) -> spreads EAST (towards Sector 15)
    downwind = calculate_downwind_sectors(14, 270.0)
    print(f"Sector 14 with Wind from 270 deg (West): Downwind sectors = {downwind}")
    assert 15 in downwind, f"Expected Sector 15 in downwind, got {downwind}"
    
    print("Testing MultiAgentWildfireSystem cycle...")
    system = MultiAgentWildfireSystem(high_threshold=0.70)
    
    # Sample mock telemetry
    mock_telemetry = [
        {
            "region_id": 14,
            "temperature": 35.0,
            "relative_humidity": 18.0,
            "wind_speed": 12.0,  # ~43 km/h
            "wind_direction": 270.0,
            "precipitation": 0.0,
            "prev_burn": 1.0,
            "prev_fire": 1,
            "roll2_sum": 2.0,
            "roll4_sum": 3.0
        },
        {
            "region_id": 1,
            "temperature": 18.0,
            "relative_humidity": 65.0,
            "wind_speed": 3.0,
            "wind_direction": 90.0,
            "precipitation": 5.0,
            "prev_burn": 0.0,
            "prev_fire": 0,
            "roll2_sum": 0.0,
            "roll4_sum": 0.0
        }
    ]
    mock_probs = {14: 0.88, 1: 0.05}
    
    report = system.run_autonomous_cycle(mock_telemetry, mock_probs)
    print(f"Cycle completed successfully!")
    print(f"Total scanned: {report['total_sectors_scanned']}")
    print(f"Anomalies detected: {report['anomalies_detected']}")
    print(f"Anomalous sectors: {report['anomalous_sectors']}")
    print(f"Active Dispatches: {len(report['active_dispatches'])}")
    print(f"Active Evacuations: {len(report['active_evacuations'])}")
    
    print("\nTesting Incident Commander Copilot tools...")
    copilot = system.copilot
    q1 = copilot.process_query("Critical sectors kaunse hain?")
    print("Query 1 Result:\n", q1)
    
    q2 = copilot.process_query("Sector 14 ka status batao")
    print("Query 2 Result:\n", q2)
    
    q3 = copilot.process_query("Simulate wind shift for Sector 14")
    print("Query 3 Result:\n", q3)
    
    print("\nAll Agentic AI tests passed successfully!")

if __name__ == "__main__":
    main()
