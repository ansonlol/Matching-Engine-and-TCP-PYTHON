import sys 
import socket 

def main():
    if len(sys.argv) != 2:
        print("python scritp <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:

        client_socket.connect(("127.0.0.1", port))
        print("connected")



    finally:
        client_socket.close()

if __name__ == "__main__":
    main()