import socket
import threading

HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
EXPECTED_RESPONSE = b"PONG\n"

CLIENT_COUNT = 5


def run_client(client_id):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, PORT))

            client_socket.sendall(REQUEST)

            response = client_socket.recv(1024)

        if response == EXPECTED_RESPONSE:
            print(f"Client {client_id}: PASSED")
        else:
            print(f"Client {client_id}: FAILED - {response!r}")

    except Exception as error:
        print(f"Client {client_id}: ERROR - {error}")


def main():
    threads = []

    for client_id in range(1, CLIENT_COUNT + 1):
        thread = threading.Thread(
            target=run_client,
            args=(client_id,),
        )

        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("All clients finished.")


if __name__ == "__main__":
    main()