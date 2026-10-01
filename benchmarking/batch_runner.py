import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

SERVERS = [
    "sequential",
    "threaded",
    "thread_pool",
    "selector",
    "asyncio",
]

CLIENT_COUNTS = [
    10,
    50,
    100,
]

DEFAULT_REPEATS = 1

COOLDOWN_SECONDS = 1


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUNNER_SCRIPT = (
    PROJECT_ROOT
    / "benchmarking"
    / "runner.py"
)


# ============================================================
# MAIN
# ============================================================

def main():
    repeats = DEFAULT_REPEATS

    # Optional:
    #
    # py -u benchmarking/batch_runner.py 3
    #
    # means repeat every test 3 times.

    if len(sys.argv) >= 2:
        try:
            repeats = int(sys.argv[1])

            if repeats <= 0:
                raise ValueError

        except ValueError:
            print(
                "ERROR: repeats must be "
                "a positive integer."
            )
            return

    total_tests = (
        len(SERVERS)
        * len(CLIENT_COUNTS)
        * repeats
    )

    completed = 0
    failed = 0

    print(
        "========== C10K BATCH BENCHMARK =========="
    )

    print(
        f"Architectures: {len(SERVERS)}"
    )

    print(
        f"Client levels: {CLIENT_COUNTS}"
    )

    print(
        f"Repeats per test: {repeats}"
    )

    print(
        f"Total benchmark runs: {total_tests}"
    )

    print()

    # --------------------------------------------------------
    # Execute all benchmark combinations
    # --------------------------------------------------------

    for repeat_number in range(
        1,
        repeats + 1,
    ):
        print()
        print(
            "=========================================="
        )

        print(
            f"REPEAT {repeat_number} "
            f"OF {repeats}"
        )

        print(
            "=========================================="
        )

        for server_name in SERVERS:

            for client_count in CLIENT_COUNTS:

                print()
                print(
                    "##########################################"
                )

                print(
                    f"RUNNING: "
                    f"{server_name} "
                    f"with {client_count} clients"
                )

                print(
                    f"Progress: "
                    f"{completed + failed + 1}"
                    f"/{total_tests}"
                )

                print(
                    "##########################################"
                )

                command = [
                    sys.executable,
                    "-u",
                    str(RUNNER_SCRIPT),
                    server_name,
                    str(client_count),
                ]

                result = subprocess.run(
                    command,
                    cwd=PROJECT_ROOT,
                )

                if result.returncode == 0:

                    completed += 1

                    print()
                    print(
                        "Batch test completed."
                    )

                else:

                    failed += 1

                    print()
                    print(
                        "Batch test FAILED."
                    )

                    print(
                        f"Exit code: "
                        f"{result.returncode}"
                    )

                # Give Windows a moment to release
                # sockets/resources before next run.
                print()
                print(
                    f"Cooling down for "
                    f"{COOLDOWN_SECONDS} second..."
                )

                time.sleep(
                    COOLDOWN_SECONDS
                )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print(
        "========== BATCH COMPLETE =========="
    )

    print(
        f"Successful runs: {completed}"
    )

    print(
        f"Failed runs: {failed}"
    )

    print(
        f"Total runs: "
        f"{completed + failed}"
    )

    print()

    print(
        "All successful results were "
        "appended to:"
    )

    print(
        PROJECT_ROOT
        / "results"
        / "trials.csv"
    )

    print(
        "===================================="
    )


if __name__ == "__main__":
    main()