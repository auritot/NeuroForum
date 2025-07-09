from collections.abc import MutableMapping

class CustomSession(MutableMapping):
    def __init__(self, service, session_id=None, initial_data=None, expiry_seconds=3600):
        self.service = service
        self.session_id = session_id
        self._data = initial_data or {}
        self.modified = False
        self._expiry_seconds = expiry_seconds

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._data[key]
        self.modified = True

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def flush(self):
        """
        Clear the session entirely.
        """
        if self.session_id:
            self.service.delete(self.session_id)
        self.session_id = None
        self._data = {}
        self.modified = True

    def set_expiry(self, seconds):
        self._expiry_seconds = seconds
        self.modified = True

    def save(self):
        if not self.session_id:
            self.session_id = self.service.generate_session_id()
        self.service.save(
            self.session_id,
            self._data,
            expiry_minutes=self._expiry_seconds / 60
        )
        self.modified = False
