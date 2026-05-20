# GidronAI SDK

[![PyPI](https://img.shields.io/pypi/v/gidronai-sdk?color=blue)](https://pypi.org/project/gidronai-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/gidronai-sdk)](https://pypi.org/project/gidronai-sdk/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Official Python SDK for the [GidronAI](https://gidronai.me) cloud API. Generate synthetic training environments, manage simulation jobs, and export datasets programmatically.

## Installation

```bash
pip install gidronai-sdk
```

## Quick Start

```python
from gidronai_sdk import GidronClient

client = GidronClient(api_key="your-api-key")

# Generate a scene
job = client.generate_scene(
    scene_type="urban_intersection",
    num_agents=20,
    weather="rain",
    export_format="coco",
)

# Poll until complete
result = client.wait_for_job(job.job_id, timeout=300)
print(f"Scene ready: {result.output_url}")

# Download the dataset
client.download(result.output_url, dest="./training_data")
```

## API Reference

### `GidronClient`

```python
client = GidronClient(
    api_key="...",
    base_url="https://api.gidronai.me/v1",  # default
    timeout=60,
)
```

### Methods

| Method | Description |
|--------|-------------|
| `generate_scene(**params)` | Submit a scene generation job |
| `get_job(job_id)` | Get status of a job |
| `wait_for_job(job_id, timeout)` | Block until job completes |
| `list_jobs(status, limit)` | List recent jobs |
| `cancel_job(job_id)` | Cancel a running job |
| `export_data(job_id, format)` | Export results in a specific format |
| `download(url, dest)` | Download output files |
| `get_usage()` | Get current billing period usage |

### Scene Parameters

```python
job = client.generate_scene(
    scene_type="urban_intersection",  # or highway_segment, parking_lot, etc.
    size=(200, 200, 50),
    num_agents=20,
    agent_behavior="social_force",    # or orca, boid, waypoint
    weather="clear",                   # clear, overcast, rain, snow, fog
    time_of_day="14:30",
    export_format="coco",              # coco, kitti, nuscenes, raw
    resolution=(1920, 1080),
    num_frames=500,
    physics_dt=0.004167,
)
```

## Error Handling

```python
from gidronai_sdk import GidronError, RateLimitError

try:
    job = client.generate_scene(scene_type="urban_intersection")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except GidronError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## License

MIT License. See [LICENSE](LICENSE) for details.

---

[GidronAI](https://gidronai.me) -- Toronto, Canada.
