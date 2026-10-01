import asyncio
import json
import math
import statistics
import sys
import time


HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
EXPECTED_RESPONSE = b"PONG\n"

CLIENT_COUNT = 10

# Maximum number of clients attempting to connect
# at the same time.
MAX_CONNECT_CONCURRENCY = 100

CONNECT_TIMEOUT = 5
REQUEST_TIMEOUT = 5

IDLE_HOLD_SECONDS = 3

# Keep False during real benchmark runs.
VERBOSE_CLIENTS = False


def percentile(values, percentile_value):
    if not values:
        return None

    values = sorted(values)

    index = math.ceil(
        percentile_value / 100 * len(values)
    ) - 1

    index = max(
        0,
        min(index, len(values) - 1),
    )

    return values[index]


async def run_client(
    client_id,
    connect_semaphore,
    ready_event,
    start_event,
    ready_counter,
    counter_lock,
):
    reader = None
    writer = None

    try:
        async with connect_semaphore:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    HOST,
                    PORT,
                ),
                timeout=CONNECT_TIMEOUT,
            )

        if VERBOSE_CLIENTS:
            print(
                f"Client {client_id}: connected"
            )

        async with counter_lock:
            ready_counter[0] += 1

            if ready_counter[0] == CLIENT_COUNT:
                ready_event.set()

        await start_event.wait()

        start_time = time.perf_counter()

        writer.write(
            REQUEST
        )

        await writer.drain()

        response = await asyncio.wait_for(
            reader.readline(),
            timeout=REQUEST_TIMEOUT,
        )

        latency_ms = (
            time.perf_counter()
            - start_time
        ) * 1000

        if response == EXPECTED_RESPONSE:
            return {
                "client_id": client_id,
                "connected": True,
                "success": True,
                "latency_ms": latency_ms,
                "error": None,
            }

        return {
            "client_id": client_id,
            "connected": True,
            "success": False,
            "latency_ms": None,
            "error": (
                f"Unexpected response: "
                f"{response!r}"
            ),
        }

    except Exception as error:
        return {
            "client_id": client_id,
            "connected": writer is not None,
            "success": False,
            "latency_ms": None,
            "error": str(error),
        }

    finally:
        if writer is not None:
            writer.close()

            try:
                await writer.wait_closed()
            except Exception:
                pass


async def main():
    global CLIENT_COUNT

    # ------------------------------------------------
    # Read client count from runner
    # ------------------------------------------------

    if len(sys.argv) >= 3:
        CLIENT_COUNT = int(
            sys.argv[2]
        )

    # ------------------------------------------------
    # Dynamic connection setup
    # ------------------------------------------------

    connect_limit = min(
        CLIENT_COUNT,
        MAX_CONNECT_CONCURRENCY,
    )

    connection_waves = math.ceil(
        CLIENT_COUNT / connect_limit
    )

    readiness_timeout = max(
        10,
        (
            connection_waves
            * CONNECT_TIMEOUT
        ) + 5,
    )

    print(
        f"Target clients: "
        f"{CLIENT_COUNT}"
    )

    print(
        f"Connection concurrency: "
        f"{connect_limit}"
    )

    print(
        f"Readiness timeout: "
        f"{readiness_timeout} seconds"
    )

    # ------------------------------------------------
    # Synchronization objects
    # ------------------------------------------------

    connect_semaphore = asyncio.Semaphore(
        connect_limit
    )

    ready_event = asyncio.Event()
    start_event = asyncio.Event()

    counter_lock = asyncio.Lock()

    ready_counter = [0]

    tasks = []

    # ------------------------------------------------
    # Create client tasks
    # ------------------------------------------------

    for client_id in range(
        1,
        CLIENT_COUNT + 1,
    ):
        task = asyncio.create_task(
            run_client(
                client_id,
                connect_semaphore,
                ready_event,
                start_event,
                ready_counter,
                counter_lock,
            )
        )

        tasks.append(
            task
        )

    print()
    print(
        f"Waiting for {CLIENT_COUNT} "
        "clients to connect..."
    )

    # ------------------------------------------------
    # Wait for clients
    # ------------------------------------------------

    try:
        await asyncio.wait_for(
            ready_event.wait(),
            timeout=readiness_timeout,
        )

    except asyncio.TimeoutError:
        print()
        print(
            "Not all clients connected "
            "before the readiness timeout."
        )

    connected_before_burst = (
        ready_counter[0]
    )

    print()
    print(
        f"Connected before burst: "
        f"{connected_before_burst}"
    )

    # ------------------------------------------------
    # IDLE phase
    # ------------------------------------------------

    print(
        f"Holding "
        f"{connected_before_burst} "
        f"connections for "
        f"{IDLE_HOLD_SECONDS} seconds..."
    )

    await asyncio.sleep(
        IDLE_HOLD_SECONDS
    )

    # ------------------------------------------------
    # BURST phase
    # ------------------------------------------------

    print()
    print(
        "Starting synchronized burst..."
    )
    print()

    burst_start = (
        time.perf_counter()
    )

    start_event.set()

    results = await asyncio.gather(
        *tasks,
        return_exceptions=False,
    )

    burst_duration = (
        time.perf_counter()
        - burst_start
    )

    # ------------------------------------------------
    # Calculate results
    # ------------------------------------------------

    successful_connections = sum(
        1
        for result in results
        if result["connected"]
    )

    successful_requests = sum(
        1
        for result in results
        if result["success"]
    )

    latencies = [
        result["latency_ms"]
        for result in results
        if result["latency_ms"]
        is not None
    ]

    connection_success_rate = (
        successful_connections
        / CLIENT_COUNT
        * 100
    )

    request_success_rate = (
        successful_requests
        / CLIENT_COUNT
        * 100
    )

    if burst_duration > 0:
        throughput = (
            successful_requests
            / burst_duration
        )
    else:
        throughput = 0

    if latencies:
        median_latency = (
            statistics.median(
                latencies
            )
        )

        p95_latency = percentile(
            latencies,
            95,
        )

        p99_latency = percentile(
            latencies,
            99,
        )

        min_latency = min(
            latencies
        )

        max_latency = max(
            latencies
        )

    else:
        median_latency = None
        p95_latency = None
        p99_latency = None
        min_latency = None
        max_latency = None

    # ------------------------------------------------
    # Print results
    # ------------------------------------------------

    print(
        "========== RESULTS =========="
    )

    print(
        f"Target clients: "
        f"{CLIENT_COUNT}"
    )

    print(
        f"Successful connections: "
        f"{successful_connections}"
    )

    print(
        f"Connection success rate: "
        f"{connection_success_rate:.2f}%"
    )

    print(
        f"Successful requests: "
        f"{successful_requests}"
    )

    print(
        f"Request success rate: "
        f"{request_success_rate:.2f}%"
    )

    print(
        f"Throughput: "
        f"{throughput:.2f} "
        "responses/sec"
    )

    if latencies:
        print(
            f"Median latency: "
            f"{median_latency:.3f} ms"
        )

        print(
            f"P95 latency: "
            f"{p95_latency:.3f} ms"
        )

        print(
            f"P99 latency: "
            f"{p99_latency:.3f} ms"
        )

        print(
            f"Minimum latency: "
            f"{min_latency:.3f} ms"
        )

        print(
            f"Maximum latency: "
            f"{max_latency:.3f} ms"
        )

    print(
        "============================="
    )

    # ------------------------------------------------
    # Failures
    # ------------------------------------------------

    failed_results = [
        result
        for result in results
        if not result["success"]
    ]

    if failed_results:
        print()
        print(
            f"Failed clients: "
            f"{len(failed_results)}"
        )

        # Avoid flooding terminal at high scale.
        for result in failed_results[:10]:
            print(
                f"Client "
                f"{result['client_id']}: "
                f"{result['error']}"
            )

        if len(failed_results) > 10:
            print(
                "... additional failures "
                "not displayed."
            )

    # ------------------------------------------------
    # Summary JSON
    # ------------------------------------------------

    summary = {
        "target_clients": CLIENT_COUNT,
        "successful_connections": (
            successful_connections
        ),
        "connection_success_rate": (
            connection_success_rate
        ),
        "successful_requests": (
            successful_requests
        ),
        "request_success_rate": (
            request_success_rate
        ),
        "throughput": throughput,
        "median_latency_ms": (
            median_latency
        ),
        "p95_latency_ms": (
            p95_latency
        ),
        "p99_latency_ms": (
            p99_latency
        ),
        "min_latency_ms": (
            min_latency
        ),
        "max_latency_ms": (
            max_latency
        ),
    }

    if len(sys.argv) >= 2:
        output_path = (
            sys.argv[1]
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                summary,
                file,
                indent=4,
            )

        print()
        print(
            f"Summary saved to: "
            f"{output_path}"
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )