import collections
import datetime

import edrlog

EDRLOG = edrlog.EDRLog()

class LRUCache(object):
    def __init__(self, max_size, max_age_seconds):
        self.capacity = max_size
        self.max_age = datetime.timedelta(seconds=max_age_seconds)
        self.cache = collections.OrderedDict()
    
    def _is_stale(self, entry):
        return (datetime.datetime.now() - entry["datetime"]) > self.max_age

    def values(self):
        return self.cache.values()

    def get(self, key):
        if self.capacity <= 0:
            return None

        try:
            self.cache[key] = self.cache.pop(key)
            entry = self.cache[key]
            if not self._is_stale(entry):
                return entry["content"]
            else:
                EDRLOG.log(u"Stale entry: {now}-{dt}>{mxa}, {content}".format(now=datetime.datetime.now(), dt=entry["datetime"], mxa=self.max_age, content=entry["content"]), "DEBUG")
        except KeyError:
            pass
        
        return None

    def set(self, key, value):
        if self.capacity <= 0:
            return

        try:
            self.cache.pop(key)
        except KeyError:
            pass

        while len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        
        self.cache[key] = { "datetime": datetime.datetime.now(), "content": value}

    def __delitem__(self, key):
        del self.cache[key]

