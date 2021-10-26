from warnings import warn

__all__ = (
    "Node",
    "APIResponse",
    "APIRequest"
)

_instance_error = "'{kwarg}' must be an instance of {expected}, not {received.__class__.__name__!r}"


class Node:
    _clb = None  # type: callable
    _parent = None  # type: Node

    def __init__(self, *methods, ignore_invalid_methods=False, used_libs=None):
        """
        Parameters
        ----------
        methods: str
        ignore_invalid_methods: bool,
        used_libs: list[str], optional
        """
        from .web import HTTP_METHODS
        u = str.upper

        methods = [u(m) for m in methods if u(m) in HTTP_METHODS]

        self._must_warn = not methods and not ignore_invalid_methods
        self._methods = methods
        self._checks_request = []  # type: list[tuple[callable, int]]
        self._checks_response = []  # type: list[callable]
        self._children = {}  # type: dict[str, "Node"]

        self._used_libs = used_libs or []

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
            node = Node(*methods, ignore_invalid_methods=ignore_invalid_methods, used_libs=self._used_libs)
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

    def add_response_check(self):
        """
        Can be used to edit responses before sending them.
        """
        def decorator(clb):
            """
            Parameters
            ----------
            clb: callable
            """
            self._checks_response.append(clb)
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
        if request.method not in self._methods:
            return APIResponse(405)

        for check, default in self._checks_request:
            if not check(request):
                return APIResponse(default)

        result = self._clb(request)
        auu = (None, {})

        # format from return from
        # AlbertUnruhUtils.ratelimit.server.ServerRateLimit.__call__.decorator()
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
            check(result)

        return result

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
            _instance_error.format(kwarg="request", expected="APIRequest", received=request)

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
    def __init__(self, method, headers, ip, url, version):
        """
        Parameters
        ----------
        method, ip, url, version: str
        headers: dict[str, str]
        """
        self._method = method
        self._headers = headers
        self._ip = ip
        self._url = url
        self._version = version

    @property
    def method(self):
        """
        Returns
        -------
        str
        """
        return self._method

    @property
    def ip(self):
        """
        Returns
        -------
        str
        """
        return self._ip

    @property
    def url(self):
        """
        Returns
        -------
        str
        """
        return self._url

    @property
    def version(self):
        """
        Returns
        -------
        str
        """
        return self._version

    @property
    def headers(self):
        """
        Returns
        -------

        """
        return self._headers

    def get(self, item, /, default=None):
        return self.headers.get(item, default)

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"method={self._method!r} " \
               f"headers={self._headers!r}>"


class APIResponse:
    __dict = type("dict", (dict,), {"__getitem__": lambda self, item: self.get(item, "")})
    DEFAULT_MESSAGES = __dict({  # copied from https://en.wikipedia.ord/wiki/List_of_HTTP_status_codes
        # 1xx  --  informational response
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        103: "Early Hints",

        # 2xx  --  success
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",

        # 3xx  --  redirection
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        306: "Switch Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",

        # 4xx  --  client errors
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        416: "Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        421: "Misdirected Request",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        425: "Too Early",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        452: "Unavailable For Legal Reasons",

        # 5xx  --  server errors
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        510: "Not Extended",
        511: "Network Authentication Required",
    })
    del __dict

    def __init__(self, status_code, response=None, message=None):
        """
        Parameters
        ----------
        status_code: int
        response: dict[str, str]
        message: str, optional

        Notes
        -----
        All parameters are type-checked, which means ``status_code`` can be
        ``response`` and 'll be ``200`` and if ``response`` is the ``message``
        it'll also be corrected.
        This is because the project for which this library originally was coded
        gets its data for this class by a return and if I want to send
        ``status_code=201, message="Entry Created"`` I just can return
        ``201, "Entry Created"`` and don't have to add an empty dictionary
        to the return.
        """
        if isinstance(response, str):
            message, response = response, {}

        if isinstance(status_code, dict):
            response, status_code = status_code, 200

        if response is None:
            response = {}

        assert isinstance(status_code, int), \
            _instance_error.format(kwarg="status_code", expected="int", received=status_code)
        assert isinstance(response, dict), \
            _instance_error.format(kwarg="response", expected="dict", received=response)

        message = response.pop("message", message)
        if message is None:
            message = self.DEFAULT_MESSAGES[status_code]

        assert isinstance(message, str), \
            _instance_error.format(kwarg="message", expected="str", received=message)

        self._status_code = status_code
        self._response = response
        self._message = message.title()

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

    @property
    def message(self):
        """
        Returns
        -------
        str
        """
        return self._message

    @message.setter
    def message(self, value):
        assert isinstance(value, str), \
            _instance_error.format(kwarg="message", expected="str", received=value)
        self._message = value.title()

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"status_code={self._status_code!r} " \
               f"response={self._response!r}>"
