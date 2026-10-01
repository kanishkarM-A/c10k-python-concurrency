import csv
from pathlib import Path

import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
)

INPUT_CSV = (
    RESULTS_DIR
    / "comparison_medians.csv"
)

GRAPHS_DIR = (
    RESULTS_DIR
    / "graphs"
)


# ============================================================
# CONFIGURATION
# ============================================================

SERVER_ORDER = [
    "sequential",
    "threaded",
    "thread_pool",
    "selector",
    "asyncio",
]


SERVER_LABELS = {
    "sequential": "Sequential",
    "threaded": "Thread-per-Connection",
    "thread_pool": "Thread Pool",
    "selector": "Selector",
    "asyncio": "Asyncio",
}


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_CSV}"
        )

    rows = []

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            rows.append({
                "server": row["server"],
                "clients": int(
                    row["target_clients"]
                ),
                "success_rate": float(
                    row["request_success_rate"]
                ),
                "throughput": float(
                    row["throughput_rps"]
                ),
                "median_latency": float(
                    row["median_latency_ms"]
                ),
                "p95_latency": float(
                    row["p95_latency_ms"]
                ),
                "rss": float(
                    row["peak_rss_mib"]
                ),
                "threads": float(
                    row["peak_threads"]
                ),
                "handles": float(
                    row["peak_handles"]
                ),
            })

    return rows


def rows_for_server(
    rows,
    server_name,
):
    selected = [
        row
        for row in rows
        if row["server"] == server_name
    ]

    selected.sort(
        key=lambda row: row["clients"]
    )

    return selected


# ============================================================
# GENERIC LINE GRAPH
# ============================================================

def create_line_graph(
    rows,
    metric,
    ylabel,
    title,
    filename,
):
    plt.figure(
        figsize=(10, 6)
    )

    for server_name in SERVER_ORDER:

        server_rows = rows_for_server(
            rows,
            server_name,
        )

        if not server_rows:
            continue

        clients = [
            row["clients"]
            for row in server_rows
        ]

        values = [
            row[metric]
            for row in server_rows
        ]

        plt.plot(
            clients,
            values,
            marker="o",
            label=SERVER_LABELS[
                server_name
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

    plt.xticks(
        [10, 50, 100]
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.legend()

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
# MAIN
# ============================================================

def main():
    print(
        "========== C10K GRAPH GENERATOR =========="
    )

    GRAPHS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        rows = load_data()

    except Exception as error:

        print()
        print(
            "GRAPH ERROR:"
        )

        print(
            error
        )

        return

    # --------------------------------------------------------
    # Median latency
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="median_latency",
        ylabel="Median Latency (ms)",
        title=(
            "Median Latency vs Concurrent Clients"
        ),
        filename="median_latency.png",
    )

    # --------------------------------------------------------
    # P95 latency
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="p95_latency",
        ylabel="P95 Latency (ms)",
        title=(
            "P95 Latency vs Concurrent Clients"
        ),
        filename="p95_latency.png",
    )

    # --------------------------------------------------------
    # Throughput
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="throughput",
        ylabel="Responses per Second",
        title=(
            "Throughput vs Concurrent Clients"
        ),
        filename="throughput.png",
    )

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="rss",
        ylabel="Peak RSS Memory (MiB)",
        title=(
            "Memory Usage vs Concurrent Clients"
        ),
        filename="memory_rss.png",
    )

    # --------------------------------------------------------
    # Threads
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="threads",
        ylabel="Peak Thread Count",
        title=(
            "Thread Count vs Concurrent Clients"
        ),
        filename="threads.png",
    )

    # --------------------------------------------------------
    # Handles
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="handles",
        ylabel="Peak Handle Count",
        title=(
            "Handle Count vs Concurrent Clients"
        ),
        filename="handles.png",
    )

    # --------------------------------------------------------
    # Success rate
    # --------------------------------------------------------

    create_line_graph(
        rows,
        metric="success_rate",
        ylabel="Request Success Rate (%)",
        title=(
            "Request Success Rate vs Concurrent Clients"
        ),
        filename="success_rate.png",
    )

    print()
    print(
        "All graphs saved to:"
    )

    print(
        GRAPHS_DIR
    )

    print()
    print(
        "Graph generation complete."
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()