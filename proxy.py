#!/usr/bin/env python3

#echo "" | openssl s_client -connect localhost:3555 -servername production.cloudfront.docker.com -showcerts | awk '/BEGIN/ {} /BEGIN/, /END/ { print }'   | less

import socket
import threading

# HTTP proxy
PROXY_HOST = "localhost"
PROXY_PORT = 3128

# Destination reached through the proxy
TARGET_HOST = "production.cloudfront.docker.com"
TARGET_PORT = 443

# Local listener
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 3555


def create_proxy_tunnel():
    sock = socket.create_connection((PROXY_HOST, PROXY_PORT))

    connect_request = (
        "CONNECT {}:{} HTTP/1.1\r\n"
        "Host: {}:{}\r\n"
        "\r\n"
    ).format(TARGET_HOST, TARGET_PORT,
             TARGET_HOST, TARGET_PORT)

    sock.sendall(connect_request.encode("ascii"))

    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            raise Exception("Proxy closed connection")
        response += chunk

    first_line = response.split(b"\r\n", 1)[0]

    if b"200" not in first_line:
        raise Exception(
            "CONNECT failed: {}".format(
                first_line.decode(errors="replace")
            )
        )

    return sock


def pipe(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        dst.close()
        src.close()


def handle_client(client_sock):
    try:
        remote_sock = create_proxy_tunnel()

        t1 = threading.Thread(
            target=pipe,
            args=(client_sock, remote_sock)
        )
        t2 = threading.Thread(
            target=pipe,
            args=(remote_sock, client_sock)
        )

        t1.daemon = True
        t2.daemon = True

        t1.start()
        t2.start()

    except Exception as e:
        print("Client error:", e)
        client_sock.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(50)

    print("Listening on {}:{}".format(
        LISTEN_HOST,
        LISTEN_PORT
    ))

    while True:
        client_sock, addr = server.accept()
        print("Connection from", addr)

        t = threading.Thread(
            target=handle_client,
            args=(client_sock,)
        )
        t.daemon = True
        t.start()


if __name__ == "__main__":
    main()
