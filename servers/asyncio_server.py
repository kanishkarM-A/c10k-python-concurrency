import asyncio

HOST = "127.0.0.1"
PORT = 8080

REQUEST = b"PING\n"
RESPONSE = b"PONG\n"
ERROR_RESPONSE = b"ERROR\n"

# Keep False during real benchmarks.
VERBOSE = False


async def handle_client(reader, writer):
    address = writer.get_extra_info("peername")

    if VERBOSE:
        print(f"Connected: {address}")

    try:
        while True:
            data = await reader.readline()

            if not data:
                break

            if data == REQUEST:
                writer.write(RESPONSE)
            else:
                writer.write(ERROR_RESPONSE)

            await writer.drain()

    except ConnectionResetError:
        pass

    finally:
        if VERBOSE:
            print(f"Closed: {address}")

        writer.close()

        try:
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(
        handle_client,
        HOST,
        PORT,
    )

    print(
        f"Asyncio server listening on "
        f"{HOST}:{PORT}"
    )

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())