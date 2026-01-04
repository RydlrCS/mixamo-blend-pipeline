# Quick Reference - Visualizations & Dashboards

## Import Guide

```python
# Individual charts
from src.utils.visualizations import (
    create_agent_capabilities_radar,
    create_reward_curve,
    create_performance_metrics_chart,
    create_learning_curve,
    create_final_rewards_bar_chart,
    create_objectives_completion_chart,
    create_mission_timeline_gif,
    create_mission_snapshot,
    create_performance_summary_table,
    create_statistics_summary,
    AgentPerformance,
    BlendMetrics,
    save_figure,
    close_all_figures,
)

# Complete dashboards
from src.utils.dashboard import (
    create_mission_performance_dashboard,
    create_agent_performance_dashboard,
    create_training_analysis_dashboard,
    create_complete_mission_analysis,
)

# Metrics integration
from src.utils.metrics import metrics
```

## Chart Examples

### Radar Chart - Agent Capabilities
```python
fig = create_agent_capabilities_radar(
    agent_stats={
        "scout": {"health": 85, "speed": 95, "strength": 60},
        "medic": {"health": 90, "speed": 70, "strength": 65}
    }
)
plt.show()
```

### Reward Curve
```python
fig = create_reward_curve(
    reward_history={
        "agent1": [1.0, 2.5, 4.2, 6.8],
        "agent2": [0.8, 2.1, 3.9, 6.2]
    }
)
plt.show()
```

### Performance Metrics (Health/Morale/Energy)
```python
fig = create_performance_metrics_chart(
    metrics_history={
        "agent1": {
            "health": [100, 95, 90, 85],
            "morale": [0.9, 0.85, 0.8, 0.75],
            "energy": [100, 80, 60, 40]
        }
    }
)
plt.show()
```

### Learning Curve
```python
fig = create_learning_curve(
    training_history={
        "agent1": [1.2, 3.4, 5.2, 8.1, 12.5],
        "agent2": [1.0, 2.8, 4.9, 7.5, 11.2]
    }
)
plt.show()
```

### Final Rewards Bar Chart
```python
fig = create_final_rewards_bar_chart(
    agent_rewards={"agent1": 15.2, "agent2": 18.7, "agent3": 12.4}
)
plt.show()
```

### Mission Timeline Animation
```python
gif_path = create_mission_timeline_gif(
    trajectories={
        "scout": [(0.1, 0.1), (0.2, 0.15), (0.3, 0.2)],
        "medic": [(0.5, 0.5), (0.55, 0.5), (0.6, 0.51)]
    }
)
# Returns path to generated GIF file
```

### Mission Snapshot
```python
fig = create_mission_snapshot(
    trajectories=agent_trajectories,
    current_timestep=10
)
plt.show()
```

## Table Examples

### Performance Summary Table
```python
from src.utils.visualizations import AgentPerformance

performances = [
    AgentPerformance(
        agent_id="scout",
        health=85.5,
        morale=0.87,
        energy=72.3,
        total_reward=15.2,
        objectives_completed=3
    ),
    AgentPerformance(
        agent_id="medic",
        health=90.2,
        morale=0.91,
        energy=68.5,
        total_reward=18.7,
        objectives_completed=4
    )
]

# Returns pandas DataFrame (if installed) or formatted string
table = create_performance_summary_table(performances)
print(table)
```

### Statistics Summary
```python
stats = create_statistics_summary(performances)
print(stats)
# Prints mean, median, std, min, max for all metrics
```

## Dashboard Examples

### Mission Performance Dashboard (2x2)
```python
fig = create_mission_performance_dashboard(
    reward_history=agent_reward_history,
    agent_stats=agent_stats,
    final_rewards=final_rewards
)
plt.show()
# Shows: Reward curves, Radar chart, Final rewards, Summary stats
```

### Agent Performance Dashboard (2x3)
```python
fig = create_agent_performance_dashboard(
    agent_performances=agent_performance_list,
    metrics_history=metrics_over_time
)
plt.show()
# Shows: Health/Morale/Energy curves, Radar chart, Summary table
```

### Training Analysis Dashboard
```python
fig = create_training_analysis_dashboard(
    training_history=episode_rewards,
    test_performance=test_scores,
    agent_stats=final_stats
)
plt.show()
# Shows: Learning curves, Test performance, Radar, Summary
```

### Complete Analysis Suite
```python
figures = create_complete_mission_analysis(
    reward_history=reward_history,
    metrics_history=metrics_history,
    agent_stats=agent_stats,
    final_rewards=final_rewards,
    trajectories=trajectories,
    output_dir="/path/to/save"  # Optional
)
# Automatically saves all figures and returns dict of Figure objects
```

## Metrics Integration

### Record Simulation Metrics
```python
from src.utils.metrics import metrics

# Track simulation duration
with metrics.track_simulation():
    results = run_simulation()

# Record complete results
metrics.record_simulation_results(
    total_reward=125.5,
    objectives_completed=3,
    average_health=85.2,
    agent_rewards={"agent1": 42.0, "agent2": 83.5}
)

# Or record individual metrics
metrics.record_agent_health("agent1", 85.5)
metrics.record_agent_morale("agent1", 0.87)
metrics.record_agent_energy("agent1", 72.3)
metrics.record_agent_final_reward("agent1", 42.0)
```

### Success/Failure Tracking
```python
try:
    with metrics.track_simulation():
        results = run_simulation()
    metrics.record_simulation_success()
except Exception as e:
    metrics.record_simulation_failure()
    raise
```

## Data Classes

### AgentPerformance
```python
from src.utils.visualizations import AgentPerformance

perf = AgentPerformance(
    agent_id="scout",
    health=85.5,
    morale=0.87,
    energy=72.3,
    total_reward=15.2,
    objectives_completed=3
)

# Convert to dict for tables
perf_dict = perf.to_dict()
# {'Agent': 'scout', 'Health': '85.5%', 'Morale': '0.87', ...}
```

### BlendMetrics
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

### Save Figure
```python
from src.utils.visualizations import save_figure

save_figure(fig, "/path/to/output.png", dpi=300)
save_figure(fig, "/path/to/output.pdf", dpi=300, format='pdf')
```

### Close All Figures
```python
from src.utils.visualizations import close_all_figures

close_all_figures()  # Free memory after creating many charts
```

## Optional Dependencies

**GIF Generation (imageio):**
```bash
pip install imageio
```

**Advanced Table Formatting (pandas):**
```bash
pip install pandas
```

If not installed, functions gracefully degrade:
- GIFs return `None` (logs warning)
- Tables use plain text format

## Customization Options

All chart functions accept `figsize` and `title` parameters:

```python
fig = create_reward_curve(
    reward_history=data,
    title="Custom Title",
    figsize=(14, 8),  # Width, Height in inches
    xlabel="Custom X Label",
    ylabel="Custom Y Label"
)
```

## Color Schemes

Charts use professional color palettes:
- **Set1, Set2** - Distinct agent colors
- **RdYlGn** - Green=good, Red=bad (reward charts)
- **Blues** - Objectives charts
- **Greens** - Test performance

## Batch Processing

Process multiple missions and save results:

```python
from pathlib import Path

mission_data = [
    {
        'name': 'mission_1',
        'reward_history': {...},
        'metrics_history': {...},
        # ...
    },
    # ... more missions
]

output_dir = Path("mission_results")
output_dir.mkdir(exist_ok=True)

for mission in mission_data:
    mission_output = output_dir / mission['name']
    
    figures = create_complete_mission_analysis(
        reward_history=mission['reward_history'],
        metrics_history=mission['metrics_history'],
        agent_stats=mission['agent_stats'],
        final_rewards=mission['final_rewards'],
        output_dir=str(mission_output)
    )
```

## Export to CSV

For pandas-generated tables:

```python
table = create_performance_summary_table(performances)
if isinstance(table, pd.DataFrame):
    table.to_csv("performance.csv", index=False)
```

## Integration Checklist

- ✅ Import metrics and visualization modules
- ✅ Track operations with `metrics.track_*()`
- ✅ Record results with `metrics.record_*()`
- ✅ Create visualizations with `create_*()` functions
- ✅ Use dashboards for comprehensive views
- ✅ Save figures with `save_figure()`
- ✅ Export tables to CSV if needed
- ✅ Clean up memory with `close_all_figures()`
