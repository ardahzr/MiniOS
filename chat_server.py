import socket
import threading
import datetime

HOST = '127.0.0.1'
PORT = 65432
MAX_CLIENTS = 10
clients = []
client_lock = threading.Lock()

def broadcast_message(message, sender_socket=None):
    with client_lock:
        for client_socket, _ in clients:
            if client_socket != sender_socket:
                try:
                    client_socket.sendall(message.encode('utf-8'))
                except socket.error:
                    pass

def handle_client(client_socket, addr):
    print(f"[SERVER] New connection from {addr}")
    username = None
    try:
        username_data = client_socket.recv(1024).decode('utf-8')
        if username_data.startswith("USERNAME:"):
            username = username_data.split(":", 1)[1]
        else:
            print(f"[SERVER] Invalid username protocol from {addr}. Closing connection.")
            client_socket.close()
            return

        with client_lock:
            clients.append((client_socket, username))
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        welcome_message = f"[{timestamp}] System: {username} has joined the chat."
        print(f"[SERVER] {username} connected.")
        broadcast_message(welcome_message)

        while True:
            try:
                message_data = client_socket.recv(1024)
                if not message_data:
                    break
                
                message_text = message_data.decode('utf-8')
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                full_message = f"[{timestamp}] {username}: {message_text}"
                
                print(f"[SERVER] Received from {username}: {message_text}")
                broadcast_message(full_message, client_socket)

            except ConnectionResetError:
                break
            except socket.error as e:
                print(f"[SERVER] Socket error with {username}: {e}")
                break
            except Exception as e:
                print(f"[SERVER] Error handling client {username}: {e}")
                break
    finally:
        with client_lock:
            client_tuple_to_remove = None
            for c_sock, u_name in clients:
                if c_sock == client_socket:
                    client_tuple_to_remove = (c_sock, u_name)
                    break
            if client_tuple_to_remove:
                clients.remove(client_tuple_to_remove)

        if username:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            disconnect_message = f"[{timestamp}] System: {username} has left the chat."
            print(f"[SERVER] {username} disconnected.")
            broadcast_message(disconnect_message)
        
        client_socket.close()
        print(f"[SERVER] Connection closed with {addr}")


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_CLIENTS)
        print(f"[SERVER] Listening on {HOST}:{PORT}")

        while True:
            client_socket, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.daemon = True
            thread.start()
    except OSError as e:
        print(f"[SERVER] Error starting server: {e} (Is the port already in use?)")
    except KeyboardInterrupt:
        print("[SERVER] Shutting down...")
    finally:
        print("[SERVER] Closing all client connections...")
        with client_lock:
            for client_socket, _ in clients:
                client_socket.close()
        server_socket.close()
        print("[SERVER] Server socket closed.")

if __name__ == '__main__':
    start_server()