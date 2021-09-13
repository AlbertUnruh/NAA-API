
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

    def __call__(self, *args, **kwargs):
        return self._clb(*args, **kwargs)

    def run(self, *args, **kwargs):
        """Just `self.__call__`"""
        return self(*args, **kwargs)

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
        self._children[node.__name__] = node
        return node

    def find_node(self, path, *args, **kwargs):
        """
        Parameters
        ----------
        path: list[str]
            The path to the next node.
        args, kwargs: Any
            The arguments for the last node in :param:`path`.
        """
        if path[0] in self._children:
            if len(path) == 1:
                return self._children[path[0]].run(*args, **kwargs)
            else:
                return self._children[path[0]].find_node(path[1:], *args, **kwargs)
        else:
            return 404

    def __repr__(self):
        return f"<{self.__class__.__name__}: " \
               f"name={self._clb.__name__} " \
               f"children={self._children}>"
