"""Nodes for constants, independent variables, and bound variables."""

__all__ = [
    "ConstNode",
    "VarNode",
    "FuncNode"
]

from .node import *


@nodeclass
class _IndependentNode(Node):
    """A Node whose value is independent of other Nodes."""

    def __init__(self, value):
        super().__init__()
        self.value = value

    @Node.state.setter
    def state(self, value):
        if self.state != Node.State.VALID:
            Node.state.fset(self, value)


@nodeclass
class ConstNode(_IndependentNode):
    """A Node whose value is a hashable constant."""

    @Node.value.setter
    def value(self, new_value):
        # Allow the value to be changed exactly once, during __init__.
        try:
            if self.__initialized:
                raise TypeError("Cannot change the value of a ConstNode.")
        except AttributeError:
            Node.value.fset(self, new_value)
            self.__initialized = True

    def invalidate(self):
        # Constants cannot be invalidated.
        pass

    def __str__(self):
        return f"{self.__class__.__name__}[{repr(self.lazy_value)}]"


@nodeclass
class VarNode(_IndependentNode):
    """A Node whose value can be changed directly.

    VarNode instances are never memoized.
    """

    _instance_counter = -1

    def __str__(self):
        return f"{self.__class__.__name__}[{self.key[1]}]"

    @staticmethod
    def key(cls, *args, **kwargs):
        VarNode._instance_counter += 1
        return (cls, VarNode._instance_counter)


@nodeclass
class FuncNode(Node):
    """A Node whose value is bound to a function of other Node values.

    The constructor arguments should be Nodes representing the
    (positional and keyword) arguments to the function. The values
    of those nodes are passed to the provided function to compute this
    Node's value.
    """

    def __init__(self, func, *args, **kwargs):
        super().__init__(ConstNode(func), *args, **kwargs)

    def compute_value(self, func, *args, **kwargs):
        return func.value(*(n.value for n in args),
                **{k: n.value for k, n in kwargs.items()})

    def __str__(self):
        before = f"{self.__class__.__name__}[{self.args[0].value.__name__}("
        args = [str(arg) for arg in self.args[1:]]
        args.extend(f"{k}={v}" for k, v in self.kwargs.items())
        args = ", ".join(args)
        return before + args + ")]"
