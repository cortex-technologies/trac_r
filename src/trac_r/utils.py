import socket

def local_network_ip() -> None:
    # Create a dummy socket to find the interface used for external routing
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # We use a public IP address (Google's DNS) and port.
        # No actual connection or packet is sent over the network.
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        # Fallback to loopback if no active network connection exists
        local_ip = "127.0.0.1"
    finally:
        s.close()
        print(f"Local Network IP Address: {local_ip}")