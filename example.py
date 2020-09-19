import functools
import operator
import os
import subprocess
import sys
import tempfile
import time

from lameflow import *
from lameflow.graphviz import dot_source


@nodeclass
class FibNode(SingleAssignNode):
    """Compute the nth Fibonacci number."""

    def __init__(self, n):
        if not isinstance(n, int) or n < 0:
            raise ValueError(f"Expected positive integer, got {n}.")

        self.name = str(f"Fib({n})")

        if n <= 1:
            super().__init__()
            self.value = n
        else:
            super().__init__(FibNode(n - 1), FibNode(n - 2))

    _instance_count = 0

    def key(self, *args, **kwargs):
        # Use original implementation for memoization.
        return super().key(*args, **kwargs)

        # Use this to disable memoization.
        # FibNode._instance_count += 1
        # return FibNode._instance_count

    def compute_value(self, a, b):
        return a.value + b.value


def fibonacci(n):
    return FibNode(n).value


def quadratic_roots(a, b, c):
    a = VarNode(a, __name="a")
    b = VarNode(b, __name="b")
    c = VarNode(c, __name="c")

    neg_b = MulNode(ConstNode(-1), b, __name=f"-{b.name}")

    four_a_c = MulNode(ConstNode(4), a, c, __name="4ac")

    b_squared = MulNode(b, b, __name="b^2")

    discriminant = SubNode(
            b_squared,
            four_a_c,
            __name=(b_squared.name + " - " + four_a_c.name))

    sqrt_discriminant = PowNode(discriminant, ConstNode(0.5),
            __name=f"sqrt({discriminant.name})")

    denominator = MulNode(ConstNode(2), a, __name="2a")

    first_root = DivNode(
            AddNode(neg_b, sqrt_discriminant),
            denominator,
            __name="first root")

    second_root = DivNode(
            AddNode(neg_b, MulNode(ConstNode(-1), sqrt_discriminant)),
            denominator,
            __name="second root")

    return first_root.value, second_root.value


file_number = 0

def save_svg(event):
    global file_number

    if isinstance(event, (NodeValueEvent, NodeCallStackEvent)):
        return

    file_number += 1

    with open(f"{file_number:04}.svg", "w") as svg:
        subprocess.run(["dot", "-Tsvg"],
                text=True, input=dot_source(), stdout=svg)


if __name__ == "__main__":
    #NodeEvent.listeners.add(lambda e: print(e, file=sys.stderr))

    #NodeEvent.listeners.add(lambda event: save_svg(event))
    #quadratic_roots(1, 1, -2)

    fibonacci(7)
    save_svg(None)
