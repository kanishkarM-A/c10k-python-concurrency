import socket
import threading
import time

HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
EXPECTED_RESPONSE = b"PONG\n"

HOLDER_COUNT = 3
EXTRA_CLIENT_COUNT = 2

release_holders = threading.Event()

# Main thread + 3 holder clients
holders_ready = threading.Barrier(HOLDER_COUNT + 1)


def holder_client(client_id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        print(f"Holder {client_id}: connected")

        # Tell main thread this holder is connected.
        holders_ready.wait()

        # Keep the pool worker blocked in recv().
        release_holders.wait()

        sock.sendall(REQUEST)
        response = sock.recv(1024)

        print(
            f"Holder {client_id}: "
            f"{'PASSED' if response == EXPECTED_RESPONSE else 'FAILED'}"
        )


def extra_client(client_id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        print(f"Extra client {client_id}: connected and sending PING")

        start = time.perf_counter()

        sock.sendall(REQUEST)
        response = sock.recv(1024)

        elapsed = time.perf_counter() - start

        print(
            f"Extra client {client_id}: "
            f"{'PASSED' if response == EXPECTED_RESPONSE else 'FAILED'} "
            f"after {elapsed:.2f} seconds"
        )


def main():
    holder_threads = []

    # Occupy all 3 pool workers.
    for client_id in range(1, HOLDER_COUNT + 1):
        thread = threading.Thread(
            target=holder_client,
            args=(client_id,),
        )

        holder_threads.append(thread)
        thread.start()

    # Wait until all holder clients are connected.
    holders_ready.wait()

    print()
    print("All 3 thread-pool workers should now be occupied.")
    print()

    extra_threads = []

    # These clients should be accepted,
    # but their handlers must wait in the pool queue.
    for client_id in range(1, EXTRA_CLIENT_COUNT + 1):
        thread = threading.Thread(
            target=extra_client,
            args=(client_id,),
        )

        extra_threads.append(thread)
        thread.start()

    print()
    print("Waiting 3 seconds before releasing pool workers...")
    print()

    time.sleep(3)

    release_holders.set()

    for thread in holder_threads:
        thread.join()

    for thread in extra_threads:
        thread.join()

    print()
    print("Starvation demonstration finished.")


if __name__ == "__main__":
    main()