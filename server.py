#!/usr/bin/env python3
"""
TCP Socket Chat Server
======================

This server demonstrates fundamental socket programming concepts:
- TCP socket creation and binding
- Accepting multiple client connections
- Threading for concurrent client handling
- Message broadcasting and private messaging

Author: Educational Example
"""

import socket
import threading
import datetime
import signal
import sys
from typing import Dict, Set

# =============================================================================
# CONFIGURATION
# =============================================================================

HOST = '127.0.0.1'  # Localhost - use '0.0.0.0' to accept connections from any interface
PORT = 5000         # Port to listen on (non-privileged ports are > 1024)
MAX_CONNECTIONS = 50  # Maximum number of simultaneous connections
BUFFER_SIZE = 1024  # Size of message buffer in bytes

# =============================================================================
# SERVER STATE
# =============================================================================

# Dictionary to store client connections: {username: client_socket}
# Thread-safe access is important - we use a lock for this
clients: Dict[str, socket.socket] = {}
clients_lock = threading.Lock()

# Server socket (global so signal handler can close it)
server_socket: socket.socket = None

# Flag to control server shutdown
running = True


# =============================================================================
# SOCKET OPERATIONS EXPLAINED
# =============================================================================

def create_server_socket() -> socket.socket:
    """
    Create a TCP server socket.
    
    What is a socket?
    -----------------
    A socket is an endpoint for sending or receiving data across a network.
    Think of it like a telephone - it allows two programs to communicate.
    
    TCP vs UDP:
    -----------
    - TCP (Transmission Control Protocol): Connection-oriented, reliable,
      ordered delivery. Like a phone call - established connection, 
      guaranteed delivery.
    - UDP (User Datagram Protocol): Connectionless, unreliable, faster.
      Like sending letters - no guarantee of delivery or order.
    
    This server uses TCP for reliable chat messaging.
    """
    # socket.AF_INET: Use IPv4 addressing
    # socket.SOCK_STREAM: Use TCP (stream-oriented, connection-based)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # SO_REUSEADDR allows the socket to bind to an address/port that's in
    # TIME_WAIT state. This prevents "Address already in use" errors when
    # restarting the server quickly.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    return sock


def broadcast_message(message: str, sender: str = None, exclude: Set[str] = None):
    """
    Send a message to all connected clients except excluded ones.
    
    Thread Safety Note:
    -------------------
    Since multiple threads (one per client) may call this simultaneously,
    we need to protect access to the shared 'clients' dictionary with a lock.
    """
    exclude = exclude or set()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Format message with timestamp
    if sender:
        formatted_msg = f"[{timestamp}] {sender}: {message}"
    else:
        formatted_msg = f"[{timestamp}] *** {message} ***"
    
    with clients_lock:
        # Create a copy of items to avoid modification during iteration
        client_items = list(clients.items())
    
    for username, client_sock in client_items:
        if username not in exclude:
            try:
                # encode() converts string to bytes (UTF-8 encoding)
                client_sock.sendall(formatted_msg.encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                # Client disconnected unexpectedly
                remove_client(username)
            except Exception as e:
                print(f"Error broadcasting to {username}: {e}")
                remove_client(username)


def send_private_message(sender: str, recipient: str, message: str):
    """
    Send a private message from one user to another.
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    with clients_lock:
        if recipient not in clients:
            # Recipient not found - notify sender
            if sender in clients:
                error_msg = f"[{timestamp}] *** User '{recipient}' not found or offline ***"
                clients[sender].sendall(error_msg.encode('utf-8'))
            return
        
        recipient_sock = clients[recipient]
        sender_sock = clients.get(sender)
    
    # Send to recipient
    whisper_msg = f"[{timestamp}] [WHISPER from {sender}]: {message}"
    try:
        recipient_sock.sendall(whisper_msg.encode('utf-8'))
    except Exception as e:
        print(f"Error sending whisper to {recipient}: {e}")
        remove_client(recipient)
    
    # Confirm to sender
    if sender_sock:
        confirm_msg = f"[{timestamp}] [WHISPER to {recipient}]: {message}"
        try:
            sender_sock.sendall(confirm_msg.encode('utf-8'))
        except Exception as e:
            print(f"Error confirming whisper to {sender}: {e}")
            remove_client(sender)


def send_system_message(username: str, message: str):
    """
    Send a system message to a specific user.
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    system_msg = f"[{timestamp}] [SYSTEM]: {message}"
    
    with clients_lock:
        if username in clients:
            try:
                clients[username].sendall(system_msg.encode('utf-8'))
            except Exception as e:
                print(f"Error sending system message to {username}: {e}")
                remove_client(username)


def get_online_users() -> str:
    """
    Return a formatted list of online users.
    """
    with clients_lock:
        user_list = sorted(clients.keys())
    
    if not user_list:
        return "No users online."
    
    users_str = ", ".join(user_list)
    return f"Online users ({len(user_list)}): {users_str}"


def remove_client(username: str):
    """
    Remove a client from the server and close their socket.
    Called when a client disconnects or on error.
    """
    with clients_lock:
        if username in clients:
            try:
                clients[username].close()
            except:
                pass
            del clients[username]
            print(f"[SERVER] {username} disconnected and removed from clients")


# =============================================================================
# CLIENT HANDLER
# =============================================================================

def handle_client(client_socket: socket.socket, address: tuple):
    """
    Handle communication with a single client.
    
    This function runs in a separate thread for each connected client.
    Threading allows the server to handle multiple clients simultaneously
    without blocking.
    
    Threading Model:
    ----------------
    - Main thread: Listens for new connections (accept())
    - Client threads: Each handles one connected client (recv(), send())
    
    This is the "one thread per client" model - simple but effective for
    small to medium numbers of connections.
    """
    username = None
    
    try:
        # ====================================================================
        # USERNAME REGISTRATION
        # ====================================================================
        
        # Request username from client
        client_socket.sendall(b"Welcome to Python Chat Server!\n")
        client_socket.sendall(b"Enter your username: ")
        
        # Receive username (bytes -> decode to string -> strip whitespace)
        username_data = client_socket.recv(BUFFER_SIZE)
        if not username_data:
            # Client disconnected before sending username
            client_socket.close()
            return
        
        username = username_data.decode('utf-8').strip()
        
        # Validate username
        if not username:
            client_socket.sendall(b"[SYSTEM]: Username cannot be empty. Disconnecting.\n")
            client_socket.close()
            return
        
        with clients_lock:
            if username in clients:
                client_socket.sendall(f"[SYSTEM]: Username '{username}' is already taken. Disconnecting.\n".encode('utf-8'))
                client_socket.close()
                return
        
        # Register client
        with clients_lock:
            clients[username] = client_socket
        
        print(f"[SERVER] {username} joined from {address[0]}:{address[1]}")
        
        # Notify everyone about new user
        broadcast_message(f"{username} has joined the chat!", exclude={username})
        send_system_message(username, f"Welcome, {username}! Type /help for available commands.")
        
        # ====================================================================
        # MESSAGE LOOP
        # ====================================================================
        
        while running:
            # Receive data from client
            # recv() blocks until data arrives or connection closes
            data = client_socket.recv(BUFFER_SIZE)
            
            if not data:
                # Empty data means client disconnected gracefully
                break
            
            message = data.decode('utf-8').strip()
            
            if not message:
                continue
            
            # =================================================================
            # COMMAND HANDLING
            # =================================================================
            
            if message.startswith('/'):
                parts = message.split(' ', 2)  # Split into max 3 parts for /whisper
                command = parts[0].lower()
                
                if command == '/help':
                    help_text = """
Available commands:
  /help              - Show this help message
  /users             - List online users
  /whisper <user> <msg> - Send private message to user
  /quit              - Disconnect from server

To send a regular message, just type and press Enter.
"""
                    send_system_message(username, help_text)
                
                elif command == '/users':
                    send_system_message(username, get_online_users())
                
                elif command == '/whisper':
                    if len(parts) < 3:
                        send_system_message(username, "Usage: /whisper <username> <message>")
                    else:
                        recipient = parts[1]
                        private_msg = parts[2]
                        if recipient == username:
                            send_system_message(username, "You can't whisper to yourself!")
                        else:
                            send_private_message(username, recipient, private_msg)
                
                elif command == '/quit':
                    send_system_message(username, "Goodbye!")
                    break
                
                else:
                    send_system_message(username, f"Unknown command: {command}. Type /help for help.")
            
            else:
                # Regular message - broadcast to all
                broadcast_message(message, sender=username, exclude={username})
    
    except ConnectionResetError:
        print(f"[SERVER] Connection reset by {username or address}")
    except BrokenPipeError:
        print(f"[SERVER] Broken pipe for {username or address}")
    except Exception as e:
        print(f"[SERVER] Error handling client {username or address}: {e}")
    
    finally:
        # Cleanup when client disconnects
        if username:
            remove_client(username)
            broadcast_message(f"{username} has left the chat.")
        
        try:
            client_socket.close()
        except:
            pass


# =============================================================================
# SERVER LIFECYCLE
# =============================================================================

def shutdown_server(signum=None, frame=None):
    """
    Gracefully shutdown the server.
    Called on SIGINT (Ctrl+C) or SIGTERM.
    """
    global running
    running = False
    
    print("\n[SERVER] Shutting down...")
    
    # Notify all clients
    with clients_lock:
        for username, client_sock in list(clients.items()):
            try:
                client_sock.sendall(b"\n[SYSTEM]: Server is shutting down. Goodbye!\n")
                client_sock.close()
            except:
                pass
        clients.clear()
    
    # Close server socket
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
    
    print("[SERVER] Shutdown complete.")
    sys.exit(0)


def start_server():
    """
    Main server startup and connection acceptance loop.
    """
    global server_socket
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_server)   # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_server)  # kill command
    
    print("=" * 60)
    print("       PYTHON TCP CHAT SERVER")
    print("=" * 60)
    print()
    
    # Create and configure server socket
    server_socket = create_server_socket()
    
    # Bind socket to address and port
    # This associates the socket with a specific network interface and port
    server_socket.bind((HOST, PORT))
    
    # Start listening for incoming connections
    # The parameter is the backlog - max number of queued connections
    server_socket.listen(MAX_CONNECTIONS)
    
    print(f"[SERVER] Listening on {HOST}:{PORT}")
    print(f"[SERVER] Maximum connections: {MAX_CONNECTIONS}")
    print(f"[SERVER] Press Ctrl+C to stop the server")
    print("-" * 60)
    
    while running:
        try:
            # accept() blocks until a client connects
            # Returns: (new_socket, (client_address, client_port))
            client_sock, client_addr = server_socket.accept()
            
            print(f"[SERVER] New connection from {client_addr[0]}:{client_addr[1]}")
            
            # Create a new thread to handle this client
            # This allows the main thread to continue accepting new connections
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_sock, client_addr),
                daemon=True  # Thread exits when main thread exits
            )
            client_thread.start()
            
            print(f"[SERVER] Active connections: {threading.active_count() - 1}")
            
        except OSError:
            # Socket was closed (likely during shutdown)
            break
        except Exception as e:
            print(f"[SERVER] Error accepting connection: {e}")
    
    shutdown_server()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    start_server()
