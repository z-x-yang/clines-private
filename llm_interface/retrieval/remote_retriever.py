import logging
from multiprocessing.managers import BaseManager


class RemoteRetrieverProxy:
    """
    Thin proxy that talks to a RetrievalManager server (BaseManager) to reuse a
    single RetrieverCoordinator across concurrent notes/processes.
    Exposes the same embedding_retrieval_* methods used by EntityProcessor.
    """

    def __init__(self, server_addr: str, authkey: str = "retriever"):
        """
        Args:
            server_addr: "host:port" of the running retrieval_server.
            authkey: Auth key configured on the server (string).
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        host, port = self._parse_addr(server_addr)

        class _RetrieverManager(BaseManager):
            pass

        _RetrieverManager.register('get_retriever')

        self.manager = _RetrieverManager(address=(host, port), authkey=authkey.encode())
        self.manager.connect()
        self._proxy = self.manager.get_retriever()
        self.logger.info(f"Connected to remote retriever at {host}:{port}")

    def _parse_addr(self, server_addr: str) -> tuple[str, int]:
        if ':' not in server_addr:
            raise ValueError("server_addr must be in 'host:port' format")
        host, port_str = server_addr.rsplit(':', 1)
        return host, int(port_str)

    def embedding_retrieval_all(self, term, batch_size=256, top_k=1):
        return self._proxy.embedding_retrieval_all(term, batch_size, top_k)

    def embedding_retrieval_bodyloc(self, term, batch_size=256, top_k=1):
        return self._proxy.embedding_retrieval_bodyloc(term, batch_size, top_k)
