"""
Supply function to help solving net problem
"""
import socket


def get_host_ip():
    """
    Get the Ip address of the host
    :return: ip
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip
