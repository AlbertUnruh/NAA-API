
__all__ = (
    "Node",
    "APIResponse",
    "APIRequest"
)


class Node:
    def __init__(self, clb):
        """
        Parameters
        ----------
        clb: callable
            The function/method which should be a node.
        """
        clb.__is_node__ = True
        self._clb = clb
        self._children = {}  # type: dict[str, Node]

    def run(self, request):
        """
        Parameters
        ----------
        request: APIRequest

        Returns
        -------
        APIResponse
        """
        result = self._clb(request)
        if isinstance(result, APIResponse):
            return result
        if isinstance(result, (int, dict)):
            return APIResponse(result)
        if isinstance(result, tuple):
            return APIResponse(*result)
        return APIResponse(result)

    __call__ = run

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
        node = self.__class__(clb)
        self._children[node._clb.__name__] = node
        return node

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
    def __init__(self, status_code, headers=None):
        """
        Parameters
        ----------
        status_code: int
        headers: dict[str, str]
        """
        if isinstance(status_code, dict):
            headers = status_code
            status_code = 200

        if headers is None:
            headers = {}

        assert isinstance(status_code, int), \
            f"'status_code' must be an instance of int, not {status_code.__class__.__name__!r}"
        assert isinstance(headers, dict), \
            f"'headers' must be an instance of dict, not {headers.__class__.__name__!r}"

        self._status_code = status_code
        self._headers = headers

    @property
    def status_code(self):
        """
        Returns
        -------
        int
        """
        return self._status_code

    @property
    def headers(self):
        """
        Returns
        -------
        dict[str, str]
        """
        return self._headers

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"status_code={self._status_code!r} " \
               f"headers={self._headers!r}>"
