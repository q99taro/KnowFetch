import socket

# Hugging Face Spaces 的容器對外（特別是 api.telegram.org）的 IPv6 路由常常不通，
# 但 DNS 同時回傳 IPv4 (A) 與 IPv6 (AAAA) 紀錄。httpx/httpcore 若挑到 IPv6 位址，
# TLS 握手就會卡住直到 ConnectTimeout，造成「時好時壞」的隨機失敗。
# 解法：在程式啟動時全域強制 DNS 只解析 IPv4 (AF_INET)。

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


def force_ipv4() -> None:
    """全域強制所有 outbound 連線只走 IPv4，避免 HF Spaces 上 IPv6 路由不通造成的 ConnectTimeout。"""
    socket.getaddrinfo = _ipv4_only_getaddrinfo
