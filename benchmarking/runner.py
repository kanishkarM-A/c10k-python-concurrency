import csv
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil


# ============================================================
# CONFIGURATION
# ============================================================

HOST = "127.0.0.1"
PORT = 8080

DEFAULT_SERVER = "asyncio"
DEFAULT_CLIENT_COUNT = 10

STARTUP_TIMEOUT = 5
SHUTDOWN_TIMEOUT = 3
SAMPLE_INTERVAL = 0.5


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SERVERS_DIR = (
    PROJECT_ROOT
    / "servers"
)

GENERATOR_SCRIPT = (
    PROJECT_ROOT
    / "load_testing"
    / "generator.py"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
)

LOGS_DIR = (
    RESULTS_DIR
    / "logs"
)

RESOURCE_DIR = (
    RESULTS_DIR
    / "resources"
)

SUMMARY_DIR = (
    RESULTS_DIR
    / "summaries"
)

TRIALS_CSV = (
    RESULTS_DIR
    / "trials.csv"
)


# ============================================================
# AVAILABLE SERVERS
# ============================================================

SERVER_FILES = {
    "sequential": "sequential.py",
    "threaded": "threaded.py",
    "thread_pool": "thread_pool.py",
    "selector": "selector.py",
    "asyncio": "asyncio_server.py",
}


# ============================================================
# ARGUMENT PARSING
# ============================================================

def parse_arguments():
    """
    Supported commands:

    py -u benchmarking/runner.py

    py -u benchmarking/runner.py 60

    py -u benchmarking/runner.py threaded 10

    py -u benchmarking/runner.py selector 50
    """

    server_name = DEFAULT_SERVER
    client_count = DEFAULT_CLIENT_COUNT

    # No arguments:
    #
    # runner.py
    if len(sys.argv) == 1:
        return server_name, client_count

    # One argument:
    #
    # runner.py 60
    #
    # OR
    #
    # runner.py threaded
    if len(sys.argv) == 2:

        argument = sys.argv[1]

        if argument.isdigit():
            client_count = int(argument)

        else:
            server_name = argument.lower()

    # Two arguments:
    #
    # runner.py threaded 10
    elif len(sys.argv) == 3:

        server_name = (
            sys.argv[1].lower()
        )

        try:
            client_count = int(
                sys.argv[2]
            )

        except ValueError:
            print(
                "ERROR: client count must "
                "be a positive integer."
            )
            return None, None

    else:
        print(
            "Usage:"
        )

        print(
            "py -u benchmarking/runner.py "
            "[server] [client_count]"
        )

        return None, None

    # Validate server name.
    if server_name not in SERVER_FILES:

        print(
            f"ERROR: unknown server "
            f"'{server_name}'."
        )

        print()
        print(
            "Available servers:"
        )

        for name in SERVER_FILES:
            print(
                f"  {name}"
            )

        return None, None

    # Validate client count.
    if client_count <= 0:

        print(
            "ERROR: client count must "
            "be a positive integer."
        )

        return None, None

    return (
        server_name,
        client_count,
    )


# ============================================================
# HELPERS
# ============================================================

def bytes_to_mib(value):
    return value / (1024 * 1024)


def port_is_available():
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:

        result = sock.connect_ex(
            (HOST, PORT)
        )

        return result != 0


def wait_for_server(process):
    deadline = (
        time.perf_counter()
        + STARTUP_TIMEOUT
    )

    while time.perf_counter() < deadline:

        if process.poll() is not None:
            raise RuntimeError(
                "Server process exited "
                "before becoming ready."
            )

        try:
            with socket.create_connection(
                (HOST, PORT),
                timeout=0.25,
            ):
                return

        except OSError:
            time.sleep(0.1)

    raise TimeoutError(
        "Server did not become ready "
        f"within {STARTUP_TIMEOUT} seconds."
    )


def stop_server(process):
    if process.poll() is not None:
        return

    print()
    print(
        "Stopping server..."
    )

    process.terminate()

    try:
        process.wait(
            timeout=SHUTDOWN_TIMEOUT
        )

    except subprocess.TimeoutExpired:

        print(
            "Server did not stop normally."
        )

        print(
            "Force killing server..."
        )

        process.kill()
        process.wait()


# ============================================================
# RESOURCE MONITOR
# ============================================================

def monitor_server(
    pid,
    csv_path,
    stop_event,
):
    try:
        process = psutil.Process(
            pid
        )

    except psutil.NoSuchProcess:
        print(
            "[MONITOR] Server process "
            "does not exist."
        )
        return

    process.cpu_percent(
        interval=None
    )

    start_time = (
        time.perf_counter()
    )

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(
            csv_file
        )

        writer.writerow([
            "elapsed_seconds",
            "cpu_percent",
            "rss_mib",
            "vms_mib",
            "threads",
            "handles",
        ])

        while not stop_event.is_set():

            try:
                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                memory = (
                    process.memory_info()
                )

                cpu = (
                    process.cpu_percent(
                        interval=None
                    )
                )

                rss = bytes_to_mib(
                    memory.rss
                )

                vms = bytes_to_mib(
                    memory.vms
                )

                threads = (
                    process.num_threads()
                )

                try:
                    handles = (
                        process.num_handles()
                    )

                except (
                    AttributeError,
                    psutil.Error,
                ):
                    handles = ""

                writer.writerow([
                    f"{elapsed:.3f}",
                    f"{cpu:.2f}",
                    f"{rss:.3f}",
                    f"{vms:.3f}",
                    threads,
                    handles,
                ])

                csv_file.flush()

                print(
                    f"[MONITOR] "
                    f"CPU={cpu:6.2f}% | "
                    f"RSS={rss:7.2f} MiB | "
                    f"VMS={vms:7.2f} MiB | "
                    f"Threads={threads:3d} | "
                    f"Handles={handles}"
                )

                stop_event.wait(
                    SAMPLE_INTERVAL
                )

            except psutil.NoSuchProcess:
                break

            except psutil.Error as error:
                print(
                    f"[MONITOR ERROR] "
                    f"{error}"
                )
                break


# ============================================================
# RESOURCE ANALYSIS
# ============================================================

def read_resource_peaks(
    resource_path
):
    peak_cpu = 0.0
    peak_rss = 0.0
    peak_vms = 0.0
    peak_threads = 0
    peak_handles = 0

    with open(
        resource_path,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            peak_cpu = max(
                peak_cpu,
                float(
                    row["cpu_percent"]
                ),
            )

            peak_rss = max(
                peak_rss,
                float(
                    row["rss_mib"]
                ),
            )

            peak_vms = max(
                peak_vms,
                float(
                    row["vms_mib"]
                ),
            )

            peak_threads = max(
                peak_threads,
                int(
                    row["threads"]
                ),
            )

            if row["handles"]:

                peak_handles = max(
                    peak_handles,
                    int(
                        row["handles"]
                    ),
                )

    return {
        "peak_cpu_percent": peak_cpu,
        "peak_rss_mib": peak_rss,
        "peak_vms_mib": peak_vms,
        "peak_threads": peak_threads,
        "peak_handles": peak_handles,
    }


# ============================================================
# MASTER trials.csv
# ============================================================

def append_trial(
    timestamp,
    server_name,
    summary_path,
    resource_path,
):
    with open(
        summary_path,
        "r",
        encoding="utf-8",
    ) as file:

        summary = json.load(
            file
        )

    resources = read_resource_peaks(
        resource_path
    )

    row = {
        "timestamp": timestamp,

        "server": server_name,

        "target_clients": summary[
            "target_clients"
        ],

        "successful_connections": summary[
            "successful_connections"
        ],

        "connection_success_rate": summary[
            "connection_success_rate"
        ],

        "successful_requests": summary[
            "successful_requests"
        ],

        "request_success_rate": summary[
            "request_success_rate"
        ],

        "throughput_rps": summary[
            "throughput"
        ],

        "median_latency_ms": summary[
            "median_latency_ms"
        ],

        "p95_latency_ms": summary[
            "p95_latency_ms"
        ],

        "p99_latency_ms": summary[
            "p99_latency_ms"
        ],

        "min_latency_ms": summary[
            "min_latency_ms"
        ],

        "max_latency_ms": summary[
            "max_latency_ms"
        ],

        "peak_cpu_percent": resources[
            "peak_cpu_percent"
        ],

        "peak_rss_mib": resources[
            "peak_rss_mib"
        ],

        "peak_vms_mib": resources[
            "peak_vms_mib"
        ],

        "peak_threads": resources[
            "peak_threads"
        ],

        "peak_handles": resources[
            "peak_handles"
        ],
    }

    fieldnames = list(
        row.keys()
    )

    file_exists = (
        TRIALS_CSV.exists()
        and TRIALS_CSV.stat().st_size > 0
    )

    with open(
        TRIALS_CSV,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            row
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "========== C10K BENCHMARK RUNNER =========="
    )

    server_name, client_count = (
        parse_arguments()
    )

    if server_name is None:
        return

    server_script = (
        SERVERS_DIR
        / SERVER_FILES[
            server_name
        ]
    )

    print()
    print(
        f"Server: {server_name}"
    )

    print(
        f"Client count: "
        f"{client_count}"
    )

    # --------------------------------------------------------
    # Check server file exists
    # --------------------------------------------------------

    if not server_script.exists():

        print()
        print(
            "ERROR: server file "
            "does not exist:"
        )

        print(
            server_script
        )

        return

    # --------------------------------------------------------
    # Create result directories
    # --------------------------------------------------------

    LOGS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SUMMARY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Check port
    # --------------------------------------------------------

    if not port_is_available():

        print()
        print(
            f"ERROR: {HOST}:{PORT} "
            "is already in use."
        )

        print(
            "Stop the old server first."
        )

        return

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    timestamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    # --------------------------------------------------------
    # Output paths
    # --------------------------------------------------------

    log_path = (
        LOGS_DIR
        / (
            f"{server_name}_"
            f"{timestamp}.log"
        )
    )

    resource_path = (
        RESOURCE_DIR
        / (
            f"{server_name}_"
            f"{timestamp}"
            "_resources.csv"
        )
    )

    summary_path = (
        SUMMARY_DIR
        / (
            f"{server_name}_"
            f"{timestamp}"
            "_summary.json"
        )
    )

    server_process = None

    monitor_thread = None

    monitor_stop_event = None

    generator_successful = False

    try:

        # ----------------------------------------------------
        # Start server
        # ----------------------------------------------------

        print()
        print(
            f"Starting "
            f"{server_name} server..."
        )

        print(
            f"Server script: "
            f"{server_script}"
        )

        print(
            f"Server log: "
            f"{log_path}"
        )

        with open(
            log_path,
            "w",
            encoding="utf-8",
        ) as log_file:

            server_process = (
                subprocess.Popen(
                    [
                        sys.executable,
                        "-u",
                        str(
                            server_script
                        ),
                    ],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=PROJECT_ROOT,
                )
            )

            print()
            print(
                f"Server PID: "
                f"{server_process.pid}"
            )

            print(
                "Waiting for server "
                "readiness..."
            )

            wait_for_server(
                server_process
            )

            print(
                "Server is READY."
            )

            # ------------------------------------------------
            # Start monitor
            # ------------------------------------------------

            monitor_stop_event = (
                threading.Event()
            )

            monitor_thread = (
                threading.Thread(
                    target=monitor_server,
                    args=(
                        server_process.pid,
                        resource_path,
                        monitor_stop_event,
                    ),
                )
            )

            monitor_thread.start()

            # Baseline measurement period.
            time.sleep(
                1
            )

            # ------------------------------------------------
            # Run load generator
            # ------------------------------------------------

            print()
            print(
                "Starting load generator..."
            )

            print(
                "----------------------------------"
            )

            generator_result = (
                subprocess.run(
                    [
                        sys.executable,
                        "-u",
                        str(
                            GENERATOR_SCRIPT
                        ),
                        str(
                            summary_path
                        ),
                        str(
                            client_count
                        ),
                    ],
                    cwd=PROJECT_ROOT,
                )
            )

            print(
                "----------------------------------"
            )

            if (
                generator_result.returncode
                == 0
            ):

                generator_successful = True

                print()
                print(
                    "Generator finished "
                    "successfully."
                )

            else:

                print()
                print(
                    "Generator exited with "
                    f"code "
                    f"{generator_result.returncode}"
                )

    except Exception as error:

        print()
        print(
            "RUNNER ERROR:"
        )

        print(
            error
        )

    finally:

        # ----------------------------------------------------
        # Stop monitor
        # ----------------------------------------------------

        if monitor_stop_event is not None:
            monitor_stop_event.set()

        if monitor_thread is not None:
            monitor_thread.join()

        # ----------------------------------------------------
        # Stop server
        # ----------------------------------------------------

        if server_process is not None:

            stop_server(
                server_process
            )

    # --------------------------------------------------------
    # Save master trial
    # --------------------------------------------------------

    if (
        generator_successful
        and summary_path.exists()
        and resource_path.exists()
    ):

        try:

            append_trial(
                timestamp,
                server_name,
                summary_path,
                resource_path,
            )

            print()
            print(
                "Trial appended to:"
            )

            print(
                TRIALS_CSV
            )

        except Exception as error:

            print()
            print(
                "Could not append trial:"
            )

            print(
                error
            )

    else:

        print()
        print(
            "Trial was not added to "
            "trials.csv because the "
            "benchmark did not complete "
            "successfully."
        )

    # --------------------------------------------------------
    # Final paths
    # --------------------------------------------------------

    print()
    print(
        "Server log saved to:"
    )

    print(
        log_path
    )

    print()
    print(
        "Resource CSV saved to:"
    )

    print(
        resource_path
    )

    if summary_path.exists():

        print()
        print(
            "Summary JSON saved to:"
        )

        print(
            summary_path
        )

    print()
    print(
        "Benchmark run finished."
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()