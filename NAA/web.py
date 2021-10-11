from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from json import dumps

from .models import Node, APIRequest, APIResponse


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

    def __init__(self, *, host="127.0.0.1", port=3333, name=None, default=1, version_pattern="v{version}"):
        """
        Parameters
        ----------
        host: str
            The host of the server.
        port: int
            The port of the server.
        name: str, optional
            The name of the server.
        default: int
            The default version.
        version_pattern: str
            The pattern for the versions.
        """
        self._host = host
        self._port = port
        self._name = name or "NAA API"
        self._checks_request_global = {}  # type: dict[str, list[tuple[callable, int]]]
        self._checks_response_global = {}  # type: dict[str, list[callable]]
        self._versions = {}  # type: dict[str, Node]

        assert "{version}" in version_pattern, "'{version}' must be present in 'version_pattern'!"
        self._version_pattern = version_pattern
        self._version_default = self._version_pattern.format(version=default)

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

            request = APIRequest(
                method=request.method,
                headers=dict(request.headers),
                ip=request.remote_addr,
                url=path,
                version=version
            )

            for check, status in self._checks_request_global.get(version):
                if not check(request):
                    return Response(status=status,
                                    response={"message": APIResponse.DEFAULT_MESSAGES[status]},
                                    content_type="application/json")

            if not path:
                return Response(status=404,
                                response={"message": "No Path!"},
                                content_type="application/json")
                # todo: allow defaults

            path = path.split("/")
            result = self._versions[version].find_node(path=path, request=request)  # type: APIResponse

            for check in self._checks_response_global.get(version):
                check(result)

            status = result.status_code

            response = result.response
            response.update(message=result.message)
            response = dumps(response)

            return Response(status=status, response=response, content_type="application/json")

        self._application = application

    def add_version(self, version, *, fallback=None):
        """
        Parameters
        ----------
        version: int
        fallback: callable, optional
        """
        if fallback:
            self.add_version(version)(fallback)

        def decorator(clb):
            """
            Parameters
            ----------
            clb: callable
            """
            self._current_version = self._version_pattern.format(version=version)

            self._checks_request_global[self._current_version] = \
                self._checks_request_global.get(self._current_version, [])
            self._checks_response_global[self._current_version] = \
                self._checks_response_global.get(self._current_version, [])

            version_node = self._versions.get(self._current_version, Node(*HTTP_METHODS))  # type: Node
            node = Node(*HTTP_METHODS)(clb)
            node._children.update(version_node._children)  # noqa
            self._versions[self._current_version] = node
            clb(self)
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
            version = self._get_version()
            node = Node(*methods, ignore_invalid_methods=ignore_invalid_methods)
            node(clb)
            self._versions[version]._children[clb.__name__] = node  # noqa
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
            version = self._get_version()
            self._checks_request_global[version].append((clb, default_return_value))
            return clb
        return decorator

    def add_global_response_check(self):
        """
        Can be used to edit responses before sending them.
        """
        def decorator(clb):
            """
            Parameters
            ----------
            clb: callable
            """
            version = self._get_version()
            self._checks_response_global[version].append(clb)
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

    def _get_version(self):
        """
        Returns
        -------
        str

        Raises
        ------
        AssertionError
        """
        assert (version := self._current_version) is not None, \
            "You can only add an endpoint if you are in a version (API.add_version)"
        return version
