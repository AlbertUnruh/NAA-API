from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from json import dumps

from .models import Node, APIRequest


__all__ = (
    "API",
    "HTTP_METHODS"
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
    _version_pattern = "v{version}"
    _version_default = None
    _current_version = None

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
        self._checks_request_global = {}  # type: dict[str, list[tuple[callable, int]]]
        self._versions = {}  # type: dict[str, callable]

        @Request.application
        def application(request):
            """
            Parameters
            ----------
            request: Request
            """
            path = request.path[1:]

            version = self._version_default
            p = path.split("/")
            if p:
                for v in self._versions:
                    if v == p[0]:
                        version = v
                        path = path[len(v)+1:]  # to get rid of the version in path
                        break
            del p

            for check, default in self._checks_request_global.get(version):
                if not check(request):
                    return Response(status=default)

            if not path:
                return Response(status=405)  # todo: allow defaults

            path = path.split("/")
            request = APIRequest(request.method, dict(request.headers))
            print(path)
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

    def setup(self, version_pattern="v{version}", default=None):
        """
        Parameters
        ----------
        version_pattern: str
        default: int, optional
        """
        assert "{version}" in version_pattern, "'{version}' must be present in 'version_pattern'!"
        self._version_pattern = version_pattern
        self._version_default = self._version_pattern.format(version=default)

    def add_version(self, version):
        """
        Parameters
        ----------
        version: int
        """
        def decorator(clb):
            """
            Parameters
            ----------
            clb: callable
            """
            self._current_version = self._version_pattern.format(version=version)
            self._checks_request_global[self._current_version] = []
            clb(self)
            self._versions[self._current_version] = clb
            self._current_version = None
            return clb
        return decorator

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
            version = self._current_version or self._version_default
            self._checks_request_global[version].append((clb, default_return_value))
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
        if self._versions and (default := self._version_default) is not None:
            if default not in self._versions:
                raise RuntimeError(f"Can't have {default!r} as default version, because this version is not set!")
        run_simple(self.host, self.port, self._application, use_reloader=reload, use_debugger=debug)

    __call__ = run_api
