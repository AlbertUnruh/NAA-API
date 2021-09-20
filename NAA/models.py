from warnings import warn


__all__ = (
    "Node",
    "APIResponse",
    "APIRequest"
)


class Node:
    _children = dict()  # type: dict[str, "Node"]
    _clb = None  # type: callable
    _parent = None  # type: Node

    def __init__(self, *methods, ignore_invalid_methods=False):
        """
        Parameters
        ----------
        methods: str
        ignore_invalid_methods: bool
        """
        from .web import HTTP_METHODS
        u = str.upper

        methods = [u(m) for m in methods if u(m) in HTTP_METHODS]

        self._must_warn = not methods and not ignore_invalid_methods
        self._methods = methods
        self._checks_request = []  # type: list[tuple[callable, int]]

    def __call__(self, clb):
        """
        Parameters
        ----------
        clb: callable
            The function/method which should be a node.
        """
        self._clb = clb
        if self._must_warn:
            valid = ", ".join(__import__(f"{__package__}.web").HTTP_METHODS)
            warn(RuntimeWarning(
                f"You haven't set any (valid) methods for {self.path}! Valid methods are {valid}."))
        return self

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
            node._parent = self
            self._children[clb.__name__] = node
            node(clb)
            return node
        return decorator

    def add_request_check(self, default_return_value):
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
            self._checks_request.append((clb, default_return_value))
            return clb
        return decorator

    def run(self, request):
        """
        Parameters
        ----------
        request: APIRequest

        Returns
        -------
        APIResponse
        """
        for check, default in self._checks_request:
            if not check(request):
                return APIResponse(default)

        if request.method not in self._methods:
            return APIResponse(405)

        result = self._clb(request)
        if isinstance(result, APIResponse):
            return result
        if isinstance(result, tuple):
            return APIResponse(*result)
        return APIResponse(result)  # type: ignore

    def find_node(self, path, request):
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
        assert isinstance(request, APIRequest), \
            f"'request' must be an instance of APIRequest, not {request.__class__.__name__!r}"

        if path[0] in self._children:
            if len(path) == 1:
                return self._children[path[0]].run(request)
            else:
                return self._children[path[0]].find_node(path[1:], request)
        else:
            return APIResponse(404)

    @property
    def path(self):
        """
        Returns
        -------
        str
        """
        if self._parent is not None:
            return self._parent.path + "/" + self._clb.__name__
        return "/" + self._clb.__name__

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"name={self._clb.__name__!r} " \
               f"children={self._children!r}>"


class APIRequest:
    def __init__(self, method, headers):
        """
        Parameters
        ----------
        method: str
        headers: dict[str, str]
        """
        self._method = method
        self._headers = headers

    @property
    def method(self):
        """
        Returns
        -------
        str
        """
        return self._method

    @property
    def headers(self):
        """
        Returns
        -------

        """
        return self._headers

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"method={self._method!r} " \
               f"headers={self._headers!r}>"


class APIResponse:
    def __init__(self, status_code, response=None):
        """
        Parameters
        ----------
        status_code: int
        response: dict[str, str]
        """
        if isinstance(status_code, dict):
            response = status_code
            status_code = 200

        if response is None:
            response = {}

        assert isinstance(status_code, int), \
            f"'status_code' must be an instance of int, not {status_code.__class__.__name__!r}"
        assert isinstance(response, dict), \
            f"'response' must be an instance of dict, not {response.__class__.__name__!r}"

        self._status_code = status_code
        self._response = response

    @property
    def status_code(self):
        """
        Returns
        -------
        int
        """
        return self._status_code

    @property
    def response(self):
        """
        Returns
        -------
        dict[str, str]
        """
        return self._response

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"status_code={self._status_code!r} " \
               f"response={self._response!r}>"
