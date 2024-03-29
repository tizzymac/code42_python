from enum import Enum


class ServerProtocol(str, Enum):
    TCP = "TCP"
    UDP = "UDP"
    TLS_TCP = "TLS-TCP"

    def __iter__(self):
        return iter([self.TCP, self.UDP, self.TLS_TCP])
