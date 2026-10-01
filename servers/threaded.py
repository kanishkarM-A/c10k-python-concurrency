import socket
import threading

HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
RESPONSE = b"PONG\n"
ERROR_RESPONSE = b"ERROR\n"

# False for real benchmark runs.
VERBOSE = False


def handle_client(client_socket, client_address):
    if VERBOSE:
        print(f"Worker started for {client_address}")

    with client_socket:
        data = client_socket.recv(1024)

        if not data:
            return

        if data == REQUEST:
            client_socket.sendall(RESPONSE)
        else:
            client_socket.sendall(ERROR_RESPONSE)

    if VERBOSE:
        print(f"Worker finished for {client_address}")


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
            f"Threaded server listening on "
            f"{HOST}:{PORT}"
        )

        while True:
            client_socket, client_address = (
                server_socket.accept()
            )

            worker = threading.Thread(
                target=handle_client,
                args=(
                    client_socket,
                    client_address,
                ),
            )

            worker.start()


if __name__ == "__main__":
    main()