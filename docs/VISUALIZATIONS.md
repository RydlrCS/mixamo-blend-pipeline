# Visualization and Dashboard Module

## Overview

This module provides comprehensive visualization and charting capabilities for the Mixamo Blend Pipeline, adapted from the [kijani-spiral](https://github.com/RydlrCS/kijani-spiral) project.

Features include:
- **Radar Charts** - Agent capabilities and performance analysis
- **Line Charts** - Reward curves and performance metrics over time
- **Bar Charts** - Comparative analysis and final rewards
- **Learning Curves** - Q-learning training progress with moving averages
- **Mission Timelines** - Animated GIF visualization of agent movement
- **Summary Tables** - Agent performance statistics and summaries
- **Complete Dashboards** - Multi-panel comprehensive visualizations

## Modules

### `src/utils/visualizations.py`

Core visualization functions for charts, animations, and tables.

#### Available Functions

**Radar Charts:**
```python
from src.utils.visualizations import create_agent_capabilities_radar

fig = create_agent_capabilities_radar(
    agent_stats={
        "scout": {"health": 85, "speed": 95, "strength": 60},
        "medic": {"health": 90, "speed": 70, "strength": 65}
    },
    title="Agent Capabilities Radar"
)
plt.show()
```

**Reward Curves:**
```python
from src.utils.visualizations import create_reward_curve

fig = create_reward_curve(
    reward_history={
        "agent1": [1.0, 2.5, 4.2, 6.8, 10.1],
        "agent2": [0.8, 2.1, 3.9, 6.2, 9.5]
    },
    title="Cumulative Reward Over Time"
)
plt.show()
```

**Performance Metrics:**
```python
from src.utils.visualizations import create_performance_metrics_chart

fig = create_performance_metrics_chart(
    metrics_history={
        "agent1": {
            "health": [100, 95, 90, 85],
            "morale": [0.9, 0.85, 0.8, 0.75],
            "energy": [100, 80, 60, 40]
        }
    },
    title="Agent Performance Metrics Over Time"
)
plt.show()
```

**Learning Curves:**
```python
from src.utils.visualizations import create_learning_curve

fig = create_learning_curve(
    training_history={
        "agent1": [1.2, 3.4, 5.2, 8.1, 12.5, ...],
        "agent2": [1.0, 2.8, 4.9, 7.5, 11.2, ...]
    },
    title="Q-Learning Training Progress"
)
plt.show()
```

**Bar Charts:**
```python
from src.utils.visualizations import create_final_rewards_bar_chart

fig = create_final_rewards_bar_chart(
    agent_rewards={"agent1": 15.2, "agent2": 18.7, "agent3": 12.4},
    title="Final Agent Rewards"
)
plt.show()
```

**Mission Timeline Animation:**
```python
from src.utils.visualizations import create_mission_timeline_gif

gif_path = create_mission_timeline_gif(
    trajectories={
        "scout": [(0.1, 0.1), (0.2, 0.15), (0.3, 0.2), ...],
        "medic": [(0.5, 0.5), (0.55, 0.5), (0.6, 0.51), ...]
    },
    title_prefix="Mission Timeline",
    duration=0.15  # Frame duration in seconds
)
print(f"GIF saved to: {gif_path}")
```

**Mission Snapshot:**
```python
from src.utils.visualizations import create_mission_snapshot

fig = create_mission_snapshot(
    trajectories=agent_trajectories,
    current_timestep=10,
    title="Agent Positions at T=10"
)
plt.show()
```

**Summary Tables:**
```python
from src.utils.visualizations import (
    create_performance_summary_table,
    create_statistics_summary,
    AgentPerformance
)

performances = [
    AgentPerformance(
        agent_id="scout",
        health=85.5,
        morale=0.87,
        energy=72.3,
        total_reward=15.2,
        objectives_completed=3
    ),
    # ... more agents
]

# Option 1: Returns pandas DataFrame if available
table = create_performance_summary_table(performances)
print(table)

# Option 2: Returns formatted string
stats = create_statistics_summary(performances)
print(stats)
```

### `src/utils/dashboard.py`

High-level dashboard functions combining multiple visualizations.

#### Available Dashboards

**Mission Performance Dashboard:**
```python
from src.utils.dashboard import create_mission_performance_dashboard

fig = create_mission_performance_dashboard(
    reward_history=agent_reward_history,
    agent_stats=agent_stats,
    final_rewards=final_rewards,
    title="Mission Performance Dashboard"
)
plt.show()
```

Includes:
- Cumulative reward curves
- Agent capabilities radar
- Final rewards bar chart
- Summary statistics

**Agent Performance Dashboard:**
```python
from src.utils.dashboard import create_agent_performance_dashboard

fig = create_agent_performance_dashboard(
    agent_performances=agent_performance_list,
    metrics_history=metrics_over_time,
    title="Agent Performance Dashboard"
)
plt.show()
```

Includes:
- Health metrics over time
- Morale metrics over time
- Energy metrics over time
- Agent capabilities radar
- Summary statistics table

**Training Analysis Dashboard:**
```python
from src.utils.dashboard import create_training_analysis_dashboard

fig = create_training_analysis_dashboard(
    training_history=episode_rewards_by_agent,
    test_performance=test_scores,
    agent_stats=final_agent_stats,
    title="Training Analysis Dashboard"
)
plt.show()
```

Includes:
- Learning curves with moving averages
- Test performance comparison
- Agent capabilities radar
- Training summary statistics

**Complete Mission Analysis Suite:**
```python
from src.utils.dashboard import create_complete_mission_analysis

figures = create_complete_mission_analysis(
    reward_history=reward_history,
    metrics_history=metrics_history,
    agent_stats=agent_stats,
    final_rewards=final_rewards,
    trajectories=agent_trajectories,
    output_dir="/path/to/output"  # Optional: saves all figures
)

# Access individual figures
mission_perf_fig = figures['mission_performance']
metrics_fig = figures['performance_metrics']
# ... etc
```

## Integration with Metrics

The visualization module integrates seamlessly with the metrics module:

```python
from src.utils.metrics import metrics
from src.utils.visualizations import create_reward_curve, create_performance_metrics_chart

# Track simulation and metrics
with metrics.track_simulation():
    results = run_simulation()

# Record results
metrics.record_simulation_results(
    total_reward=results['total_reward'],
    objectives_completed=results['objectives_completed'],
    average_health=results['average_health'],
    agent_rewards=results['agent_rewards']
)

# Visualize the results
fig = create_reward_curve(metrics_data['reward_history'])
plt.show()
```

## Data Classes

### `AgentPerformance`

Dataclass for storing agent performance metrics:

```python
from src.utils.visualizations import AgentPerformance

perf = AgentPerformance(
    agent_id="scout",
    health=85.5,          # 0-100
    morale=0.87,          # 0.0-1.0
    energy=72.3,          # 0-100
    total_reward=15.2,    # Any float
    objectives_completed=3  # Integer count
)

# Convert to dictionary for table display
perf_dict = perf.to_dict()
```

### `BlendMetrics`

Dataclass for tracking blend operation metrics:

```python
from src.utils.visualizations import BlendMetrics

blend = BlendMetrics(
    operation_id="blend_001",
    start_time=1234567890.0,
    end_time=1234567895.5,
    frames_processed=150,
    method="linear",
    status="success"
)

duration = blend.duration  # 5.5 seconds
```

## Utility Functions

**Save Figures:**
```python
from src.utils.visualizations import save_figure

save_figure(fig, "/path/to/output.png", dpi=300)
```

**Close All Figures:**
```python
from src.utils.visualizations import close_all_figures

# Free memory after creating many figures
close_all_figures()
```

## Optional Dependencies

Some features require additional packages:

- **`imageio`** - Required for GIF generation (mission timeline animations)
- **`pandas`** - Optional for advanced table formatting

Install with:
```bash
pip install imageio pandas
```

If not installed, the module gracefully handles missing dependencies:
- GIF generation returns `None` and logs a warning
- Table generation falls back to plain text formatting

## Examples

### Complete Simulation Analysis

```python
from src.utils.dashboard import create_complete_mission_analysis
from src.utils.visualizations import save_figure
from pathlib import Path

# Collect simulation data
reward_history = {"agent1": [...], "agent2": [...]}
metrics_history = {
    "agent1": {"health": [...], "morale": [...], "energy": [...]},
    "agent2": {...}
}
agent_stats = {
    "agent1": {"health": 85, "speed": 90, "strength": 75},
    "agent2": {...}
}
final_rewards = {"agent1": 15.2, "agent2": 18.7}

# Create all visualizations and save
output_dir = Path("mission_analysis")
figures = create_complete_mission_analysis(
    reward_history=reward_history,
    metrics_history=metrics_history,
    agent_stats=agent_stats,
    final_rewards=final_rewards,
    output_dir=str(output_dir)
)

# All figures automatically saved to output_dir
print(f"Analysis saved to {output_dir}")
```

### Custom Dashboard Combination

```python
import matplotlib.pyplot as plt
from src.utils.visualizations import (
    create_reward_curve,
    create_agent_capabilities_radar,
    create_final_rewards_bar_chart
)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Create individual figures and display in subplots
# (Note: These functions return Figure objects, requiring manual subplot integration)

# Alternative: Use dashboard functions for automatic layout
from src.utils.dashboard import create_mission_performance_dashboard
dashboard_fig = create_mission_performance_dashboard(...)
plt.show()
```

## Notes

- All visualizations support optional `figsize` parameter for customization
- Charts use color palettes from matplotlib's Set1, Set2, Set3, and RdYlGn
- Mission timeline GIF generation is memory-intensive; use for shorter missions
- Tables can be exported to CSV if using pandas:
  ```python
  df = create_performance_summary_table(performances)
  df.to_csv("performance_summary.csv", index=False)
  ```

## Attribution

This visualization module is adapted from the [kijani-spiral](https://github.com/RydlrCS/kijani-spiral) project, which provides multi-agent simulation and visualization capabilities.
