"""Represent expressions and objects as Nodes."""

from enum import Enum
import itertools
from typing import NamedTuple

from ._collections import ObservableList, ObservableDict


class Node(_NodeSuperclass, new_key_space=True, same_key_error=False):
    """Represent a node in the data flow graph."""

    class State(Enum):
        """Whether a Node is invalidated, recalculating, or valid."""
        INVALID = 0
        PENDING = 1
        VALID = 2

    _by_key = {}
    """Index all Node instances by their keys."""

    def __new__(new_class, key_data):
        key = NodeKey(new_class._key_space, key_data)
        existing = Node._by_key.get(key)
        if existing is None:
            instance = super().__new__(new_class)
            instance.key = key
            Node._by_key[key] = instance
            return instance
        elif existing.__class__._same_key_error:
            raise SameKeyError(key_data, existing.__class__, new_class)
        else:
            return existing

    def _on_arg_add(node):
        self.invalidate()
        try:
            self._arg_refcount[node] += 1
        except KeyError:
            node._dependents.add(self)
            self._arg_refcount[node] = 1

    def _on_arg_remove(node):
        self.invalidate()
        self._arg_refcount[node] -= 1
        if self._arg_refcount[node] == 0:
            del self._arg_refcount[node]
            node._dependents.remove(self)

    def _on_args_changed(mutation):
        for node in mutation.added:
            self._on_arg_add(node)
        for node in mutation.removed:
            self._on_arg_remove(node)

    def _on_kwargs_changed(mutation):
        for node in mutation.added.values():
            self._on_arg_add(node)
        for node in mutation.removed.values():
            self._on_arg_remove(node)

    def __init__(self, key_data):
        # Key is assigned in __new__.

        self.state = Node.State.INVALID

        # Nodes passed as keyword and positional arguments to
        # compute_value.
        self.args = ObservableList()
        self.kwargs = ObservableDict()

        self.args.listeners.add(self._on_args_changed)
        self.kwargs.listeners.add(self._on_kwargs_changed)

        # Map Nodes to the number of times they appear in this Node's
        # arguments.
        self._arg_refcount = {}

        # Nodes whose values depend on this Node.
        self._dependents = set()

    def invalidate(self):
        """Indicate that the value of this Node is no longer valid."""

        if self.state == Node.State.VALID:
            self.state = Node.State.INVALID
            for dependent in self._dependents:
                dependent.invalidate()

    def compute_value(self, *args, **kwargs):
        """Compute this Node's value from the values of parent Nodes.

        Subclasses should override this method to do something useful.
        """

        return None

    def _compute_value(self):
        """Set this node's value using compute_value."""

        self.value = self.compute_value(*self.args, **self.kwargs)

    @property
    def value(self):
        """Get the value of this Node, recomputing it if necessary."""

        if self.state == Node.State.VALID:
            return self._value
        elif self.state == Node.State.INVALID:
            try:
                self._compute_value()
                return self._value
            except DependencyCycleError as e:
                e.trace.append(self)
                raise
        else:
            # Tried to get this Node's value while recomputing this Node.
            raise DependencyCycleError(self)

    @value.setter
    def value(self, new_value):
        self.state = Node.State.VALID
        self._value = new_value


class _NodeSuperclass:
    """Dummy superclass allowing the Node class to use the functionality
    in __init_subclass__.
    """

    def __init_subclass__(cls, /, new_key_space=None, same_key_error=None,
            **kwargs):
        """Customize Node subclass behavior.

        Nodes in different key spaces will always compare unequal. If
        new_key_space is True, a new key space will be created for this
        class and its subclasses (recursively).

        If new_key_space is False, instances of this class (including
        subclasses) will share the same key space.

        The value of same_key_error determines what happens when
        attempting to create a Node with the same key as an existing
        Node. If same_key_error is True, then a SameKeyError will be
        raised; this can be used to ensure that only one Node has access
        to an exclusive resource, for example.

        If same_key_error is False, then the existing Node is returned
        instead of creating a new Node. This can be used for memoizing
        the result of a computation.

        If new_key_space or same_key_error are not specified, the value
        of the superclass will be used.
        """

        super().__init_subclass__(**kwargs)
        if new_key_space is not None:
            cls._new_key_space = new_key_space
        if cls._new_key_space:
            cls._key_space = cls
        if same_key_error is not None:
            cls._same_key_error = same_key_error


class NodeKey(NamedTuple):
    """Uniquely identify a Node using its key space and key data."""

    key_space: type
    data: object

    def __str__(self):
        return f"{self.key_space.__name__}:{self.data}"


class DependencyCycleError(Exception):
    """Raised when a dependency cycle is detected."""

    def __init__(self, node):
        super().__init__("Dependency cycle detected.")
        self.trace = [node]

    def cycle(self):
        """Return the Nodes which make up the cycle."""

        seen = set()
        for node, i in zip(self.trace, itertools.count()):
            if node in seen:
                return self.trace[:i]
            else:
                seen.add(node)


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
