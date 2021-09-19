from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from json import dumps

from .models import Node, APIRequest


__all__ = (
    "API",
    "HTTP_METHODS"
)


HEADERS_TO_REMOVE = ("Content-Type", "Content-Length")
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
    def __init__(self, host="127.0.0.1", port=3333, *, name=None):
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
        self._checks_request_global = []  # type: list[tuple[callable, int]]

        @Request.application
        def application(request):
            """
            Parameters
            ----------
            request: Request
            """
            for check, default in self._checks_request_global:
                if not check(request):
                    return Response(status=default)

            if not (path := request.path[1:]):
                return Response(status=123)  # todo: allow defaults

            path = path.split("/")
            request = APIRequest(request.method, dict(request.headers))

            result = self._node.find_node(path=path, request=request)

            status = result.status_code
            if response := result.response:
                response = dumps(response)
            else:
                response = None

            return Response(status=status, response=response, content_type="application/json")

        self._node = Node(*HTTP_METHODS)
        self._node(application)
        self._application = application

    def add(self, *methods, ignore_invalid_methods=False):
        """
        Parameters
        ----------
        methods: str
        ignore_invalid_methods: bool
        """
        def decorator(clb):
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
            node = Node(*methods, ignore_invalid_methods=ignore_invalid_methods)
            node(clb)
            self._node._children[clb.__name__] = node  # noqa
            return node
        return decorator

    def add_global_request_check(self, default_return_value):
        """
        If the check returns False the `default_return_value`
        is returned and the request 'll not be processed.

        Parameters
        ----------
        default_return_value: int
        """
        def decorator(clb):
            """
            Parameters
            ----------
            clb: callable
            """
            self._checks_request_global.append((clb, default_return_value))
            return clb
        return decorator

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

    def run_api(self, *, debug=False, reload=False):
        """
        Parameters
        ----------
        debug, reload: bool
            Whether it should debug/reload.
        """
        run_simple(self.host, self.port, self._application, use_reloader=reload, use_debugger=debug)

    __call__ = run_api
