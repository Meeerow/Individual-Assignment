# Investigating Performance Bottlenecks in a Public API Using Artillery-Based Testing

> **Parallel Programming Assignment** | Individual Submission  
> **Target API:** `https://jsonplaceholder.typicode.com/posts`  
> **Primary Tool:** Artillery (YAML configs) + Python orchestration  
> **Language:** Python 3.10+

---

## Table of Contents
1. [Problem Statement](#problem-statement)  
2. [System Requirements](#system-requirements)  
3. [Installation](#installation)  
4. [How to Run](#how-to-run)  
5. [Project Structure](#project-structure)  
6. [Techniques Explained](#techniques-explained)  
7. [Test Types](#test-types)  
8. [Sample Output](#sample-output)  
9. [Artillery YAML Configs](#artillery-yaml-configs)  
10. [Results & Analysis](#results--analysis)  
11. [Demo Video](#demo-video)

---

## Problem Statement

Modern APIs must handle varying traffic patterns — from steady sustained load to sudden spikes. Identifying **where and when** performance degrades is critical for building reliable systems.

This project investigates the performance characteristics of a public REST API (`jsonplaceholder.typicode.com/posts`) under three traffic profiles:

| Test Type | Description |
|-----------|-------------|
| **Load Test** | Simulate normal, sustained traffic (100 requests) |
| **Stress Test** | Exceed normal capacity to find breaking points (300 requests) |
| **Spike Test** | Simulate sudden traffic burst (200 requests at once) |

Each test is executed with **three different Python execution strategies** to compare performance:

| Technique | Category | Description |
|-----------|----------|-------------|
| `asyncio` | **Concurrent** | Single-threaded async I/O via event loop |
| `threading` | **Concurrent** | Multi-threaded via `ThreadPoolExecutor` |
| `multiprocessing` | **Parallel** | Multi-process via `ProcessPoolExecutor` |

---

## System Requirements

| Component | Minimum |
|-----------|---------|
| Python | 3.10 or higher |
| RAM | 512 MB |
| OS | Windows 10 / macOS 12 / Ubuntu 20.04 |
| Internet | Required (fetches live API) |
| Node.js *(optional)* | 18+ (only needed to run Artillery directly) |

---

## Installation

### Step 1 – Clone the Repository

```bash
git clone https://github.com/Meeerow/Individual-Assignment.git
cd Individual-Assignment
```

### Step 2 – Install Python Dependencies

```bash
pip install -r requirements.txt
```

---


## How to Run

### Run the Full Python Test Suite

```bash
python api_performance_tester.py
```

This will:
1. Generate three Artillery YAML config files in `./results/`
2. Run **Load**, **Stress**, and **Spike** tests using all three Python techniques
3. Print a comparison table to the console
4. Save raw + summary JSON files to `./results/`

---

### Run Artillery Tests Directly (Optional)

After running the Python program once (to generate YAML files):

```bash
# Load Test
artillery run results/artillery_load.yml --output results/artillery_load_report.json
artillery report results/artillery_load_report.json

# Stress Test
artillery run results/artillery_stress.yml --output results/artillery_stress_report.json

# Spike Test
artillery run results/artillery_spike.yml --output results/artillery_spike_report.json
```

---

## Project Structure

```
api-performance-tester/
│
├── api_performance_tester.py   # Main program (Python)
├── requirements.txt            # Python dependencies
├── README.md                   # This user manual
│
└── results/                    # Auto-created on first run
    ├── artillery_load.yml      # Artillery config – Load Test
    ├── artillery_stress.yml    # Artillery config – Stress Test
    ├── artillery_spike.yml     # Artillery config – Spike Test
    ├── summary_<timestamp>.json
    └── raw_<timestamp>.json
```

---

## Techniques Explained

### Concurrent Technique A – `asyncio`

```python
async def fetch_post_async(session, post_id, test_type):
    async with session.get(url) as resp:
        await resp.json()
```

- Uses Python's built-in `asyncio` event loop
- All requests are fired from a **single thread**
- The event loop switches between coroutines whenever one is waiting on I/O
- Best for: very high numbers of I/O-bound tasks with low CPU overhead

### Concurrent Technique B – `threading`

```python
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(fetch_post_threaded, args): args ...}
```

- Uses OS threads managed by `ThreadPoolExecutor`
- Python's GIL (Global Interpreter Lock) is released during I/O waits
- Multiple threads can wait on network simultaneously
- Best for: I/O-bound tasks where each task needs its own blocking call

### Parallel Technique – `multiprocessing`

```python
with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
    for result in executor.map(fetch_post_process, args):
        ...
```

- Spawns **separate OS processes** (one per CPU core)
- Each process has its own Python interpreter — **GIL is bypassed**
- True CPU-level parallelism
- Best for: CPU-bound work; adds overhead for pure I/O tasks

---

## Test Types

### Load Test (100 requests)
Simulates normal, sustainable traffic. All 100 available post IDs are fetched once.

### Stress Test (300 requests)  
Each of the 100 posts is fetched 3× to push the API and the client beyond normal operating levels, revealing degradation points.

### Spike Test (200 requests)  
10 posts are requested 20× each, all launched simultaneously, creating a sudden burst to test recovery behaviour.

---

## Sample Output

> The following is the **actual output** from a real test run on this machine.

### Program Startup

```
╔══════════════════════════════════════════════════════╗
║  API Performance Bottleneck Investigator             ║
║  Target : jsonplaceholder.typicode.com/posts         ║
╚══════════════════════════════════════════════════════╝

  Started : 2026-05-03 22:46:01
  CPUs    : 8

── Generating Artillery YAML configs ──
  [✓] Artillery config → results/artillery_load.yml
  [✓] Artillery config → results/artillery_stress.yml
  [✓] Artillery config → results/artillery_spike.yml
```

### Results Saved

```
── Saving Results ──
  [✓] Summary saved → results/summary_20260503_224646.json
  [✓] Raw data saved → results/raw_20260503_224646.json

  [✓] All tests complete.
```

### Performance Comparison Summary (Actual Results)

| Technique        | Test Type | Duration (s) | Throughput  | p95 Latency  |
|------------------|-----------|:------------:|:-----------:|:------------:|
| asyncio          | load      |    1.407     |  71.09 /s   |  1378.86 ms  |
| threading        | load      |    5.712     |  17.51 /s   |  1336.21 ms  |
| multiprocessing  | load      |    7.339     |  13.63 /s   |   850.31 ms  |
|                  |           |              |             |              |
| asyncio          | stress    |    1.056     | 284.22 /s   |   963.15 ms  |
| threading        | stress    |   16.837     |  17.82 /s   |  1361.38 ms  |
| multiprocessing  | stress    |   19.550     |  15.34 /s   |   787.34 ms  |
|                  |           |              |             |              |
| asyncio          | spike     |    0.737     | 271.44 /s   |   693.40 ms  |
| threading        | spike     |   11.529     |  17.35 /s   |  1380.40 ms  |
| multiprocessing  | spike     |   12.922     |  15.48 /s   |   783.53 ms  |

---

## Artillery YAML Configs

The program auto-generates these. They can also be run with the `artillery` CLI:

**Load Test** (`artillery_load.yml`):
- 60-second run at 5 arrivals/second

**Stress Test** (`artillery_stress.yml`):
- 30s warm-up → 60s at 20 arrivals/s → 30s cool-down

**Spike Test** (`artillery_spike.yml`):
- 10s baseline → 5s burst at 100 arrivals/s → 10s recovery

---

## Results & Analysis

### Winner per Test Type

| Test Type | 🥇 Fastest    | 🥈 Second      | 🥉 Slowest      |
|-----------|--------------|----------------|-----------------|
| Load      | asyncio (1.4s)  | threading (5.7s)  | multiprocessing (7.3s) |
| Stress    | asyncio (1.1s)  | threading (16.8s) | multiprocessing (19.6s) |
| Spike     | asyncio (0.7s)  | threading (11.5s) | multiprocessing (12.9s) |

### Key Findings

**1. `asyncio` dominated all 3 test types** — up to 17× faster than threading in the stress test. This is because the API workload is entirely **I/O-bound** (waiting for network). The async event loop fires all requests without creating extra threads or processes.

**2. `threading` performed moderately** — reasonable for low concurrency but degrades at higher loads due to GIL contention and thread management overhead.

**3. `multiprocessing` was slowest here** — spawning separate OS processes is expensive. This technique is designed for **CPU-heavy** tasks (e.g. image processing, data crunching), not network requests.

### Conclusion

> For network I/O workloads like API testing, **asyncio is the best choice**. Multiprocessing should be reserved for CPU-bound parallel tasks where the GIL is a real bottleneck.

---

## Demo Video

▶️ [Watch on YouTube](https://youtube.com/your-link-here)

---

## Source Code

Full source: [`api_performance_tester.py`](./api_performance_tester.py)

---

*Submitted for Parallel Programming Assignment — [Your Institution] — [Date]*
