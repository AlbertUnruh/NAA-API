import typing

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from json import dumps
from warnings import warn

from .models import Node, APIRequest, APIResponse


__all__ = (
    "API",
    "HTTP_METHODS",
    "ALLOWED_LIBS",
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
    "PATCH",
]

ALLOWED_LIBS = {
    "AlbertUnruhUtils": "https://github.com/AlbertUnruh/AlbertUnruhUtils.py",
}


def _default_endpoint(*_):
    return APIResponse(404, {"message": "No Path!"})


class API:
    _version_pattern = "v{version}"
    _version_default = None
    _current_version = None

    _checks_request_global: dict[str, list[tuple[callable, int]]]
    _checks_response_global: dict[str, list[callable]]
    _versions: dict[str, Node]

    def __init__(
        self,
        *,
        host="127.0.0.1",
        port=3333,
        name=None,
        default=1,
        version_pattern="v{version}",
        used_libs=None,
    ):
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
        used_libs: list[str], optional
            Additional used libraries to adapt the code to them.
        """
        self._host = host
        self._port = port
        self._name = name or "NAA API"
        self._checks_request_global = {}
        self._checks_response_global = {}
        self._versions = {}
        self._default_endpoint = _default_endpoint

        assert (
            "{version}" in version_pattern
        ), "'{version}' must be present in 'version_pattern'!"
        self._version_pattern = version_pattern
        self._version_default = self._version_pattern.format(version=default)

        if used_libs is None:
            used_libs = []
        assert all(lib in ALLOWED_LIBS for lib in used_libs), (
            f"You can only use supported libraries! You can use one of these: "
            f"{', '.join(f'{k} ({ALLOWED_LIBS[k]})' for k in ALLOWED_LIBS)}"
        )
        if len(used_libs):
            if len(used_libs) == 1:
                lib = used_libs[0]
                warn(RuntimeWarning(f"Used Library {lib} must be used everywhere!"))
            else:
                libs = ", ".join(used_libs[:-1]) + f" and {used_libs[-1]}"
                warn(RuntimeWarning(f"Used Libraries {libs} must be used everywhere!"))
        self._used_libs = used_libs

    @Request.application
    def _application(self, request):
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
                    # to get rid of the version in path
                    path = path[len(v) + 1 :]  # noqa: E203
                    break
        del p

        request = APIRequest(
            method=request.method,
            headers=dict(request.headers),
            ip=request.remote_addr,
            url=path,
            version=version,
        )

        for check, status in self._checks_request_global.get(version):
            if not check(request):
                return Response(
                    status=status,
                    response=dumps({"message": APIResponse.DEFAULT_MESSAGES[status]}),
                    content_type="application/json",
                )

        if not path:
            result = self._default_endpoint(request)

            # format result from
            # AlbertUnruhUtils.ratelimit.server.ServerRateLimit.__call__.decorator()
            # Notes
            # -----
            # - decorator is in this case nested and not direct accessible
            # - library: https://github.com/AlbertUnruh/AlbertUnruhUtils.py
            if "AlbertUnruhUtils" in self._used_libs:
                auu, result = result
                if not auu[0]:
                    result = APIResponse(429)
                result._response.update(auu[1])  # noqa

        else:
            path = path.split("/")
            result = self._versions[version].find_node(
                path=path, request=request
            )  # type: APIResponse

        for check in self._checks_response_global.get(version):
            check(result)

        status = result.status_code

        response = result.response
        response.update(message=result.message)
        response = dumps(response)

        return Response(
            status=status, response=response, content_type="application/json"
        )

    def add_version(self, version, *, fallback: list[callable] = None):
        """
        Parameters
        ----------
        version: int
        fallback: list[callable]
        """
        for fb in fallback or []:
            self.add_version(version)(fb)

        def decorator(clb):
            """
            Parameters
            ----------
            clb: callable
            """
            self._current_version = self._version_pattern.format(version=version)

            self._checks_request_global[
                self._current_version
            ] = self._checks_request_global.get(self._current_version, [])
            self._checks_response_global[
                self._current_version
            ] = self._checks_response_global.get(self._current_version, [])

            version_node = self._versions.get(
                self._current_version, Node(*HTTP_METHODS, used_libs=self._used_libs)
            )  # type: Node
            node = Node(*HTTP_METHODS, used_libs=self._used_libs)(clb)
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
            node = Node(
                *methods,
                ignore_invalid_methods=ignore_invalid_methods,
                used_libs=self._used_libs,
            )
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

    def default_endpoint(
        self,
        clb: typing.Callable[[APIRequest], APIResponse],
    ) -> typing.Callable[[APIRequest], APIResponse]:
        """
        Adds a default endpoint. 'll be displayed if no path is given.

        Parameters
        ----------
        clb: typing.Callable[[APIRequest], APIResponse]
            The endpoint.

        Returns
        -------
        typing.Callable[[APIRequest], APIResponse]
        """
        self._default_endpoint = clb
        return clb

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

    def run_api(self, *, debug=False, reload=False, processes=1):
        """
        Parameters
        ----------
        debug, reload: bool
            Whether it should debug/reload.
        processes: int
            The number of processes which can be used by the server.
        """
        if self._versions and (default := self._version_default) is not None:
            if default not in self._versions:
                raise RuntimeError(
                    f"Can't have {default!r} as default version, because this version is not set!"
                )
        run_simple(
            self.host,
            self.port,
            self._application,
            use_reloader=reload,
            use_debugger=debug,
            processes=processes,
        )

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
        assert (
            version := self._current_version
        ) is not None, (
            "You can only add an endpoint if you are in a version (API.add_version)"
        )
        return version
