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
| OS | Windows 11 / macOS 12 / Ubuntu 20.04 |
| Internet | Required (fetches live API) |
| Node.js *(optional)* | 18+ (only needed to run Artillery directly) |

---

## Installation

### Step 1 – Clone the Repository

```bash
git clone https://github.com/<your-username>/api-performance-tester.git
cd api-performance-tester
```

### Step 2 – Create a Virtual Environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 – Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 – (Optional) Install Artillery

Artillery is a Node.js tool. The Python program auto-generates `.yml` configs for it.

```bash
npm install -g artillery
artillery version   # verify installation
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

> **Last updated:** 2026-05-04 01:27:12

### Performance Comparison Summary (Actual Results)

| Technique        | Test Type | Duration (s) | Throughput   | p95 Latency  |
|------------------|-----------|:------------:|:------------:|:------------:|
| asyncio          | load      |        0.795 |   125.71 /s  |    750.69 ms |
| threading        | load      |       10.547 |     9.48 /s  |   2390.80 ms |
| multiprocessing  | load      |       12.507 |     8.00 /s  |   1302.13 ms |
| asyncio          | stress    |        2.300 |   130.45 /s  |   2173.14 ms |
| threading        | stress    |       30.929 |     9.70 /s  |   2453.79 ms |
| multiprocessing  | stress    |       32.881 |     9.12 /s  |   1291.24 ms |
| asyncio          | spike     |        1.472 |   135.87 /s  |   1385.63 ms |
| threading        | spike     |       20.731 |     9.65 /s  |   2496.09 ms |
| multiprocessing  | spike     |       22.607 |     8.85 /s  |   1283.62 ms |

### Key Finding
- **asyncio** is fastest — no thread/process overhead for I/O-bound tasks
- **threading** performs moderately — GIL released during network waits
- **multiprocessing** slowest here — process spawn overhead not worth it for pure network I/O
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

> **Last updated:** 2026-05-04 01:27:12

### Winner per Test Type

| Test Type | 🥇 Fastest | 🥈 Second | 🥉 Slowest |
|-----------|-----------|----------|-----------|
| Load      | 🥇 asyncio (0.8s)          | 🥈 threading (10.5s)       | 🥉 multiprocessing (12.5s) |
| Stress    | 🥇 asyncio (2.3s)          | 🥈 threading (30.9s)       | 🥉 multiprocessing (32.9s) |
| Spike     | 🥇 asyncio (1.5s)          | 🥈 threading (20.7s)       | 🥉 multiprocessing (22.6s) |

### Key Findings

**1. `asyncio` dominated all 3 test types** — the API workload is entirely I/O-bound. The async event loop fires all requests without extra threads or processes.

**2. `threading` performed moderately** — reasonable for low concurrency but the GIL adds overhead at higher loads.

**3. `multiprocessing` was slowest here** — spawning separate OS processes is expensive for network tasks. Best suited for CPU-heavy work.

> **Conclusion:** For network I/O workloads, **asyncio is the best choice**. Multiprocessing should be reserved for CPU-bound parallel tasks.
## Demo Video

▶️ [Watch on YouTube](https://youtube.com/your-link-here)

---

## Source Code

Full source: [`api_performance_tester.py`](./api_performance_tester.py)

---

*Submitted for 2603-ITT440 Network Programming — Universiti Teknologi MARA (UiTM) — NBCS2555A*
