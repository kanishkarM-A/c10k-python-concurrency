import csv
import statistics
from collections import defaultdict
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

# These are the loads used for the fair
# five-architecture comparison.
CLIENT_COUNTS = [
    10,
    50,
    100,
]

SERVERS = [
    "sequential",
    "threaded",
    "thread_pool",
    "selector",
    "asyncio",
]

# Use only the latest 3 trials for each
# server/client-count combination.
#
# This prevents very old development tests
# from affecting the final comparison.
LATEST_TRIALS_PER_GROUP = 3


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
    / "comparison_medians.csv"
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


def median_of(rows, column):
    values = []

    for row in rows:
        value = to_float(
            row.get(column)
        )

        if value is not None:
            values.append(
                value
            )

    if not values:
        return None

    return statistics.median(
        values
    )


def format_number(
    value,
    decimal_places=2,
):
    if value is None:
        return "N/A"

    return (
        f"{value:.{decimal_places}f}"
    )


# ============================================================
# LOAD TRIAL DATA
# ============================================================

def load_trials():
    if not TRIALS_CSV.exists():
        raise FileNotFoundError(
            f"Could not find {TRIALS_CSV}"
        )

    rows = []

    with open(
        TRIALS_CSV,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            try:
                client_count = int(
                    row["target_clients"]
                )

            except (
                ValueError,
                TypeError,
                KeyError,
            ):
                continue

            server_name = (
                row.get(
                    "server",
                    "",
                )
                .strip()
            )

            # Ignore experimental loads such as
            # 25, 60 and 75 for this particular
            # architecture comparison.
            if client_count not in CLIENT_COUNTS:
                continue

            if server_name not in SERVERS:
                continue

            row["_client_count"] = (
                client_count
            )

            rows.append(
                row
            )

    return rows


# ============================================================
# GROUP TRIALS
# ============================================================

def group_trials(rows):
    groups = defaultdict(
        list
    )

    for row in rows:
        key = (
            row["server"],
            row["_client_count"],
        )

        groups[key].append(
            row
        )

    # Sort by timestamp so we can use
    # the newest trials.
    for key in groups:
        groups[key].sort(
            key=lambda row: row[
                "timestamp"
            ]
        )

    return groups


# ============================================================
# CALCULATE MEDIANS
# ============================================================

def calculate_summary(groups):
    summary_rows = []

    for server_name in SERVERS:

        for client_count in CLIENT_COUNTS:

            key = (
                server_name,
                client_count,
            )

            all_rows = groups.get(
                key,
                [],
            )

            if not all_rows:
                continue

            selected_rows = (
                all_rows[
                    -LATEST_TRIALS_PER_GROUP:
                ]
            )

            summary = {
                "server": server_name,

                "target_clients": (
                    client_count
                ),

                "trials_available": (
                    len(all_rows)
                ),

                "trials_used": (
                    len(selected_rows)
                ),

                "connection_success_rate": (
                    median_of(
                        selected_rows,
                        "connection_success_rate",
                    )
                ),

                "request_success_rate": (
                    median_of(
                        selected_rows,
                        "request_success_rate",
                    )
                ),

                "throughput_rps": (
                    median_of(
                        selected_rows,
                        "throughput_rps",
                    )
                ),

                "median_latency_ms": (
                    median_of(
                        selected_rows,
                        "median_latency_ms",
                    )
                ),

                "p95_latency_ms": (
                    median_of(
                        selected_rows,
                        "p95_latency_ms",
                    )
                ),

                "p99_latency_ms": (
                    median_of(
                        selected_rows,
                        "p99_latency_ms",
                    )
                ),

                "peak_cpu_percent": (
                    median_of(
                        selected_rows,
                        "peak_cpu_percent",
                    )
                ),

                "peak_rss_mib": (
                    median_of(
                        selected_rows,
                        "peak_rss_mib",
                    )
                ),

                "peak_vms_mib": (
                    median_of(
                        selected_rows,
                        "peak_vms_mib",
                    )
                ),

                "peak_threads": (
                    median_of(
                        selected_rows,
                        "peak_threads",
                    )
                ),

                "peak_handles": (
                    median_of(
                        selected_rows,
                        "peak_handles",
                    )
                ),
            }

            summary_rows.append(
                summary
            )

    return summary_rows


# ============================================================
# SAVE SUMMARY CSV
# ============================================================

def save_summary(summary_rows):
    if not summary_rows:
        return

    fieldnames = list(
        summary_rows[0].keys()
    )

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            summary_rows
        )


# ============================================================
# PRINT COMPARISON TABLE
# ============================================================

def print_table(summary_rows):
    print()
    print(
        "================ C10K COMPARISON ================"
    )

    print(
        f"{'Server':<13}"
        f"{'Clients':>8}"
        f"{'Trials':>8}"
        f"{'Success':>10}"
        f"{'Throughput':>14}"
        f"{'Median ms':>12}"
        f"{'P95 ms':>10}"
        f"{'Threads':>10}"
        f"{'RSS MiB':>10}"
        f"{'Handles':>10}"
    )

    print(
        "-" * 105
    )

    for row in summary_rows:

        success = format_number(
            row[
                "request_success_rate"
            ]
        )

        throughput = format_number(
            row[
                "throughput_rps"
            ]
        )

        latency = format_number(
            row[
                "median_latency_ms"
            ]
        )

        p95 = format_number(
            row[
                "p95_latency_ms"
            ]
        )

        threads = format_number(
            row[
                "peak_threads"
            ],
            0,
        )

        rss = format_number(
            row[
                "peak_rss_mib"
            ]
        )

        handles = format_number(
            row[
                "peak_handles"
            ],
            0,
        )

        print(
            f"{row['server']:<13}"
            f"{row['target_clients']:>8}"
            f"{row['trials_used']:>8}"
            f"{success + '%':>10}"
            f"{throughput:>14}"
            f"{latency:>12}"
            f"{p95:>10}"
            f"{threads:>10}"
            f"{rss:>10}"
            f"{handles:>10}"
        )

    print(
        "=" * 105
    )


# ============================================================
# CHECK COVERAGE
# ============================================================

def print_trial_coverage(groups):
    print()
    print(
        "Trial coverage:"
    )

    for server_name in SERVERS:

        for client_count in CLIENT_COUNTS:

            rows = groups.get(
                (
                    server_name,
                    client_count,
                ),
                [],
            )

            count = len(
                rows
            )

            status = (
                "OK"
                if count >= 3
                else "NEEDS MORE"
            )

            print(
                f"{server_name:<13} "
                f"{client_count:>3} clients: "
                f"{count} trials "
                f"[{status}]"
            )


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "========== C10K RESULT ANALYZER =========="
    )

    print()
    print(
        f"Reading:"
    )

    print(
        TRIALS_CSV
    )

    try:
        rows = load_trials()

    except Exception as error:
        print()
        print(
            "ANALYSIS ERROR:"
        )

        print(
            error
        )

        return

    groups = group_trials(
        rows
    )

    print_trial_coverage(
        groups
    )

    summary_rows = calculate_summary(
        groups
    )

    if not summary_rows:
        print()
        print(
            "No benchmark data found."
        )
        return

    save_summary(
        summary_rows
    )

    print_table(
        summary_rows
    )

    print()
    print(
        "Median comparison saved to:"
    )

    print(
        OUTPUT_CSV
    )

    print()
    print(
        "Analysis complete."
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()