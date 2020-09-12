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

    def _notify(mutation):
        for listener in self.listeners:
            listener(mutation)

    def __len__(self):
        return self._data.__len__()

    def __repr__(self):
        return f"ObservableList({repr(self._data)})"

    def __getitem__(self, index):
        return self._data.__getitem__(index)

    def _index_normalize(self, i):
        """If i is negative, return the corresponding index relative to
        the end of the list. Otherwise, return i unchanged.
        """
        if i is None or i >= 0:
            return i
        else:
            return len(self) - i

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

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            pass # TODO
        else:
            index = int(index)
            if index < 0:
                index = len(self) + index

            old_value = self[index]
            self._data[index] = value
            self._notify(ObservableList.Mutation(index, [old_value], [value]))
            


        if not isinstance(index, int):
            raise TypeError(f"Expected int, got {index.__class__.__name__}")

        if index < 0:
            index = len(self) + index

        old_value = NotImplemented
        try:
            old_value = self[index]
        except IndexError:
            pass

        self._data.__setitem__(index, value)

        for listener in self.listeners:
            listener(ObservableList.Mutation(index, old_value, value))

    def _set_item_single(self, index, value):
        """Set the item at a single index."""

        if index < 0:
            index = len(self) + index

        removed = self[index]

    def __delitem__(self, index):
        raise NotImplementedError

    def insert(self, index, value):
        raise NotImplementedError
