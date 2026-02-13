#!/usr/bin/env python3
"""
TCP Socket Chat Client (CLI)
============================

This client demonstrates how to connect to a TCP server and communicate.
Features:
- Connect to chat server with username
- Send and receive messages simultaneously using threads
- Support for chat commands (/help, /users, /whisper, /quit)

Author: Educational Example
"""

import socket
import threading
import sys
import signal

# =============================================================================
# CONFIGURATION
# =============================================================================

SERVER_HOST = '127.0.0.1'  # Server address (localhost for testing)
SERVER_PORT = 5000         # Must match server's port
BUFFER_SIZE = 1024         # Size of receive buffer


# =============================================================================
# CLIENT STATE
# =============================================================================

client_socket: socket.socket = None
running = True


# =============================================================================
# NETWORK OPERATIONS
# =============================================================================

def connect_to_server() -> socket.socket:
    """
    Create a TCP socket and connect to the server.
    
    Connection Process:
    -------------------
    1. Create socket (AF_INET = IPv4, SOCK_STREAM = TCP)
    2. Connect to server's address and port
    3. Return connected socket
    
    The TCP handshake happens automatically during connect():
    - Client sends SYN
    - Server responds with SYN-ACK
    - Client sends ACK
    - Connection established!
    """
    try:
        # Create TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        print(f"[CLIENT] Connecting to {SERVER_HOST}:{SERVER_PORT}...")
        
        # Connect to server
        # This initiates the TCP three-way handshake
        sock.connect((SERVER_HOST, SERVER_PORT))
        
        print(f"[CLIENT] Connected successfully!")
        return sock
        
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to server at {SERVER_HOST}:{SERVER_PORT}")
        print("[ERROR] Make sure the server is running.")
        sys.exit(1)
    except socket.gaierror:
        print(f"[ERROR] Could not resolve address: {SERVER_HOST}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)


def receive_messages(sock: socket.socket):
    """
    Continuously receive messages from the server.
    
    This function runs in a separate thread to allow simultaneous
    sending and receiving (full-duplex communication).
    
    TCP is full-duplex, meaning data can flow both directions
    simultaneously over the same connection.
    """
    global running
    
    while running:
        try:
            # recv() blocks until data arrives or connection closes
            # Returns empty bytes when connection is closed
            data = sock.recv(BUFFER_SIZE)
            
            if not data:
                # Server closed the connection
                print("\n[CLIENT] Server closed the connection.")
                running = False
                break
            
            # Decode bytes to string and display
            message = data.decode('utf-8')
            
            # Print message (clear current line first for clean output)
            print(f"\r{message}")
            
            # Reprint prompt
            print("> ", end='', flush=True)
            
        except ConnectionResetError:
            print("\n[CLIENT] Connection reset by server.")
            running = False
            break
        except OSError:
            # Socket was closed
            break
        except Exception as e:
            if running:
                print(f"\n[CLIENT] Error receiving message: {e}")
            break


def send_messages(sock: socket.socket):
    """
    Read user input and send messages to the server.
    
    Runs in the main thread.
    """
    global running
    
    print("\n" + "=" * 50)
    print("Type your messages and press Enter to send.")
    print("Commands: /help, /users, /whisper <user> <msg>, /quit")
    print("=" * 50 + "\n")
    
    while running:
        try:
            # Get user input
            # Using print for prompt to work better with receive thread
            print("> ", end='', flush=True)
            message = input()
            
            if not running:
                break
            
            if not message:
                continue
            
            # Check for local quit command
            if message.lower() == '/quit':
                print("[CLIENT] Disconnecting...")
                running = False
                break
            
            # Send message to server
            # encode() converts string to bytes
            sock.sendall(message.encode('utf-8'))
            
        except EOFError:
            # Ctrl+D pressed
            print("\n[CLIENT] Disconnecting...")
            running = False
            break
        except KeyboardInterrupt:
            # Ctrl+C pressed
            print("\n[CLIENT] Disconnecting...")
            running = False
            break
        except BrokenPipeError:
            print("\n[CLIENT] Connection lost.")
            running = False
            break
        except Exception as e:
            if running:
                print(f"\n[CLIENT] Error sending message: {e}")
            running = False
            break


def disconnect(sock: socket.socket):
    """
    Gracefully close the connection.
    
    TCP Connection Termination:
    ---------------------------
    1. One side sends FIN (finish) packet
    2. Other side ACKs the FIN
    3. Other side sends its own FIN
    4. First side ACKs that FIN
    - Connection fully closed
    """
    global running
    running = False
    
    try:
        # Shut down the socket for both reading and writing
        # This sends a FIN packet to the server
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass
    
    try:
        # Close the socket, releasing system resources
        sock.close()
    except:
        pass
    
    print("[CLIENT] Disconnected.")


def signal_handler(signum, frame):
    """
    Handle Ctrl+C (SIGINT) gracefully.
    """
    global running
    print("\n[CLIENT] Caught interrupt signal. Disconnecting...")
    running = False
    if client_socket:
        disconnect(client_socket)
    sys.exit(0)


# =============================================================================
# MAIN CLIENT LOOP
# =============================================================================

def main():
    global client_socket
    
    print("=" * 50)
    print("       PYTHON CHAT CLIENT (CLI)")
    print("=" * 50)
    
    # Allow custom server address via command line
    global SERVER_HOST, SERVER_PORT
    if len(sys.argv) >= 2:
        SERVER_HOST = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            SERVER_PORT = int(sys.argv[2])
        except ValueError:
            print(f"[ERROR] Invalid port: {sys.argv[2]}")
            sys.exit(1)
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Connect to server
    client_socket = connect_to_server()
    
    # Handle username registration prompt
    try:
        # Receive welcome message
        welcome = client_socket.recv(BUFFER_SIZE).decode('utf-8')
        print(welcome, end='')
        
        # Receive username prompt
        prompt = client_socket.recv(BUFFER_SIZE).decode('utf-8')
        print(prompt, end='')
        
        # Send username
        username = input()
        client_socket.sendall(username.encode('utf-8'))
        
        # Start receive thread
        # This allows us to receive messages while typing
        receive_thread = threading.Thread(
            target=receive_messages,
            args=(client_socket,),
            daemon=True  # Exit when main thread exits
        )
        receive_thread.start()
        
        # Main thread handles sending
        send_messages(client_socket)
        
        # Wait for receive thread to finish
        receive_thread.join(timeout=2)
        
    except Exception as e:
        print(f"\n[CLIENT] Error: {e}")
    
    finally:
        disconnect(client_socket)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    main()
