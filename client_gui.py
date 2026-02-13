#!/usr/bin/env python3
"""
TCP Socket Chat Client (GUI)
============================

A graphical version of the chat client using tkinter.
Demonstrates how to integrate socket programming with GUI event loops.

Author: Educational Example
"""

import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import sys

# =============================================================================
# CONFIGURATION
# =============================================================================

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000
BUFFER_SIZE = 1024


# =============================================================================
# CHAT CLIENT GUI CLASS
# =============================================================================

class ChatClientGUI:
    """
    A tkinter-based GUI for the chat client.
    
    GUI + Socket Programming Notes:
    -------------------------------
    - Tkinter runs its own event loop (mainloop())
    - Socket recv() is blocking - we use a separate thread
    - Thread-safe GUI updates using after() method
    """
    
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Python Chat Client")
        self.master.geometry("600x500")
        self.master.minsize(400, 300)
        
        # Connection state
        self.client_socket: socket.socket = None
        self.username: str = None
        self.connected: bool = False
        self.receive_thread: threading.Thread = None
        
        # Message queue for thread-safe GUI updates
        self.message_queue = []
        
        self._build_ui()
        self._check_message_queue()  # Start queue checker
    
    def _build_ui(self):
        """
        Build the user interface components.
        """
        # Configure grid weights for resizing
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        
        # === Main Frame ===
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # === Connection Frame ===
        conn_frame = tk.LabelFrame(main_frame, text="Connection", padx=5, pady=5)
        conn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        conn_frame.grid_columnconfigure(1, weight=1)
        
        # Server address
        tk.Label(conn_frame, text="Server:").grid(row=0, column=0, sticky="w")
        self.server_entry = tk.Entry(conn_frame)
        self.server_entry.insert(0, f"{SERVER_HOST}:{SERVER_PORT}")
        self.server_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Username
        tk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.username_entry = tk.Entry(conn_frame)
        self.username_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(5, 0))
        
        # Connect button
        self.connect_btn = tk.Button(
            conn_frame, 
            text="Connect", 
            command=self._connect,
            bg="#4CAF50",
            fg="white",
            width=15
        )
        self.connect_btn.grid(row=0, column=2, rowspan=2, sticky="ns", padx=5)
        
        # === Chat Display ===
        chat_frame = tk.LabelFrame(main_frame, text="Chat", padx=5, pady=5)
        chat_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        # Scrolled text widget for chat history
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            state='disabled',
            font=('Consolas', 10)
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.tag_config('system', foreground='gray')
        self.chat_display.tag_config('whisper', foreground='purple')
        self.chat_display.tag_config('self', foreground='blue')
        self.chat_display.tag_config('error', foreground='red')
        self.chat_display.tag_config('timestamp', foreground='darkgray')
        
        # === Message Input ===
        input_frame = tk.Frame(main_frame)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.msg_entry = tk.Entry(input_frame, font=('Consolas', 10))
        self.msg_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.msg_entry.bind('<Return>', lambda e: self._send_message())
        self.msg_entry.config(state='disabled')
        
        self.send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self._send_message,
            bg="#2196F3",
            fg="white",
            width=10
        )
        self.send_btn.grid(row=0, column=1)
        self.send_btn.config(state='disabled')
        
        # === Status Bar ===
        self.status_var = tk.StringVar(value="Disconnected")
        status_bar = tk.Label(
            main_frame,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        
        # === Help Button ===
        help_btn = tk.Button(
            main_frame,
            text="Help",
            command=self._show_help
        )
        help_btn.grid(row=4, column=0, sticky="e", pady=(5, 0))
    
    def _log(self, message: str, tag: str = None):
        """
        Add a message to the chat display.
        Thread-safe: can be called from any thread.
        """
        self.message_queue.append((message, tag))
    
    def _check_message_queue(self):
        """
        Process pending messages in the queue.
        Must be called from main thread for thread safety.
        """
        while self.message_queue:
            message, tag = self.message_queue.pop(0)
            self._append_to_chat(message, tag)
        
        # Schedule next check (every 100ms)
        self.master.after(100, self._check_message_queue)
    
    def _append_to_chat(self, message: str, tag: str = None):
        """
        Append message to chat display widget.
        Must be called from main thread only!
        """
        self.chat_display.config(state='normal')
        if tag:
            self.chat_display.insert(tk.END, message + '\n', tag)
        else:
            self.chat_display.insert(tk.END, message + '\n')
        self.chat_display.see(tk.END)  # Scroll to bottom
        self.chat_display.config(state='disabled')
    
    def _connect(self):
        """
        Connect to the chat server.
        """
        if self.connected:
            self._disconnect()
            return
        
        # Parse server address
        server_str = self.server_entry.get().strip()
        try:
            if ':' in server_str:
                host, port_str = server_str.rsplit(':', 1)
                port = int(port_str)
            else:
                host = server_str
                port = SERVER_PORT
        except ValueError:
            messagebox.showerror("Error", "Invalid server address format. Use host:port")
            return
        
        # Get username
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return
        
        try:
            # Create and connect socket
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._log(f"Connecting to {host}:{port}...", 'system')
            self.client_socket.connect((host, port))
            
            # Receive welcome and prompt
            welcome = self.client_socket.recv(BUFFER_SIZE).decode('utf-8')
            prompt = self.client_socket.recv(BUFFER_SIZE).decode('utf-8')
            
            # Send username
            self.client_socket.sendall(username.encode('utf-8'))
            
            self.username = username
            self.connected = True
            
            # Update UI
            self.connect_btn.config(text="Disconnect", bg="#f44336")
            self.msg_entry.config(state='normal')
            self.send_btn.config(state='normal')
            self.server_entry.config(state='disabled')
            self.username_entry.config(state='disabled')
            self.status_var.set(f"Connected as {username}")
            
            self._log(f"Connected successfully!", 'system')
            
            # Start receive thread
            self.receive_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True
            )
            self.receive_thread.start()
            
            # Focus message entry
            self.msg_entry.focus_set()
            
        except ConnectionRefusedError:
            self._log(f"Connection refused. Is the server running?", 'error')
            self._cleanup_connection()
        except Exception as e:
            self._log(f"Connection error: {e}", 'error')
            self._cleanup_connection()
    
    def _disconnect(self):
        """
        Disconnect from the server.
        """
        if not self.connected:
            return
        
        self._log("Disconnecting...", 'system')
        
        try:
            self.client_socket.sendall(b'/quit')
        except:
            pass
        
        self._cleanup_connection()
    
    def _cleanup_connection(self):
        """
        Clean up socket and reset UI state.
        """
        self.connected = False
        
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        
        try:
            self.client_socket.close()
        except:
            pass
        
        self.client_socket = None
        
        # Reset UI
        self.connect_btn.config(text="Connect", bg="#4CAF50")
        self.msg_entry.config(state='disabled')
        self.send_btn.config(state='disabled')
        self.server_entry.config(state='normal')
        self.username_entry.config(state='normal')
        self.status_var.set("Disconnected")
    
    def _send_message(self):
        """
        Send a message to the server.
        """
        if not self.connected or not self.client_socket:
            return
        
        message = self.msg_entry.get().strip()
        if not message:
            return
        
        try:
            self.client_socket.sendall(message.encode('utf-8'))
            self.msg_entry.delete(0, tk.END)
            
            # Display own messages locally (optional, server also broadcasts)
            if not message.startswith('/'):
                # Format similar to server for consistency
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                self._log(f"[{timestamp}] You: {message}", 'self')
            
        except Exception as e:
            self._log(f"Send error: {e}", 'error')
            self._disconnect()
    
    def _receive_loop(self):
        """
        Continuously receive messages from the server.
        Runs in a separate thread.
        """
        while self.connected:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                
                if not data:
                    # Connection closed
                    self.message_queue.append(("Connection closed by server.", 'system'))
                    break
                
                message = data.decode('utf-8').strip()
                
                # Determine message type for coloring
                tag = None
                if '[WHISPER' in message:
                    tag = 'whisper'
                elif '[SYSTEM]' in message or '***' in message:
                    tag = 'system'
                
                self.message_queue.append((message, tag))
                
            except ConnectionResetError:
                self.message_queue.append(("Connection reset by server.", 'error'))
                break
            except OSError:
                # Socket closed
                break
            except Exception as e:
                if self.connected:
                    self.message_queue.append((f"Receive error: {e}", 'error'))
                break
        
        # Connection lost
        if self.connected:
            self.master.after(0, self._cleanup_connection)
    
    def _show_help(self):
        """
        Show help dialog.
        """
        help_text = """
Chat Commands:

/users              - List online users
/whisper <user> <msg> - Send private message
/help               - Show this help
/quit               - Disconnect

Simply type and press Enter to send messages to everyone.

Server Address Format:
- hostname:port (e.g., localhost:5000)
- IP:port (e.g., 127.0.0.1:5000)
"""
        messagebox.showinfo("Help", help_text)
    
    def on_closing(self):
        """
        Handle window close button.
        """
        if self.connected:
            self._disconnect()
        self.master.destroy()


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    # Allow command-line override of server
    global SERVER_HOST, SERVER_PORT
    if len(sys.argv) >= 2:
        SERVER_HOST = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            SERVER_PORT = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port: {sys.argv[2]}")
            sys.exit(1)
    
    # Create main window
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    print("Chat Client GUI starting...")
    print(f"Default server: {SERVER_HOST}:{SERVER_PORT}")
    
    # Start GUI event loop
    root.mainloop()


if __name__ == '__main__':
    main()
