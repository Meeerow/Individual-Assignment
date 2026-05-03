"""
============================================================
 Investigating Performance Bottlenecks in a Public API
 Using Artillery-Based Testing (Python Implementation)
------------------------------------------------------------
 Target  : https://jsonplaceholder.typicode.com/posts
 Tool    : Artillery (YAML configs) + Python orchestration
 Author  : [Your Name]
 Subject : Parallel Programming Assignment
============================================================

OVERVIEW
--------
This program investigates API performance bottlenecks by
executing three test types:
  1. Load Test   – sustained normal traffic
  2. Stress Test – traffic ramped beyond normal capacity
  3. Spike Test  – sudden burst of concurrent requests

TECHNIQUES USED
---------------
  • Concurrent  : asyncio + aiohttp  (async I/O)
  • Concurrent  : threading           (thread pool)
  • Parallel    : multiprocessing     (process pool)

Each technique runs the same workload so execution time
and throughput can be directly compared.
"""

import asyncio
import threading
import multiprocessing
import time
import json
import subprocess
import os
import statistics
import aiohttp                    # async HTTP client
import requests                   # sync HTTP client (threads)
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import List, Dict
from datetime import datetime

# ─────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────
TARGET_URL   = "https://jsonplaceholder.typicode.com/posts"
POST_IDS     = list(range(1, 101))   # 100 posts available
RESULTS_DIR  = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────
@dataclass
class RequestResult:
    """Holds the outcome of a single HTTP GET request."""
    post_id     : int
    status_code : int
    latency_ms  : float          # response time in milliseconds
    success     : bool
    technique   : str            # 'asyncio' | 'threading' | 'multiprocessing'
    test_type   : str            # 'load' | 'stress' | 'spike'

@dataclass
class TestSummary:
    """Aggregated statistics for one test run."""
    technique        : str
    test_type        : str
    total_requests   : int
    successful       : int
    failed           : int
    total_duration_s : float
    avg_latency_ms   : float
    min_latency_ms   : float
    max_latency_ms   : float
    p95_latency_ms   : float
    throughput_rps   : float     # requests per second


# ═══════════════════════════════════════════════════════════
# SECTION 1 – CONCURRENT TECHNIQUE A: asyncio (async I/O)
# ═══════════════════════════════════════════════════════════

async def fetch_post_async(session: aiohttp.ClientSession,
                           post_id: int,
                           test_type: str) -> RequestResult:
    """
    Coroutine: fetch a single post asynchronously.
    Uses aiohttp so the event loop is never blocked.
    """
    url   = f"{TARGET_URL}/{post_id}"
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            await resp.json()                        # consume body
            latency = (time.perf_counter() - start) * 1000
            return RequestResult(post_id, resp.status, latency,
                                 resp.status == 200, "asyncio", test_type)
    except Exception:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(post_id, 0, latency, False, "asyncio", test_type)


async def run_asyncio_test(post_ids: List[int], test_type: str) -> List[RequestResult]:
    """
    Concurrent technique – asyncio.
    Fires all requests concurrently within a single thread using
    an event loop; ideal for I/O-bound workloads.
    """
    print(f"  [asyncio] Starting {test_type} test with {len(post_ids)} requests …")
    connector = aiohttp.TCPConnector(limit=0)        # no connection limit
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_post_async(session, pid, test_type) for pid in post_ids]
        results = await asyncio.gather(*tasks)
    return list(results)


# ═══════════════════════════════════════════════════════════
# SECTION 2 – CONCURRENT TECHNIQUE B: threading
# ═══════════════════════════════════════════════════════════

def fetch_post_threaded(args) -> RequestResult:
    """
    Worker function executed in a thread pool.
    Uses the requests library (blocking I/O) inside a thread.
    """
    post_id, test_type = args
    url   = f"{TARGET_URL}/{post_id}"
    start = time.perf_counter()
    try:
        resp    = requests.get(url, timeout=10)
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(post_id, resp.status_code, latency,
                             resp.status_code == 200, "threading", test_type)
    except Exception:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(post_id, 0, latency, False, "threading", test_type)


def run_threading_test(post_ids: List[int], test_type: str,
                       max_workers: int = 20) -> List[RequestResult]:
    """
    Concurrent technique – ThreadPoolExecutor.
    Threads share the same process memory; GIL is released
    during I/O, so multiple threads can wait on network
    simultaneously.
    """
    print(f"  [threading] Starting {test_type} test with {len(post_ids)} requests "
          f"({max_workers} threads) …")
    args = [(pid, test_type) for pid in post_ids]
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_post_threaded, a): a for a in args}
        for future in as_completed(futures):
            results.append(future.result())
    return results


# ═══════════════════════════════════════════════════════════
# SECTION 3 – PARALLEL TECHNIQUE: multiprocessing
# ═══════════════════════════════════════════════════════════

def fetch_post_process(args) -> dict:
    """
    Worker function executed in a separate OS process.
    Returns a plain dict (must be picklable for IPC).
    Bypasses the GIL entirely – true parallelism.
    """
    post_id, test_type = args
    url   = f"{TARGET_URL}/{post_id}"
    start = time.perf_counter()
    try:
        resp    = requests.get(url, timeout=10)
        latency = (time.perf_counter() - start) * 1000
        return {"post_id": post_id, "status_code": resp.status_code,
                "latency_ms": latency, "success": resp.status_code == 200,
                "technique": "multiprocessing", "test_type": test_type}
    except Exception:
        latency = (time.perf_counter() - start) * 1000
        return {"post_id": post_id, "status_code": 0,
                "latency_ms": latency, "success": False,
                "technique": "multiprocessing", "test_type": test_type}


def run_multiprocessing_test(post_ids: List[int], test_type: str,
                             max_workers: int = None) -> List[RequestResult]:
    """
    Parallel technique – ProcessPoolExecutor.
    Spawns separate OS processes (one per CPU core by default).
    Each process has its own Python interpreter and memory space,
    bypassing the Global Interpreter Lock (GIL) for true
    CPU-level parallelism.
    """
    workers = max_workers or multiprocessing.cpu_count()
    print(f"  [multiprocessing] Starting {test_type} test with {len(post_ids)} requests "
          f"({workers} processes) …")
    args = [(pid, test_type) for pid in post_ids]
    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for d in executor.map(fetch_post_process, args):
            results.append(RequestResult(**d))
    return results


# ═══════════════════════════════════════════════════════════
# SECTION 4 – TEST SCENARIOS
# ═══════════════════════════════════════════════════════════

def build_load_test_ids() -> List[int]:
    """
    Load Test – simulate normal sustained traffic.
    All 100 posts fetched once (moderate concurrency).
    """
    return POST_IDS[:]


def build_stress_test_ids() -> List[int]:
    """
    Stress Test – push the system beyond normal capacity.
    Each post is fetched 3× (300 requests total).
    """
    return POST_IDS * 3


def build_spike_test_ids() -> List[int]:
    """
    Spike Test – simulate a sudden burst.
    A small subset (10 posts) fired 20× simultaneously = 200 requests
    all launched at the same instant, creating a sharp spike.
    """
    return (POST_IDS[:10]) * 20


# ═══════════════════════════════════════════════════════════
# SECTION 5 – STATISTICS & REPORTING
# ═══════════════════════════════════════════════════════════

def compute_summary(results: List[RequestResult],
                    duration: float) -> TestSummary:
    """Calculate aggregate statistics from a list of RequestResult objects."""
    latencies  = [r.latency_ms for r in results]
    successful = sum(1 for r in results if r.success)
    sorted_lat = sorted(latencies)
    p95_index  = int(len(sorted_lat) * 0.95)

    return TestSummary(
        technique        = results[0].technique,
        test_type        = results[0].test_type,
        total_requests   = len(results),
        successful       = successful,
        failed           = len(results) - successful,
        total_duration_s = round(duration, 3),
        avg_latency_ms   = round(statistics.mean(latencies), 2),
        min_latency_ms   = round(min(latencies), 2),
        max_latency_ms   = round(max(latencies), 2),
        p95_latency_ms   = round(sorted_lat[p95_index], 2),
        throughput_rps   = round(len(results) / duration, 2),
    )


def print_summary(s: TestSummary):
    """Pretty-print a TestSummary to the console."""
    print(f"\n  ┌─ Result: [{s.technique.upper()}] {s.test_type.capitalize()} Test")
    print(f"  │  Total Requests : {s.total_requests}")
    print(f"  │  Successful     : {s.successful}")
    print(f"  │  Failed         : {s.failed}")
    print(f"  │  Duration       : {s.total_duration_s} s")
    print(f"  │  Throughput     : {s.throughput_rps} req/s")
    print(f"  │  Avg Latency    : {s.avg_latency_ms} ms")
    print(f"  │  Min Latency    : {s.min_latency_ms} ms")
    print(f"  │  Max Latency    : {s.max_latency_ms} ms")
    print(f"  └─ p95 Latency    : {s.p95_latency_ms} ms")


def save_results(summaries: List[TestSummary], all_results: List[RequestResult]):
    """Persist raw results and summaries to JSON files in ./results/."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── summary JSON ──
    summary_path = os.path.join(RESULTS_DIR, f"summary_{ts}.json")
    with open(summary_path, "w") as f:
        json.dump([asdict(s) for s in summaries], f, indent=2)
    print(f"\n  [✓] Summary saved → {summary_path}")

    # ── raw results JSON ──
    raw_path = os.path.join(RESULTS_DIR, f"raw_{ts}.json")
    with open(raw_path, "w") as f:
        json.dump([asdict(r) for r in all_results], f, indent=2)
    print(f"  [✓] Raw data saved → {raw_path}")

    return summary_path, raw_path


# ═══════════════════════════════════════════════════════════
# SECTION 6 – ARTILLERY YAML GENERATOR
# ═══════════════════════════════════════════════════════════

def generate_artillery_config(test_type: str) -> str:
    """
    Generates an Artillery YAML configuration file for the
    specified test type and saves it to ./results/.
    Artillery is a Node.js load-testing tool that can run
    these configs independently of the Python program.
    """
    base = {
        "load": {
            "phases": [{"duration": 60, "arrivalRate": 5, "name": "Load Test"}]
        },
        "stress": {
            "phases": [
                {"duration": 30, "arrivalRate": 5,  "name": "Warm Up"},
                {"duration": 60, "arrivalRate": 20, "name": "Stress"},
                {"duration": 30, "arrivalRate": 5,  "name": "Cool Down"},
            ]
        },
        "spike": {
            "phases": [
                {"duration": 10, "arrivalRate": 2,   "name": "Baseline"},
                {"duration": 5,  "arrivalRate": 100, "name": "Spike"},
                {"duration": 10, "arrivalRate": 2,   "name": "Recovery"},
            ]
        },
    }

    phases_yaml = ""
    for p in base[test_type]["phases"]:
        phases_yaml += (
            f"    - duration: {p['duration']}\n"
            f"      arrivalRate: {p['arrivalRate']}\n"
            f"      name: \"{p['name']}\"\n"
        )

    yaml_content = f"""# Artillery {test_type.capitalize()} Test Configuration
# Target: {TARGET_URL}
# Generated by api_performance_tester.py

config:
  target: "https://jsonplaceholder.typicode.com"
  phases:
{phases_yaml}
  defaults:
    headers:
      Content-Type: "application/json"

scenarios:
  - name: "Fetch Posts"
    flow:
      - loop:
          - get:
              url: "/posts/{{{{ $randomInt(1, 100) }}}}"
              capture:
                - json: "$.id"
                  as: "postId"
        count: 5
"""
    path = os.path.join(RESULTS_DIR, f"artillery_{test_type}.yml")
    with open(path, "w") as f:
        f.write(yaml_content)
    print(f"  [✓] Artillery config → {path}")
    return path


# ═══════════════════════════════════════════════════════════
# SECTION 7 – MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════

def run_test(test_type: str, post_ids: List[int]) -> List[TestSummary]:
    """
    Run one test scenario (load / stress / spike) across all
    three execution techniques and return their summaries.
    """
    summaries = []
    header    = f"{'═'*55}\n  TEST TYPE : {test_type.upper()}\n{'═'*55}"
    print(f"\n{header}")

    # ── 1. asyncio ──────────────────────────────────────────
    t0      = time.perf_counter()
    results = asyncio.run(run_asyncio_test(post_ids, test_type))
    dur     = time.perf_counter() - t0
    s       = compute_summary(results, dur)
    print_summary(s)
    summaries.append(s)

    # ── 2. threading ────────────────────────────────────────
    t0      = time.perf_counter()
    results = run_threading_test(post_ids, test_type)
    dur     = time.perf_counter() - t0
    s       = compute_summary(results, dur)
    print_summary(s)
    summaries.append(s)

    # ── 3. multiprocessing ──────────────────────────────────
    t0      = time.perf_counter()
    results = run_multiprocessing_test(post_ids, test_type)
    dur     = time.perf_counter() - t0
    s       = compute_summary(results, dur)
    print_summary(s)
    summaries.append(s)

    return summaries


def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║  API Performance Bottleneck Investigator             ║")
    print("║  Target : jsonplaceholder.typicode.com/posts         ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  CPUs    : {multiprocessing.cpu_count()}")

    # Generate Artillery YAML configs (can be run separately)
    print("\n── Generating Artillery YAML configs ──")
    for t in ("load", "stress", "spike"):
        generate_artillery_config(t)

    # Run Python-based tests
    all_summaries = []
    all_raw       = []

    # Each test type uses a different traffic pattern (post_ids list)
    test_configs = {
        "load"  : build_load_test_ids(),
        "stress": build_stress_test_ids(),
        "spike" : build_spike_test_ids(),
    }

    for test_type, ids in test_configs.items():
        sums = run_test(test_type, ids)
        all_summaries.extend(sums)

    # Persist results
    print("\n── Saving Results ──")
    save_results(all_summaries, [])

    # Final comparison table
    print("\n╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  PERFORMANCE COMPARISON SUMMARY                                         ║")
    print("╠══════════════╦═══════════════╦══════════════╦═════════════╦════════════╣")
    print("║ Technique    ║ Test Type     ║ Duration (s) ║ Throughput  ║ p95 (ms)   ║")
    print("╠══════════════╬═══════════════╬══════════════╬═════════════╬════════════╣")
    for s in all_summaries:
        print(f"║ {s.technique:<12} ║ {s.test_type:<13} ║ "
              f"{s.total_duration_s:>12.3f} ║ {s.throughput_rps:>9.2f}/s ║ "
              f"{s.p95_latency_ms:>8.2f} ms ║")
    print("╚══════════════╩═══════════════╩══════════════╩═════════════╩════════════╝")
    print("\n  [✓] All tests complete.")


if __name__ == "__main__":
    # Guard required for multiprocessing on Windows / macOS
    multiprocessing.freeze_support()
    main()
