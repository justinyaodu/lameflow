"""Nodes for constants, independent variables, and bound variables."""

__all__ = [
    "SingleAssignNode",
    "IndependentNode",
    "ConstNode",
    "VarNode",
    "FuncNode"
]

from .node import *


@nodeclass
class SingleAssignNode(Node):
    """A Node whose value can only be assigned once."""

    def invalidate(self):
        if self.state == Node.State.VALID:
            raise TypeError("Cannot invalidate the value of a "
                    f"{self.__class__.__name__}.")
        else:
            super().invalidate()


@nodeclass
class IndependentNode(Node):
    """A Node whose value is not dependent on other Nodes."""

    def __init__(self, value):
        super().__init__()
        self.value = value

        self.args.listeners.add(self._args_modified_error)
        self.kwargs.listeners.add(self._args_modified_error)

    def _args_modified_error(self, *args, **kwargs):
        raise TypeError("Cannot add arguments to a "
                f"{self.__class__.__name__}.")


@nodeclass
class ConstNode(IndependentNode, SingleAssignNode):
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

    def __str__(self):
        return f"{self.__class__.__name__}[{repr(self.lazy_value)}]"


@nodeclass
class VarNode(IndependentNode):
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
        before = (f"{self.__class__.__name__}"
                f"[{self.args[0].value.__qualname__}(")
        args = [str(arg) for arg in self.args[1:]]
        args.extend(f"{k}={v}" for k, v in self.kwargs.items())
        args = ", ".join(args)
        return before + args + ")]"
