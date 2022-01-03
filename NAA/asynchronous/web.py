import asyncio
import typing

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from json import dumps

from .models import Node, APIRequest, APIResponse
from .. import web as sync_web


__all__ = (
    "API",
    "HTTP_METHODS",
    "ALLOWED_LIBS",
)


HTTP_METHODS = sync_web.HTTP_METHODS
ALLOWED_LIBS = sync_web.ALLOWED_LIBS


# just for type-hinting
_C_req = typing.Callable[["APIRequest"], typing.Awaitable[bool]]
_C_res = typing.Callable[["APIResponse"], typing.Awaitable[typing.NoReturn]]
_TC_req = typing.TypeVar("_TC_req", bound=_C_req)
_TC_res = typing.TypeVar("_TC_res", bound=_C_res)


async def _default_endpoint(*_):
    return APIResponse(404, {"message": "No Path!"})


class API(sync_web.API):
    _checks_request_global: dict[str, list[tuple[_C_req, int]]]
    _checks_response_global: dict[str, list[_C_res]]
    _versions: dict[str, Node]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_endpoint = _default_endpoint

    @Request.application
    def _application(self, request):
        """
        Parameters
        ----------
        request: Request
        """
        return asyncio.run(self._application_async(request))

    async def _application_async(self, request):
        """
        Parameters
        ----------
        request: Request

        Returns
        -------
        Response
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
            if not await check(request):
                return Response(
                    status=status,
                    response=dumps({"message": APIResponse.DEFAULT_MESSAGES[status]}),
                    content_type="application/json",
                )

        if not path:
            result = await self._default_endpoint(request)

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
            result = await self._versions[version].find_node(
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

    def add_global_request_check(
        self, default_return_value
    ) -> typing.Callable[[_TC_req], _TC_req]:
        """
        If the check returns False the `default_return_value`
        is returned and the request 'll not be processed.

        Parameters
        ----------
        default_return_value: int

        Returns
        -------
        typing.Callable[[_TC_req], _TC_req]
        """

        def decorator(clb: _TC_req) -> _TC_req:
            """
            Parameters
            ----------
            clb: _TC_req

            Returns
            -------
            _TC_req
            """
            version = self._get_version()
            self._checks_request_global[version].append((clb, default_return_value))
            return clb

        return decorator

    def add_global_response_check(
        self,
    ) -> typing.Callable[[_TC_res], _TC_res]:
        """
        Can be used to edit responses before sending them.

        Returns
        -------
        typing.Callable[[_TC_res], _TC_res]
        """

        def decorator(clb: _TC_res) -> _TC_res:
            """
            Parameters
            ----------
            clb: _TC_res

            Returns
            -------
            _TC_res
            """
            version = self._get_version()
            self._checks_response_global[version].append(clb)
            return clb

        return decorator

    def default_endpoint(
        self,
        clb: typing.Callable[[APIRequest], typing.Awaitable[APIResponse]],
    ) -> typing.Callable[[APIRequest], typing.Awaitable[APIResponse]]:
        """
        Adds a default endpoint. 'll be displayed if no path is given.

        Parameters
        ----------
        clb: typing.Callable[[APIRequest], typing.Awaitable[APIResponse]]
            The endpoint.

        Returns
        -------
        typing.Callable[[APIRequest], typing.Awaitable[APIResponse]]
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

    async def run_api(
        self,
        *,
        debug: bool = False,
        reload: bool = False,
        processes: int = 1,
    ):
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
