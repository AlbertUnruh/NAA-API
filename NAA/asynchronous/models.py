import typing

from .. import models as sync_models


__all__ = (
    "Node",
    "APIResponse",
    "APIRequest",
)


_instance_error = sync_models._instance_error  # noqa


# just for type-hinting
_C_req = typing.Callable[["APIRequest"], typing.Awaitable[bool]]
_C_res = typing.Callable[["APIResponse"], typing.Awaitable[typing.NoReturn]]
_TC_req = typing.TypeVar("_TC_req", bound=_C_req)
_TC_res = typing.TypeVar("_TC_res", bound=_C_res)


class Node(sync_models.Node):
    _clb: typing.Callable[[...], typing.Coroutine]
    _parent: "Node"

    _checks_request: list[tuple[_C_req, int]]
    _checks_response: list[_C_res]
    _children: dict[str, "Node"]

    def add_request_check(
        self,
        default_return_value: int,
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
            self._checks_request.append((clb, default_return_value))
            return clb

        return decorator

    def add_response_check(self) -> typing.Callable[[_TC_res], _TC_res]:
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
            self._checks_response.append(clb)
            return clb

        return decorator

    async def run(
        self,
        request: "APIRequest",
    ) -> "APIResponse":
        """
        Parameters
        ----------
        request: APIRequest

        Returns
        -------
        APIResponse
        """
        if request.method not in self._methods:
            return APIResponse(405)

        for check, default in self._checks_request:
            if not await check(request):
                return APIResponse(default)

        result = await self._clb(request)
        auu = (None, {})

        # format from return from
        # AlbertUnruhUtils.asynchronous.ratelimit.server.ServerRateLimit.__call__.decorator()
        # Notes
        # -----
        # - decorator is in this case nested and not direct accessible
        # - library: https://github.com/AlbertUnruh/AlbertUnruhUtils.py
        if "AlbertUnruhUtils" in self._used_libs:
            auu, result = result
            if not auu[0]:
                result = 429

        if isinstance(result, tuple):
            result = APIResponse(*result)
        else:
            result = APIResponse(result)

        result._response.update(auu[1])  # noqa

        for check in self._checks_response:
            await check(result)

        return result

    async def find_node(
        self,
        path: list[str],
        request: "APIRequest",
    ) -> "APIResponse":
        """
        Parameters
        ----------
        path: list[str]
            The path to the next node.
        request: APIRequest

        Returns
        -------
        APIResponse
        """
        assert isinstance(request, APIRequest), _instance_error.format(
            kwarg="request", expected="APIRequest", received=request
        )

        if path[0] in self._children:
            if len(path) == 1:
                return await self._children[path[0]].run(request)
            else:
                return await self._children[path[0]].find_node(path[1:], request)
        else:
            return APIResponse(404)


# not in a class definition since nothing changes
APIRequest = sync_models.APIRequest
APIResponse = sync_models.APIResponse
