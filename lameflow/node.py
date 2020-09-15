"""Define the Node class and node subclass decorator."""

__all__ = [
    "nodeclass",
    "Node",
    "NodeCallStack",
    "DependencyCycleError",
    "SameKeyError"
]

import enum
from typing import NamedTuple

from .event import *

from ._collections import FrozenDict, ObservableList, ObservableDict


def nodeclass(cls):
    """Decorator for Node subclasses.

    This decorator enables Node instances to be properly memoized by
    preventing multiple calls to __init__ when returning an existing
    instance.

    If this decorator is missing from a Node subclass, a TypeError will
    be raised at instantiation.
    """

    init = cls.__init__

    def init_wrapper(self, *args, **kwargs):
        if not hasattr(self, "_init_run_for_class"):
            self._init_run_for_class = set()
        if cls not in self._init_run_for_class:
            init(self, *args, **kwargs)
            self._init_run_for_class.add(cls)

    cls.__init__ = init_wrapper

    # Mark this class as decorated.
    del cls._node_decorator_missing_flag

    return cls


class _NodeSuperclass:
    """Dummy superclass allowing the Node class to use the functionality
    in __init_subclass__.
    """

    def __init_subclass__(cls, /, same_key_error=None, **kwargs):
        """Customize Node subclass behavior.

        The value of same_key_error determines what happens when
        attempting to create a Node with the same key as an existing
        Node. If same_key_error is True, then a SameKeyError will be
        raised; this can be used to ensure that only one Node has access
        to an exclusive resource, for example.

        If same_key_error is False, then the existing Node is returned
        instead of creating a new Node. This can be used for memoizing
        the result of a computation.

        If same_key_error is not specified, the behavior of the
        superclass will be used.
        """

        super().__init_subclass__(**kwargs)

        if same_key_error is not None:
            cls._same_key_error = same_key_error

        # Add a dummy attribute to be removed by the node decorator. The
        # presence of this attribute indicates that the subclass was not
        # decorated.
        cls._node_decorator_missing_flag = cls

    def __init__(self):
        super().__init__()

        try:
            subclass = self._node_decorator_missing_flag
            msg = (f"Node subclass '{subclass}' is missing the "
                    "@nodeclass decorator.")
            raise TypeError(msg)
        except AttributeError:
            pass


@nodeclass
class Node(_NodeSuperclass, same_key_error=False):
    """Represent a node in the data flow graph."""

    class State(enum.Enum):
        """Whether a Node is invalidated, recalculating, or valid."""
        INVALID = enum.auto()
        PENDING = enum.auto()
        VALID = enum.auto()

    _by_key = {}
    """Index all Node instances by their keys."""

    _trace = []
    """Stack trace of executing Nodes."""

    def __new__(new_class, *args, **kwargs):
        key = new_class.key(new_class, *args, **kwargs)
        existing = Node._by_key.get(key)
        if existing is None:
            instance = super().__new__(new_class)
            Node._by_key[key] = instance
            instance._init(key)
            return instance
        elif existing._same_key_error:
            raise SameKeyError(key, existing.__class__, new_class)
        else:
            return existing

    def __str__(self):
        return f"{self.__class__.__name__}[{self.key}]"

    def __hash__(self):
        if hasattr(self, "_hash"):
            return self._hash
        self._hash = hash(self.key)
        return self._hash

    def _on_arg_add(self, arg):
        self.invalidate()
        try:
            self._arg_refcount[arg] += 1
        except KeyError:
            arg._dependents.add(self)
            self._arg_refcount[arg] = 1
        NodeArgAddEvent(self, arg)

    def _on_arg_remove(self, arg):
        self.invalidate()
        self._arg_refcount[arg] -= 1
        if self._arg_refcount[arg] == 0:
            del self._arg_refcount[arg]
            arg._dependents.remove(self)
        NodeArgRemoveEvent(self, arg)

    def _on_args_changed(self, mutation):
        for arg in mutation.added:
            self._on_arg_add(arg)
        for arg in mutation.removed:
            self._on_arg_remove(arg)

    def _on_kwargs_changed(self, mutation):
        for arg in mutation.added.values():
            self._on_arg_add(arg)
        for arg in mutation.removed.values():
            self._on_arg_remove(arg)

    @staticmethod
    def key(cls, *args, **kwargs):
        """Return a hashable key unique to a Node instance.

        This static method is passed the class of the requested instance
        and the constructor arguments, just like __new__.

        If the returned key matches an existing Node instance, the
        existing instance will be returned (or a SameKeyError will be
        raised, depending on the class' value for same_key_error).
        Subclasses can override this method to customize how instance
        memoization (if any) is done.

        To avoid key collisions between Node subclasses, it is
        recommended to include the class of the Node instance as part of
        the key.
        """

        items = [cls]
        if args:
            items.append(tuple(args))
        if kwargs:
            items.append(FrozenDict(kwargs))
        return tuple(items)

    def _init(self, key):
        """Do some initialization after __new__ but before __init__."""

        self.key = key

        self._state = Node.State.INVALID
        self._value = None

        # Keyword and positional arguments to compute_value.
        self._args = ObservableList()
        self._kwargs = ObservableDict()

        self.args.listeners.add(self._on_args_changed)
        self.kwargs.listeners.add(self._on_kwargs_changed)

        # Map Nodes to the number of times they appear in this Node's
        # arguments.
        self._arg_refcount = {}

        # Nodes whose values depend on this Node.
        self._dependents = set()

        NodeCreateEvent(self)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        old_state = self._state
        self._state = new_state
        NodeStateEvent(self, old_state, new_state)

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, value):
        # Replace contents instead of replacing the attribute.
        self._args.clear()
        self._args.extend(value)

    @property
    def kwargs(self):
        return self._kwargs

    @kwargs.setter
    def kwargs(self, value):
        # Replace contents instead of replacing the attribute.
        self._kwargs.clear()
        self._kwargs.update(value)

    def invalidate(self):
        """Indicate that the value of this Node is no longer valid."""

        if self.state == Node.State.VALID:
            with _NodeStackFrame(self):
                self.state = Node.State.INVALID
                for dependent in self._dependents:
                    dependent.invalidate()

    def compute_value(self, *args, **kwargs):
        """Compute this Node's value from its parent Nodes.

        Subclasses should override this method to do something useful.
        """

        return None

    @property
    def value(self):
        """Get the value of this Node, recomputing it if necessary."""

        if self.state == Node.State.VALID:
            return self._value
        else:
            with _NodeStackFrame(self):
                self.state = Node.State.PENDING
                self.value = self.compute_value(*self.args, **self.kwargs)
                return self._value

    @value.setter
    def value(self, new_value):
        if self._value == new_value:
            return

        self.invalidate()

        old_value = self._value
        self._value = new_value
        NodeValueEvent(self, old_value, new_value)

        self.state = Node.State.VALID

    @property
    def lazy_value(self):
        """Return the value of this Node if it is valid, or None if it
        is invalid.
        """

        if self.state == Node.State.VALID:
            return self.value
        else:
            return None


class NodeCallStack:
    """Call stack for currently executing nodes."""

    stack = []
    _nodes = set()

    @classmethod
    def _push(cls, node):
        if node in cls._nodes:
            raise DependencyCycleError(cls.stack + [node])
        else:
            cls._nodes.add(node)
            cls.stack.append(node)

    @classmethod
    def _pop(cls, node):
        if not cls.stack:
            raise IndexError(f"Cannot pop '{node}' from empty call stack.")
        elif node != cls.stack[-1]:
            raise TypeError("super().__init__ not called for node "
                    f"{cls.stack[-1]}.")
        else:
            cls._nodes.remove(node)
            cls.stack.pop()


class _NodeStackFrame:
    """Context manager which creates a stack frame for the currently
    executing node and detects dependency cycles.
    """

    def __init__(self, node):
        self.node = node

    def __enter__(self):
        NodeCallStack._push(self.node)

    def __exit__(self, exc_type, exc_value, traceback):
        NodeCallStack._pop(self.node)


class DependencyCycleError(Exception):
    """Raised when a dependency cycle is detected."""

    def __init__(self, trace):
        super().__init__("Dependency cycle detected.")
        self.trace = trace


class SameKeyError(Exception):
    """Raised during Node instantiation if another Node exists with the
    same key and same_key_error is True.
    """

    def __init__(key_data, existing_class, new_class):
        self.key_data = key_data
        self.existing_class = existing_class
        self.new_class = new_class
        self.key_space = new_class._key_space

        msg = (f"{existing_class.__name__} with key data '{key_data}' "
                f"already exists in key space {self.key_space.__name__}; "
                f"cannot create {new_class.__name__} with the same key.")
        super().__init__(msg)
