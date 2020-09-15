"""Allow observation of Node creation and modification."""

__all__ = [
    "NodeEvent",
    "NodeCreateEvent",
    "NodeStateEvent",
    "NodeValueEvent",
    "NodeArgEvent",
    "NodeArgAddEvent",
    "NodeArgRemoveEvent",
    "NodeCallStackEvent",
    "NodeCallStackPushEvent",
    "NodeCallStackPopEvent",
]

class NodeEvent:
    """Represent a change that occurred to a Node (for logging)."""

    listeners = set()

    def __init__(self, node):
        self.node = node

        for listener in NodeEvent.listeners:
            listener(self)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.node}"


class NodeCreateEvent(NodeEvent):
    """Fired when a new Node is created."""

    def __init__(self, node):
        super().__init__(node)


class NodeStateEvent(NodeEvent):
    """Fired when a Node's state changes."""

    def __init__(self, node, old_state, new_state):
        self.old_state = old_state
        self.new_state = new_state
        super().__init__(node)

    def __str__(self):
        return (super().__str__()
                + f": {self.old_state.name} -> {self.new_state.name}")


class NodeValueEvent(NodeEvent):
    """Fired when a Node's value changes."""

    def __init__(self, node, old_value, new_value):
        self.old_value = old_value
        self.new_value = new_value
        super().__init__(node)

    def __str__(self):
        return super().__str__() + f": {self.new_value}"


class NodeArgEvent(NodeEvent):
    """Fired when a Node's arguments are added or removed."""

    def __init__(self, node, arg):
        self.arg = arg
        super().__init__(node)


class NodeArgAddEvent(NodeArgEvent):
    pass


class NodeArgRemoveEvent(NodeArgEvent):
    pass


class NodeCallStackEvent(NodeEvent):
    """Fired when the Node call stack is modified."""


class NodeCallStackPushEvent(NodeCallStackEvent):
    pass


class NodeCallStackPopEvent(NodeCallStackEvent):
    pass
