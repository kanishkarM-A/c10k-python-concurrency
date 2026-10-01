import sys
import time

import psutil


SAMPLE_INTERVAL = 0.5


def bytes_to_mib(value):
    return value / (1024 * 1024)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: py -u benchmarking/monitor.py <PID>"
        )
        return

    pid = int(sys.argv[1])

    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"No process exists with PID {pid}")
        return

    print(f"Monitoring PID: {pid}")
    print(f"Process name: {process.name()}")
    print()

    # Initialize CPU measurement.
    process.cpu_percent(interval=None)

    previous_context_switches = None
    previous_time = None

    while True:
        try:
            now = time.perf_counter()

            memory = process.memory_info()

            rss_mib = bytes_to_mib(
                memory.rss
            )

            vms_mib = bytes_to_mib(
                memory.vms
            )

            thread_count = (
                process.num_threads()
            )

            cpu_percent = (
                process.cpu_percent(
                    interval=None
                )
            )

            # Windows has handles instead of Unix-style
            # file descriptor counting through psutil.
            try:
                handles = process.num_handles()
            except (
                AttributeError,
                psutil.Error,
            ):
                handles = None

            try:
                context_switches = (
                    process.num_ctx_switches()
                )

                total_context_switches = (
                    context_switches.voluntary
                    + context_switches.involuntary
                )

            except psutil.Error:
                total_context_switches = None

            context_switch_rate = None

            if (
                total_context_switches is not None
                and previous_context_switches
                is not None
                and previous_time is not None
            ):
                elapsed = (
                    now - previous_time
                )

                if elapsed > 0:
                    context_switch_rate = (
                        total_context_switches
                        - previous_context_switches
                    ) / elapsed

            print(
                f"CPU: {cpu_percent:6.2f}% | "
                f"RSS: {rss_mib:8.2f} MiB | "
                f"VMS: {vms_mib:8.2f} MiB | "
                f"Threads: {thread_count:4d}",
                end="",
            )

            if handles is not None:
                print(
                    f" | Handles: {handles:5d}",
                    end="",
                )

            if context_switch_rate is not None:
                print(
                    f" | Context switches/s: "
                    f"{context_switch_rate:8.2f}",
                    end="",
                )

            print()

            previous_context_switches = (
                total_context_switches
            )

            previous_time = now

            time.sleep(
                SAMPLE_INTERVAL
            )

        except psutil.NoSuchProcess:
            print()
            print(
                "Server process ended."
            )
            break

        except KeyboardInterrupt:
            print()
            print(
                "Monitor stopped."
            )
            break


if __name__ == "__main__":
    main()