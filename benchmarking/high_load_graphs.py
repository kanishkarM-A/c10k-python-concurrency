import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

CLIENT_COUNTS = [
    100,
    250,
    500,
    1000,
    2000,
    5000,
    10000,
]

LATEST_TRIALS_PER_LEVEL = 3


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
)

TRIALS_CSV = (
    RESULTS_DIR
    / "trials.csv"
)

OUTPUT_CSV = (
    RESULTS_DIR
    / "asyncio_scaling_medians.csv"
)

GRAPHS_DIR = (
    RESULTS_DIR
    / "graphs"
    / "asyncio_scaling"
)


# ============================================================
# HELPERS
# ============================================================

def to_float(value):
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    try:
        return float(value)

    except ValueError:
        return None


def median_value(rows, column):
    values = []

    for row in rows:
        value = to_float(
            row.get(column)
        )

        if value is not None:
            values.append(value)

    if not values:
        return None

    return statistics.median(
        values
    )


# ============================================================
# LOAD ASYNCIO TRIALS
# ============================================================

def load_asyncio_trials():
    if not TRIALS_CSV.exists():
        raise FileNotFoundError(
            f"Could not find {TRIALS_CSV}"
        )

    groups = defaultdict(list)

    with open(
        TRIALS_CSV,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            if row.get("server") != "asyncio":
                continue

            try:
                clients = int(
                    row["target_clients"]
                )

            except (
                ValueError,
                TypeError,
                KeyError,
            ):
                continue

            if clients not in CLIENT_COUNTS:
                continue

            groups[clients].append(
                row
            )

    # Sort each group by timestamp.
    for clients in groups:
        groups[clients].sort(
            key=lambda row: row[
                "timestamp"
            ]
        )

    return groups


# ============================================================
# CREATE MEDIAN SUMMARY
# ============================================================

def calculate_summary(groups):
    summary_rows = []

    for clients in CLIENT_COUNTS:

        rows = groups.get(
            clients,
            [],
        )

        if not rows:
            continue

        selected_rows = (
            rows[
                -LATEST_TRIALS_PER_LEVEL:
            ]
        )

        summary_rows.append({
            "target_clients": clients,

            "trials_available": len(
                rows
            ),

            "trials_used": len(
                selected_rows
            ),

            "connection_success_rate": (
                median_value(
                    selected_rows,
                    "connection_success_rate",
                )
            ),

            "request_success_rate": (
                median_value(
                    selected_rows,
                    "request_success_rate",
                )
            ),

            "throughput_rps": (
                median_value(
                    selected_rows,
                    "throughput_rps",
                )
            ),

            "median_latency_ms": (
                median_value(
                    selected_rows,
                    "median_latency_ms",
                )
            ),

            "p95_latency_ms": (
                median_value(
                    selected_rows,
                    "p95_latency_ms",
                )
            ),

            "p99_latency_ms": (
                median_value(
                    selected_rows,
                    "p99_latency_ms",
                )
            ),

            "peak_cpu_percent": (
                median_value(
                    selected_rows,
                    "peak_cpu_percent",
                )
            ),

            "peak_rss_mib": (
                median_value(
                    selected_rows,
                    "peak_rss_mib",
                )
            ),

            "peak_threads": (
                median_value(
                    selected_rows,
                    "peak_threads",
                )
            ),

            "peak_handles": (
                median_value(
                    selected_rows,
                    "peak_handles",
                )
            ),
        })

    return summary_rows


# ============================================================
# SAVE SUMMARY CSV
# ============================================================

def save_summary(rows):
    if not rows:
        return

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys(),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# GRAPH HELPER
# ============================================================

def make_graph(
    rows,
    column,
    ylabel,
    title,
    filename,
):
    clients = [
        row["target_clients"]
        for row in rows
    ]

    values = [
        row[column]
        for row in rows
    ]

    plt.figure(
        figsize=(10, 6)
    )

    plt.plot(
        clients,
        values,
        marker="o",
        linewidth=2,
    )

    # Log scale makes 100 -> 10000 easier to read.
    plt.xscale(
        "log"
    )

    plt.xticks(
        CLIENT_COUNTS,
        [
            "100",
            "250",
            "500",
            "1K",
            "2K",
            "5K",
            "10K",
        ],
    )

    plt.xlabel(
        "Concurrent Clients"
    )

    plt.ylabel(
        ylabel
    )

    plt.title(
        title
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.tight_layout()

    output_path = (
        GRAPHS_DIR
        / filename
    )

    plt.savefig(
        output_path,
        dpi=200,
    )

    plt.close()

    print(
        f"Saved: {output_path}"
    )


# ============================================================
# PRINT TABLE
# ============================================================

def print_summary(rows):
    print()
    print(
        "========== ASYNCIO SCALING SUMMARY =========="
    )

    print(
        f"{'Clients':>8}"
        f"{'Conn %':>10}"
        f"{'Req %':>10}"
        f"{'RPS':>12}"
        f"{'Median ms':>12}"
        f"{'P95 ms':>12}"
        f"{'RSS MiB':>12}"
        f"{'Threads':>10}"
        f"{'Handles':>10}"
    )

    print(
        "-" * 96
    )

    for row in rows:

        print(
            f"{row['target_clients']:>8}"
            f"{row['connection_success_rate']:>10.2f}"
            f"{row['request_success_rate']:>10.2f}"
            f"{row['throughput_rps']:>12.2f}"
            f"{row['median_latency_ms']:>12.2f}"
            f"{row['p95_latency_ms']:>12.2f}"
            f"{row['peak_rss_mib']:>12.2f}"
            f"{row['peak_threads']:>10.0f}"
            f"{row['peak_handles']:>10.0f}"
        )

    print(
        "=" * 96
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "========== ASYNCIO HIGH-LOAD ANALYSIS =========="
    )

    GRAPHS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        groups = load_asyncio_trials()

        rows = calculate_summary(
            groups
        )

    except Exception as error:

        print()
        print(
            "ANALYSIS ERROR:"
        )

        print(
            error
        )

        return

    if not rows:
        print(
            "No asyncio scaling data found."
        )
        return

    save_summary(
        rows
    )

    print_summary(
        rows
    )

    # --------------------------------------------------------
    # SUCCESS RATE
    # --------------------------------------------------------

    make_graph(
        rows,
        column="request_success_rate",
        ylabel="Request Success Rate (%)",
        title=(
            "Asyncio Request Success Rate "
            "vs Concurrent Clients"
        ),
        filename="success_rate.png",
    )

    # --------------------------------------------------------
    # CONNECTION SUCCESS
    # --------------------------------------------------------

    make_graph(
        rows,
        column="connection_success_rate",
        ylabel="Connection Success Rate (%)",
        title=(
            "Asyncio Connection Success Rate "
            "vs Concurrent Clients"
        ),
        filename="connection_success.png",
    )

    # --------------------------------------------------------
    # THROUGHPUT
    # --------------------------------------------------------

    make_graph(
        rows,
        column="throughput_rps",
        ylabel="Responses per Second",
        title=(
            "Asyncio Throughput "
            "vs Concurrent Clients"
        ),
        filename="throughput.png",
    )

    # --------------------------------------------------------
    # MEDIAN LATENCY
    # --------------------------------------------------------

    make_graph(
        rows,
        column="median_latency_ms",
        ylabel="Median Latency (ms)",
        title=(
            "Asyncio Median Latency "
            "vs Concurrent Clients"
        ),
        filename="median_latency.png",
    )

    # --------------------------------------------------------
    # P95 LATENCY
    # --------------------------------------------------------

    make_graph(
        rows,
        column="p95_latency_ms",
        ylabel="P95 Latency (ms)",
        title=(
            "Asyncio P95 Latency "
            "vs Concurrent Clients"
        ),
        filename="p95_latency.png",
    )

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    make_graph(
        rows,
        column="peak_rss_mib",
        ylabel="Peak RSS Memory (MiB)",
        title=(
            "Asyncio Memory Usage "
            "vs Concurrent Clients"
        ),
        filename="memory_rss.png",
    )

    # --------------------------------------------------------
    # HANDLES
    # --------------------------------------------------------

    make_graph(
        rows,
        column="peak_handles",
        ylabel="Peak Handle Count",
        title=(
            "Asyncio Handles "
            "vs Concurrent Clients"
        ),
        filename="handles.png",
    )

    # --------------------------------------------------------
    # THREADS
    # --------------------------------------------------------

    make_graph(
        rows,
        column="peak_threads",
        ylabel="Peak Thread Count",
        title=(
            "Asyncio Threads "
            "vs Concurrent Clients"
        ),
        filename="threads.png",
    )

    print()
    print(
        "Scaling data saved to:"
    )

    print(
        OUTPUT_CSV
    )

    print()
    print(
        "All high-load graphs saved to:"
    )

    print(
        GRAPHS_DIR
    )

    print()
    print(
        "High-load analysis complete."
    )

    print(
        "==============================================="
    )


if __name__ == "__main__":
    main()