import re

from . import constants as const

class Statistics:
    """Statistics: Stores statistical data for a single run of YCSB"""

    # Handle importing stats from kwargs
    def __init__(self, **kwargs):
        self.__stats = {}
        # Import values from given keyword arguments
        for k, v in kwargs.items():
            if k not in const.TRACKED_STATS:
                raise AttributeError("Unexpected keyword argument: '%s'. " % k +
                    "Valid arguments are ({})".format(','.join(const.TRACKED_STATS.keys())))
            setattr(self, k, v)
        # Add default values for missing stats
        for k, v in const.TRACKED_STATS.items():
            if k not in kwargs:
                setattr(self, k, v())

    # Get from __stats dict
    def __getattr__(self, name):
        if name in self.__stats:
            return self.__stats[name]
        raise AttributeError("'%s' does not exist" % name)

    # Store stats attributes in __stats dict
    def __setattr__(self, name, value):
        if name in const.TRACKED_STATS:
            # Ensure the type of the value matches what we expect
            if type(value) != type(const.TRACKED_STATS[name]()):
                raise TypeError("Type mismatch: '%s' should be '%s', but was '%s'" %
                    (name, type(const.TRACKED_STATS[name]()).__name__, type(value).__name__))
            self.__stats[name] = value
        else:
            object.__setattr__(self, name, value)

    def __getitem__(self, key):
        if key in self.__stats:
            return self.__stats[key]
        raise KeyError(key)

    def __str__(self):
        return str(dict(self.__stats))

    def __dir__(self):
        objdir = list(dir(super(Statistics, self)))
        objdir += list(self.__dict__.keys())
        objdir +=  list(self.__stats.keys())
        return objdir

    @property
    def anomaly_score(self):
        """anomaly_score
        Calculates the closed economy workload Simple Anomaly Score
        Returns None if S.A.S. can't be calculated from current data
        """
        if self.opcount > 0:
            return float(abs(self.totalcash - self.countcash) / self.opcount)
        return 0.

    def dict(self, *fields):
        """dict
        Returns a dictionary representing this Statistics object

        :param *fields: Names of fields to be included in the returned dictionary
        """
        try:
            return {field : getattr(self, field) for field in fields}
        except TypeError:
            raise TypeError("Statistics.dict(): field names must be strings")

class StatisticsSet:
    """StatisticsSet: Stores a set of Statistics objects.

    Averages can be accessed by prepending a Statistics field name with avg_
        e.g. statset.avg_anomaly_score
        or   statset.avg_opcount
    """
    # The type of data we're storing here
    STATS_TYPE = Statistics

    def __init__(self, *args):
        """__init__
        Instantiate this StatisticsSet with the given Statistics objects

        :param *args: Statistics instances to add to this StatisticsSet
        """
        # Mappings of magic prefixes to aggregation methods
        self.__MAGIC_ATTR_PREFIX_MAP = {
            "avg_": self.average,
            "sum_": self.sum,
        }
        self.__stats = []
        self.addstats(*args)

    def __getattr__(self, name):
        # Handle magic property prefixes
        for prefix, f in self.__MAGIC_ATTR_PREFIX_MAP.items():
            if name.startswith(prefix):
                name = re.sub(r'^' + prefix, "", name)
                return f(name)
        raise AttributeError("'%s' does not exist" % name)

    def __getitem__(self, key):
        """__getitem__
        Implements index operator [] to get store Statistics instances

        :param key: Index to retrieve (int), or name of an attribute (str)
        """
        if type(key) is int:
            try:
                return self.__stats[key]
            # Custom error string to avoid confusion and avoid leaking internal
            # implementation details
            except IndexError:
                raise IndexError("StatisticsSet index out of range")
        elif type(key) is str:
            try:
                return getattr(self, key)
            except AttributeError:
                raise KeyError(key)
        else:
            raise TypeError("key must be an integer or string")

    def __len__(self):
        """__len__
        Number of Statistics instances stored
        """
        return len(self.__stats)

    def __dir__(self):
        objdir = list(dir(super(StatisticsSet, self)))
        objdir += list(self.__dict__.keys())
        for prefix in self.__MAGIC_ATTR_PREFIX_MAP.keys():
            for stat in const.TRACKED_STATS.keys():
                objdir.append(prefix + stat)
        return objdir

    def addstats(self, *args):
        """addstats
        Add the given Statistics instances to this StatisticsSet instance

        Raises ValueError if parameters are not of type Statistics

        :param *args: Statistics instances to be added
        """
        for arg in args:
            if type(arg) != self.STATS_TYPE:
                raise ValueError("Can only store instances of %s class" %
                        self.STATS_TYPE.__name__)
            else:
                self.__stats.append(arg)

    def items(self):
        """items
        A list of Statistics instances stored in this StatisticsSet
        """
        return self.__stats

    def getfields(self, *fields):
        """getfields
        Returns an unsorted iterable of dicts containing values for the given
        fields.

        :param *fields: Names of fields from each Statistics object to be
        included in the returned output. These must be strings.
        """
        if len(fields) == 0:
            raise TypeError("StatisticsSet.getfields expected at least 1 argument, got 0")
        return list(map(lambda s: s.dict(*fields), self.items()))

    def average(self, field):
        """average
        Average of values stored in given field

        :param field: Field to average
        """
        stats = self.getvalues(field)
        if None in stats:
            return None
        return sum(stats) / len(stats)

    def sum(self, field):
        """sum
        Sum of values stored in given field

        :param field: Field to be summed
        """
        stats = self.getvalues(field)
        if None in stats:
            return None
        return sum(stats)

    def getvalues(self, field):
        """getvalues
        Get a list of all the values of the given field

        :param field: Field for which values should be retrieved
        """
        return [getattr(stat, field) for stat in self.__stats]
