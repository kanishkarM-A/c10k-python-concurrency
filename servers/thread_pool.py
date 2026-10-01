import socket
from concurrent.futures import ThreadPoolExecutor

HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
RESPONSE = b"PONG\n"
ERROR_RESPONSE = b"ERROR\n"

MAX_WORKERS = 3

VERBOSE = False


def handle_client(client_socket, client_address):
    if VERBOSE:
        print(f"Handling {client_address}")

    with client_socket:
        data = client_socket.recv(1024)

        if not data:
            return

        if data == REQUEST:
            client_socket.sendall(RESPONSE)
        else:
            client_socket.sendall(ERROR_RESPONSE)

    if VERBOSE:
        print(f"Finished {client_address}")


def main():
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as server_socket:

        server_socket.bind(
            (HOST, PORT)
        )

        server_socket.listen()

        print(
            f"Thread-pool server listening on "
            f"{HOST}:{PORT}"
        )

        print(
            f"MAX_WORKERS = {MAX_WORKERS}"
        )

        with ThreadPoolExecutor(
            max_workers=MAX_WORKERS
        ) as executor:

            while True:
                client_socket, client_address = (
                    server_socket.accept()
                )

                executor.submit(
                    handle_client,
                    client_socket,
                    client_address,
                )


if __name__ == "__main__":
    main()