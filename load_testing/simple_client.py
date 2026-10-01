import socket

HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
EXPECTED_RESPONSE = b"PONG\n"


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))

        client_socket.sendall(REQUEST)

        response = client_socket.recv(1024)

    print(f"Received raw bytes: {response!r}")

    if response != EXPECTED_RESPONSE:
        raise RuntimeError(
            f"Unexpected response: {response!r}"
        )

    print("Protocol test PASSED")


if __name__ == "__main__":
    main()