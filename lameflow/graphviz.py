import itertools
import re
import textwrap

from .node import *
from .core import *


before = textwrap.dedent("""
    digraph G {
    node [shape=record style=filled]
    node [fontname=courier]
    edge [fontname=courier]
    graph [fontname=courier labelloc=t]""")

after = "}"


def dot_source(label=""):
    chunks = []
    nodes = [DotNode(n) for n in Node._by_key.values()]

    for node in nodes:
        chunks.append(node.definition)

    call_stack_adj = set(zip(NodeCallStack.stack, NodeCallStack.stack[1:]))
    for node in nodes:
        chunks.append(node.edges(call_stack_adj))

    return "\n".join([before, f'label = "{label}"', *chunks, after])


class DotNode:
    """Represent a node in a Graphviz DOT graph."""

    state_to_color = {
        Node.State.VALID: "#ddffdd",
        Node.State.PENDING: "#ffffdd",
        Node.State.INVALID: "#ffdddd",
    }

    @staticmethod
    def format_attrs(attrs):
        return "[" + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + "]"

    def __init__(self, node):
        self.node = node

    @property
    def definition(self):
        attrs = {}
        attrs["label"] = self.label
        attrs["fillcolor"] = DotNode.state_to_color[self.node.state]
        return f"{id(self.node)} {DotNode.format_attrs(attrs)}"

    @property
    def label(self):
        node = self.node
        rows = []

        args = []
        for arg_name in itertools.chain(range(len(node.args)), node.kwargs):
            args.append(f"<{arg_name}>{arg_name}")
        if args:
            rows.append("{" + "|".join(args) + "}")

        header = node.__class__.__name__
        if hasattr(node, "name"):
            header += f" {node.name}"
        rows.append(header)

        rows.append("<!>" + self.value_str)

        return "{" + "|".join(rows) + "}"

    @property
    def value_str(self):
        node = self.node
        if node.state != Node.State.VALID:
            s = node.state.name
        elif hasattr(node.value, "__qualname__"):
            s = node.value.__qualname__
        else:
            s = repr(node.value)
        return re.sub(r"([\\{}|<>]|\\n)", r"\\1", s)

    def edges(self, highlighted_pairs):
        node = self.node
        lines = []

        if (hasattr(node, "_created_by")
                and not node._created_by._arg_refcount.get(node)):
            # Creator node has not added this argument yet.
            lines.append(
                    f"{id(node)} -> {id(node._created_by)} [style=dashed]")

        for name, arg in itertools.chain(
                enumerate(node.args), node.kwargs.items()):
            line = f'{id(arg)}:"!":s -> {id(node)}:"{name}":n'
            if (node, arg) in highlighted_pairs:
                line += " [penwidth=4]"
            lines.append(line)

        return "\n".join(lines)
