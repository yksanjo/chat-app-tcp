# Python TCP Socket Chat Application

A complete educational chat application demonstrating TCP socket programming fundamentals in Python. Includes a multi-client server, CLI client, and optional GUI client.

## 📁 Project Structure

```
chat-app/
├── server.py       # Multi-client chat server with threading
├── client.py       # Command-line chat client
├── client_gui.py   # GUI chat client (tkinter)
└── README.md       # This file
```

---

## 🚀 Quick Start

### 1. Start the Server

```bash
cd /Users/yoshikondo/network-projects/chat-app
python3 server.py
```

You should see:
```
============================================================
       PYTHON TCP CHAT SERVER
============================================================

[SERVER] Listening on 127.0.0.1:5000
[SERVER] Maximum connections: 50
[SERVER] Press Ctrl+C to stop the server
------------------------------------------------------------
```

### 2. Connect Clients

**Terminal 1 (CLI Client):**
```bash
python3 client.py
# Enter username: Alice
```

**Terminal 2 (Another CLI Client):**
```bash
python3 client.py
# Enter username: Bob
```

**Or use the GUI Client:**
```bash
python3 client_gui.py
```

### 3. Chat!

Type messages and press Enter to send to everyone.

---

## 📚 Educational Concepts

### What are TCP Sockets?

A **socket** is an endpoint for sending or receiving data across a computer network. Think of it like a telephone:

- **IP Address** = Phone number (identifies the computer)
- **Port** = Extension number (identifies the specific application)
- **Socket** = The actual telephone connection

**Key Socket Operations:**

| Operation | Server | Client | Description |
|-----------|--------|--------|-------------|
| `socket()` | ✓ | ✓ | Create a new socket |
| `bind()` | ✓ | | Bind to a specific address/port |
| `listen()` | ✓ | | Listen for incoming connections |
| `accept()` | ✓ | | Accept a connection (returns new socket) |
| `connect()` | | ✓ | Connect to a server |
| `send()` / `sendall()` | ✓ | ✓ | Send data |
| `recv()` | ✓ | ✓ | Receive data |
| `close()` | ✓ | ✓ | Close the connection |

### TCP vs UDP

| Feature | TCP (Transmission Control Protocol) | UDP (User Datagram Protocol) |
|---------|-------------------------------------|------------------------------|
| **Connection** | Connection-oriented | Connectionless |
| **Reliability** | Guaranteed delivery | No guarantee |
| **Order** | Messages arrive in order | No ordering guarantee |
| **Speed** | Slower (more overhead) | Faster (less overhead) |
| **Use Case** | Chat, file transfer, web browsing | Streaming, gaming, DNS |
| **Analogy** | Phone call (connected, reliable) | Postcard (fast, no guarantee) |

**This chat app uses TCP** because we need reliable, ordered message delivery.

### How Threading Enables Multiple Clients

Python's `socket.recv()` is **blocking** - it waits until data arrives. Without threading, the server could only handle one client at a time!

**Solution: One Thread Per Client**

```
Main Thread              Client Thread 1          Client Thread 2
    │                          │                        │
    ├─ accept() ──Client 1─────┤                        │
    │                          ├─ recv/send loop ───────┤
    ├─ accept() ──Client 2─────┤                        │
    │                          │                   ├─ recv/send loop
    ├─ accept() ──wait─────────┤                        │
```

**Thread Safety:**
- Multiple threads access shared data (the `clients` dictionary)
- We use a `threading.Lock()` to prevent race conditions
- Lock is acquired before reading/writing shared data

### The TCP Three-Way Handshake

When a client connects, TCP establishes the connection:

```
Client                          Server
   │                                │
   ├────────── SYN ───────────────→│  "I want to connect"
   │                                │
   │←──────── SYN-ACK ─────────────┤  "I got it, you there?"
   │                                │
   ├────────── ACK ───────────────→│  "I'm here, let's talk!"
   │                                │
   ═════════════════════════════════  Connection Established!
```

---

## 🎮 Available Commands

### Client Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/users` | List all online users |
| `/whisper <username> <message>` | Send private message |
| `/quit` | Disconnect from server |

### Example Chat Session

```
[12:34:56] *** Alice has joined the chat! ***
[12:35:02] [SYSTEM]: Welcome, Alice! Type /help for available commands.

> /users
[12:35:10] [SYSTEM]: Online users (1): Alice

> Hello everyone!
[12:35:15] You: Hello everyone!

[12:36:01] *** Bob has joined the chat! ***
[12:36:05] Bob: Hey Alice!

> /whisper Bob Hi Bob, this is private
[12:36:20] [WHISPER to Bob]: Hi Bob, this is private

[12:36:22] [WHISPER from Bob]: Hey! Got your message.

> /quit
[CLIENT] Disconnecting...
[CLIENT] Disconnected.
```

---

## 🔧 Running with Custom Settings

### Change Server Address

**CLI Client:**
```bash
python3 client.py 192.168.1.100 8080
```

**GUI Client:**
Edit the "Server" field in the connection panel.

**Server:**
Edit these variables in `server.py`:
```python
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 8080       # Custom port
```

### Network Setup for Multiple Computers

1. Find your server's IP address:
   ```bash
   # Linux/Mac
   ifconfig
   
   # Windows
   ipconfig
   ```

2. Update server to listen on all interfaces:
   ```python
   HOST = '0.0.0.0'  # In server.py
   ```

3. Connect clients using server's IP:
   ```bash
   python3 client.py 192.168.1.5 5000
   ```

---

## 🧪 Code Highlights

### Creating a Server Socket

```python
import socket

# Create TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Allow address reuse (prevents "Address already in use" errors)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind to address and port
sock.bind(('127.0.0.1', 5000))

# Listen for connections (backlog of 50)
sock.listen(50)

# Accept a connection
client_socket, address = sock.accept()
```

### Creating a Client Socket

```python
import socket

# Create TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
sock.connect(('127.0.0.1', 5000))

# Send data
sock.sendall(b"Hello, Server!")

# Receive data
data = sock.recv(1024)
message = data.decode('utf-8')
```

### Threading for Concurrent Clients

```python
import threading

def handle_client(client_socket, address):
    # Handle one client's messages
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        # Process message...

# In main server loop:
client_sock, addr = server_socket.accept()
thread = threading.Thread(
    target=handle_client,
    args=(client_sock, addr),
    daemon=True
)
thread.start()
```

### Thread-Safe Shared State

```python
import threading

clients = {}           # Shared dictionary
clients_lock = threading.Lock()  # Protects access

# Safe read/write:
with clients_lock:
    clients[username] = client_socket
    
with clients_lock:
    if username in clients:
        del clients[username]
```

---

## ⚠️ Error Handling

The application handles these network scenarios:

| Scenario | Handling |
|----------|----------|
| Server not running | Client shows "Connection refused" |
| Client disconnects | Server removes from list, notifies others |
| Server shuts down | Clients receive notification |
| Network interruption | Graceful cleanup on both sides |
| Duplicate username | Server rejects connection |

---

## 📖 Learning Path

1. **Start here:** Read the code comments in `server.py` and `client.py`
2. **Experiment:** Run multiple clients, try the commands
3. **Modify:** Add new features (see ideas below)
4. **Extend:** Try async/await with `asyncio` instead of threading

### Feature Extension Ideas

- [ ] File sharing between users
- [ ] Password authentication
- [ ] Chat history/persistence
- [ ] Message encryption (TLS/SSL)
- [ ] Chat rooms/channels
- [ ] User status (away, busy, etc.)

---

## 🔗 Additional Resources

- [Python socket documentation](https://docs.python.org/3/library/socket.html)
- [Python threading documentation](https://docs.python.org/3/library/threading.html)
- [TCP/IP Illustrated](https://en.wikipedia.org/wiki/TCP/IP_Illustrated) (book)
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)

---

## 📝 License

This educational code is provided as-is for learning purposes.
