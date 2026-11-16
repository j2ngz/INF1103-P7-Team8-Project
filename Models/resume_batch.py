
#All the ResumeData will be stored here temporarily until its passed to the LogicManager
class ResumeBatch:

    def __init__(self, items=None):
        #Store the resumes passed in (if any) from ResumeData. otherwise the batch starts empty
        self._items = list(items) if items else []

    def add(self, item):
        #add one ResumeData to the batch each time it's called
        self._items.append(item)

    @property
    def filenames(self):
        return [item.filename for item in self._items if item.filename]

    def is_empty(self):
        return not self._items

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)
