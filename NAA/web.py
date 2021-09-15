from flask import Flask, request, Response

from .models import Node, APIRequest


__all__ = (
    "API",
)


HTTP_METHODS = [
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "OPTIONS",
    "TRACE",
    "PATCH"
]


class API:
    def __init__(self, host, port, *, name=None):
        """
        Parameters
        ----------
        host: str
            The host of the server.
        port: int
            The port of the server.
        name: str, optional
            The name of the server.
        """
        self._host = host
        self._port = port
        self._name = name or "NAA API"
        self._flask = Flask(self._name)

        @self._flask.route("/", methods=None)
        @self._flask.route("/<path:path>", methods=None)
        def base(path=None):
            """
            Parameters
            ----------
            path:
            """
            if path is None:
                return Response(status=123)
            result = self._node.find_node(path.split("/"), APIRequest(request.method, dict(request.headers)))
            return Response(status=result.status_code, headers=result.headers)

        self._node = Node(base)

    def add(self, clb):
        """
        Parameters
        ----------
        clb: callable
            The function/method which should be added as a node.

        Returns
        -------
        Node
            The new node.
        """
        node = Node(clb)
        self._node._children[clb.__name__] = node  # noqa
        return node

    @property
    def host(self):
        """
        Returns
        -------
        str
        """
        return self._host

    @property
    def port(self):
        """
        Returns
        -------
        int
        """
        return self._port

    def run_api(self, *, debug=True):
        """
        Parameters
        ----------
        debug: bool
            Whether it should debug.
        """
        self._flask.run(self._host, self._port, debug)

    __call__ = run_api
