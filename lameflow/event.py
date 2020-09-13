"""Allow observation of Node creation and modification."""

__all__ = ["NodeEvent", "NodeCreateEvent", "NodeStateEvent", "NodeValueEvent"]

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
        return super().__str__() + f": {self.old_state} -> {self.new_state}"


class NodeValueEvent(NodeEvent):
    """Fired when a Node's value changes."""

    def __init__(self, node, old_value, new_value):
        self.old_value = old_value
        self.new_value = new_value
        super().__init__(node)

    def __str__(self):
        return super().__str__() + f": {self.new_value}"
