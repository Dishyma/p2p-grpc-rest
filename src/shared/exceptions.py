class P2PException(Exception):
    """Base exception for P2P system"""
    pass

class PeerNotFoundError(P2PException):
    pass

class FileNotFoundError(P2PException):
    pass

class TransferError(P2PException):
    pass