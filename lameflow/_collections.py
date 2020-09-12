"""Collections classes with additional functionality."""

__all__ = ["ObservableList", "ObservableDict"]

from collections.abc import MutableSequence, MutableMapping


class _ObservableCollection:
    """A collection which can be observed for mutations."""

    def __init__(self, data):
        super().__init__()
        self._data = data
        self.listeners = set()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data})"

    def _notify(self, *args):
        mutation = self.__class__.Mutation(*args)
        for listener in self.listeners:
            listener(mutation)


class ObservableList(MutableSequence, _ObservableCollection):
    """A list which can be observed for mutations."""

    class Mutation:
        """A mutation to a list.

        Before the mutation:
            removed == obs_list[index:len(removed)]

        After the mutation:
            added == obs_list[index:len(added)]
        """

        def __init__(self, index, removed, added):
            self.index = index
            self.removed = removed
            self.added = added

        def __str__(self):
            return (f"index {self.index}: "
                    f"removed {self.removed}, added {self.added}")

    def __init__(self, iterable=[]):
        super().__init__(list(iterable))

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
                self._notify(key.start or 0, removed, added)
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

    def clear(self):
        del self[:]


def _is_extended_slice(s):
    """Return whether a slice is an extended slice."""

    return s.step is not None and s.step != 1


class ObservableDict(MutableMapping, _ObservableCollection):
    """A dict which can be observed for mutations."""

    class Mutation:
        """A mutation to a dict.

        Before the mutation:
            all(obs_dict[k] == v for k, v in removed.items())

        After the mutation:
            all(obs_dict[k] == v for k, v in added.items())
        """

        def __init__(self, removed, added):
            self.removed = removed
            self.added = added

        def __str__(self):
            return f"removed {self.removed}, added {self.added}"

    def __init__(self, *args, **kwargs):
        super().__init__(dict(*args, **kwargs))

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __setitem__(self, key, value):
        removed = {}
        try:
            removed[key] = self[key]
        except KeyError:
            pass

        self._data[key] = value
        self._notify(removed, {key: value})

    def __delitem__(self, key):
        removed = {key: self[key]}
        del self._data[key]
        self._notify(removed, {})
