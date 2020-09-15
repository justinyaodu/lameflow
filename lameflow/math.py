"""Nodes which perform mathematical operations."""

__all__ = [
    "AddNode",
    "SubNode",
    "MulNode",
    "DivNode",
    "PowNode",
]

import functools
import itertools
import operator

from .node import *


@nodeclass
class AddNode(Node):
    """Compute the sum of the arguments."""

    def compute_value(self, *args):
        return functools.reduce(operator.add, (a.value for a in args))


@nodeclass
class SubNode(Node):
    """Compute the difference of the two arguments."""

    def compute_value(self, a, b):
        return a.value - b.value


@nodeclass
class MulNode(Node):
    """Compute the product of the arguments."""

    def compute_value(self, *args):
        return functools.reduce(operator.mul, (a.value for a in args))


@nodeclass
class DivNode(Node):
    """Compute the quotient of the two arguments."""

    def compute_value(self, a, b):
        return a.value / b.value


@nodeclass
class PowNode(Node):
    """Raise the first argument to the power of the second argument."""

    def compute_value(self, a, b):
        return a.value ** b.value
