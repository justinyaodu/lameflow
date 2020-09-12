from collections.abc import MutableSequence

class ObservableList(MutableSequence):
    """A list which can be observed for mutations."""

    class Mutation:
        """A mutation to a list.

        Before the mutation:
            removed == list[index:len(removed)]

        After the mutation:
            added == list[index:len(added)]
        """

        def __init__(self, index, removed, added):
            self.index = index
            self.removed = removed
            self.added = added

        def __str__(self):
            return f"[{self.index}]: removed {self.removed}, added {self.added}"

    def __init__(self, iterable=[]):
        self._data = list(iterable)
        self.listeners = set()

    def _notify(self, *args):
        mutation = ObservableList.Mutation(*args)
        for listener in self.listeners:
            listener(mutation)

    def __repr__(self):
        return f"ObservableList({repr(self._data)})"

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def _index_normalize(self, i):
        """If i is negative, return the corresponding index relative to
        the end of the list. Otherwise, return i unchanged.
        """
        if i is None or i >= 0:
            return i
        else:
            return len(self) - i

    def _slice_indices(self, s):
        """Return the indices in a slice of this list.

        The algorithm is explained here:
        https://docs.python.org/3/library/stdtypes.html#common-sequence-operations
        """

        if s.step is None:
            k = 1
        elif s.step == 0:
            raise ValueError("Slice step must be a non-zero integer.")
        else:
            k = s.step

        i = self._index_normalize(s.start)
        j = self._index_normalize(s.stop)
        if k > 0:
            i = self._slice_lower(i)
            j = self._slice_upper(j)
        else:
            i = self._slice_upper(i, -1)
            j = self._slice_lower(j, -1)

        index = i
        indices = []
        if k > 0:
            while index < j:
                indices.append(index)
                index += k
        else:
            while index > j:
                indices.append(index)
                index += k
        return indices

    def _slice_lower(self, i, end_offset=0):
        if i is None:
            return 0 + end_offset
        else:
            return min(i, len(self) + end_offset)

    def _slice_upper(self, i, end_offset=0):
        if i is None:
            return len(self) + end_offset
        else:
            return min(i, len(self) + end_offset)

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            added = list(value)
            if not _is_extended_slice(key):
                removed = self._data[key]
                self._data[key] = added
                self._notify(key.start, removed, added)
            else:
                indices = self._slice_indices(key)
                if len(indices) != len(added):
                    msg = (f"Cannot assign {len(added)} elements to extended "
                            "slice with {len(indices)} indices.")
                    raise ValueError(msg)
                for index, element in zip(indices, added):
                    self[index] = element
        else:
            key = int(key)
            if key < 0:
                key = len(self) + key

            old_value = self[key]
            self._data[key] = value
            self._notify(key, [old_value], [value])

    def __delitem__(self, key):
        if isinstance(key, slice):
            if not _is_extended_slice(key):
                self[key] = []
            else:
                indices = self._slice_indices(key)

                # Remove elements in descending index order (to avoid
                # shifting elements before they are removed).
                if key.step > 0:
                    indices = reversed(indices)

                for index in indices:
                    del self[index]
        else:
            self[key:key] = []

    def insert(self, index, value):
        self[index:index] = [value]


def _is_extended_slice(s):
    """Return whether a slice is an extended slice."""

    return s.step is not None and s.step != 1
