import socket


HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
RESPONSE = b"PONG\n"
ERROR_RESPONSE = b"ERROR\n"

# False during benchmark runs.
VERBOSE = False


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
            f"Sequential server listening on "
            f"{HOST}:{PORT}"
        )

        while True:
            client_socket, client_address = (
                server_socket.accept()
            )

            if VERBOSE:
                print(
                    f"Connected: "
                    f"{client_address}"
                )

            with client_socket:
                data = client_socket.recv(
                    1024
                )

                if not data:
                    continue

                if data == REQUEST:
                    client_socket.sendall(
                        RESPONSE
                    )

                else:
                    client_socket.sendall(
                        ERROR_RESPONSE
                    )


if __name__ == "__main__":
    main()