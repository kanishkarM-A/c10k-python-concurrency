import selectors
import socket


HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
RESPONSE = b"PONG\n"
ERROR_RESPONSE = b"ERROR\n"

VERBOSE = False

selector = selectors.DefaultSelector()


class ConnectionState:
    def __init__(self, address):
        self.address = address
        self.in_buffer = bytearray()
        self.out_buffer = bytearray()


def close_connection(sock):
    try:
        selector.unregister(sock)
    except Exception:
        pass

    sock.close()


def accept_connection(server_socket):
    client_socket, client_address = (
        server_socket.accept()
    )

    if VERBOSE:
        print(
            f"Accepted: {client_address}"
        )

    client_socket.setblocking(False)

    state = ConnectionState(
        client_address
    )

    selector.register(
        client_socket,
        selectors.EVENT_READ,
        data=state,
    )


def service_connection(key, mask):
    sock = key.fileobj
    state = key.data

    if mask & selectors.EVENT_READ:

        try:
            data = sock.recv(4096)

        except ConnectionResetError:
            close_connection(sock)
            return

        if not data:

            if VERBOSE:
                print(
                    f"Closed: {state.address}"
                )

            close_connection(sock)
            return

        state.in_buffer.extend(
            data
        )

        while b"\n" in state.in_buffer:

            line, _, remaining = (
                state.in_buffer.partition(
                    b"\n"
                )
            )

            state.in_buffer = bytearray(
                remaining
            )

            message = (
                bytes(line)
                + b"\n"
            )

            if message == REQUEST:
                state.out_buffer.extend(
                    RESPONSE
                )

            else:
                state.out_buffer.extend(
                    ERROR_RESPONSE
                )

        if state.out_buffer:

            selector.modify(
                sock,
                selectors.EVENT_READ
                | selectors.EVENT_WRITE,
                data=state,
            )

    if mask & selectors.EVENT_WRITE:

        if state.out_buffer:

            try:
                sent = sock.send(
                    state.out_buffer
                )

            except (
                BrokenPipeError,
                ConnectionResetError,
            ):
                close_connection(sock)
                return

            del state.out_buffer[:sent]

        if not state.out_buffer:

            selector.modify(
                sock,
                selectors.EVENT_READ,
                data=state,
            )


def main():
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as server_socket:

        server_socket.bind(
            (HOST, PORT)
        )

        server_socket.listen()

        server_socket.setblocking(
            False
        )

        selector.register(
            server_socket,
            selectors.EVENT_READ,
            data=None,
        )

        print(
            f"Selector server listening on "
            f"{HOST}:{PORT}"
        )

        try:
            while True:

                events = selector.select()

                for key, mask in events:

                    if key.data is None:
                        accept_connection(
                            key.fileobj
                        )

                    else:
                        service_connection(
                            key,
                            mask,
                        )

        finally:
            selector.close()


if __name__ == "__main__":
    main()