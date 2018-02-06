_TYPEDICT = '_typedict'


def is_sequence(seq):
    """True if the argument is a sequence, but not a string type."""
    return hasattr(seq, '__iter__') and not isinstance(seq, str)



class record(object):
    """A record with typechecking.

    record(k1=v1, k2=v2, ...) -> initialise the record with the possible
        keys and values (or value types)

    The keys are checked when getting and setting values.
    When setting a value, the type is also checked.
    """

    def __init__(self, **kw):
        typedict = self.__dict__[_TYPEDICT] = {}
        for key, value in list(kw.items()):
            if isinstance(value, type):
                typedict[key] = value
            else:
                typedict[key] = type(value)
                setattr(self, key, value)

    def asdict(self, recursive=False):
        """Return a dict consisting of the keys and values."""
        if not recursive:
            return dict((key, self.__dict__[key])
                        for key in self.__dict__[_TYPEDICT]
                        if key in self.__dict__)
        else:
            tmp = dict((key, self.__dict__[key])
                       for key in self.__dict__[_TYPEDICT]
                       if key in self.__dict__)
            for key, val in tmp.items():
                if isinstance(val, record):
                    tmp[key] = val.asdict(True)
                elif str(type(val)) == "<class 'trindikit.enum.<locals>.Enum'>":
                    tmp[key] = str(val)
                elif isinstance(val, stack):
                    tmp[key] = val.aslist()
                elif isinstance(val, set):
                    tmp[key] = list(val)
                else:
                    raise Exception("No type I know of")
            return tmp

    def _typecheck(self, key, value=None):
        typedict = self.__dict__[_TYPEDICT]
        try:
            keytype = typedict[key]
            if value is None or isinstance(value, keytype):
                return
            else:
                raise TypeError("%s is not an instance of %s" % (value, keytype))
        except KeyError:
            keys = ", ".join(list(typedict.keys()))
            raise KeyError("%s is not among the possible keys: %s" % (key, keys))

    def __getattr__(self, key):
        """r.__getattr__('key') <==> r.key

        The key must be one of the keys that was used at creation.
        """
        self._typecheck(key)
        return self.__dict__[key]

    def __setattr__(self, key, value):
        """r.__setattr__('key', value) <==> r.key = value

        The key must be one of the keys that was used at creation.
        The value must be of the type that was used at creation.
        """
        self._typecheck(key, value)
        self.__dict__[key] = value

    def __delattr__(self, key):
        """r.__delattr__('key') <==> del r.key

        The key must be one of the keys that was used at creation.
        """
        self._typecheck(key)
        del self.__dict__[key]

    def pprint(self, prefix="", indent="    "):
        """Pretty-print a record to standard output."""
        print(self.pformat(prefix, indent))  # NICHT abhängig von verbose, sind nur IS und MVIS

    def pformat(self, prefix="", indent="    "):
        """Pretty-format a record, i.e., return a pretty-printed string."""
        result = ""
        for key, value in list(self.asdict().items()):
            if result: result += '\n'
            result += prefix + key + ': '
            if isinstance(value, record):
                result += '\n' + value.pformat(prefix + indent, indent)
            else:
                result += str(value)
        return result

    def __str__(self):
        return "{" + "; ".join("%s = %s" % kv for kv in list(self.asdict().items())) + "}"

    def __repr__(self):
        return "record(" + "; ".join("%s = %r" % kv for kv in list(self.asdict().items())) + ")"


class stack(object):
    """Stacks with (optional) typechecking.

    stack() -> new stack
    stack(type) -> new stack with elements of type 'type'
    stack(sequence) -> new stack initialised from sequence's items,
        where all items have to be of the same type

    If a type/class is given as argument when creating the stack,
    all stack operations will be typechecked.
    """

    def __init__(self, elements=None, fixedType=False):
        self.elements = []
        self._type = object
        if elements is None:
            pass
        elif isinstance(elements, type):
            self._type = elements
        elif is_sequence(elements):
            self.elements = list(elements)
            if len(self.elements) > 0:
                if fixedType:
                    self._type = fixedType
                else:
                    self._type = type(self.elements[0])
                self._typecheck(*self.elements)
        else:
            raise ValueError("The argument (%s) should be a type or a sequence" % elements)

    def top(self):
        """Return the topmost element in a stack.

        If the stack is empty, raise StopIteration instead of IndexError.
        This means that the method can be used in preconditions for update rules.
        """
        if len(self.elements) == 0:
            raise StopIteration
        return self.elements[-1]

    def pop(self):
        """Pop the topmost value in a stack.

        If the stack is empty, raise StopIteration instead of IndexError.
        This means that the method can be used in preconditions for update rules.
        """
        if len(self.elements) == 0:
            raise StopIteration
        return self.elements.pop()

    def push(self, value):
        """Push a value onto the stack."""
        self._typecheck(value)
        self.elements.append(value)

    def clear(self):
        """Clear the stack from all values."""
        del self.elements[:]

    def __len__(self):
        return len(self.elements)

    def _typecheck(self, *values):
        if self._type is not None:
            for val in values:
                if not isinstance(val, self._type):
                    raise TypeError("%s is not an instance of %s" % (val, self._type))

    def __iter__(self):
        return self.elements.__iter__()

    def __str__(self):
        return "<[ " + ", ".join(map(str, reversed(self.elements))) + " <]"

    def __repr__(self):
        return "<stack with %s elements>" % len(self)

    def aslist(self):
        return self.elements


class stackset(stack):
    """A stack which also can be used as a set.

    See the documentation for stack on how to create stacksets.
    """

    def __contains__(self, value):
        """x.__contains__(y) <==> y in x"""
        return value in self.elements

    def push(self, value):
        """Push a value onto the stackset."""
        self._typecheck(value)
        try:
            self.elements.remove(value)
        except ValueError:
            pass
        self.elements.append(value)

    def __str__(self):
        return "<{ " + ", ".join(map(str, reversed(self.elements))) + " <}"

    def __repr__(self):
        return "<stackset with %s elements>" % len(self)


class tset(object):
    """Sets with (optional) typechecking.

    tset() -> new set
    tset(type) -> new set with elements of type 'type'
    tset(sequence) -> new set initialised from sequence's items,
        where all items have to be of the same type

    If a type/class is given as argument when creating the set,
    all set operations will be typechecked.
    """

    def __init__(self, elements=None):
        self.elements = set([])
        self._type = object
        if elements is None:
            pass
        elif isinstance(elements, type):
            self._type = elements
        elif is_sequence(elements):
            self.elements = set(elements)
            for elem in self.elements:
                self._type = type(elem)
                break
            self._typecheck(*self.elements)
        else:
            raise ValueError("The argument (%s) should be a type or a sequence" % elements)

    def __contains__(self, value):
        return value in self.elements

    def add(self, value):
        self._typecheck(value)
        self.elements.add(value)

    def clear(self):
        """Clear the set from all values."""
        self.elements.clear()

    def __len__(self):
        return len(self.elements)

    def _typecheck(self, *values):
        if self._type is not None:
            for val in values:
                if not isinstance(val, self._type):
                    raise TypeError("%s is not an instance of %s" % (val, self._type))

    def __str__(self):
        return "{" + ", ".join(map(str, reversed(self.elements))) + "}"

    def __repr__(self):
        return "<set with %s elements>" % len(self)


def enum(*names):
    """Creates an enumeration class.

    The class instances are stored as attributes to the class. Example:

    >>> Swallow = enum('African', 'European')
    >>> Swallow.African, Swallow.European
    (<Enum object: African>, <Enum object: European>)
    >>> Swallow.Thracian
    AttributeError: type object 'Enum' has no attribute 'Thracian'
    >>> help(Swallow)
    class Enum(__builtin__.object)
     |  Enumeration class consisting of the instances: African, European
     |  (...)
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |  African = <Enum object: African>
     |  European = <Enum object: European>
    """
    assert names, "Empty enums are not supported"
    slots = names + ('__name',)
    doc = "Enumeration class consisting of the instances: " + ", ".join(names)

    class Enum(object):
        __doc__ = doc
        __slots__ = slots

        def __repr__(self):
            return "<Enum object: %s>" % self.__name

        def __str__(self):
            return self.__name

        def __init__(self, name):
            self.__name = name

    for name in names:
        setattr(Enum, name, Enum(name))
    Enum.__new__ = None
    return Enum


# standard enumeration classes: speakers and program states

Speaker = enum('USR', 'SYS')

ProgramState = enum('RUN', 'QUIT')




from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///ObjectRelDB.sqlite', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

from sqlalchemy import Column, Integer, String

class IS(Base, record):
    __tablename__ = 'IS'


    id = Column(Integer, primary_key=True)






    def __repr__(self):
        return "<User(name='%s', fullname='%s', password='%s')>" % (self.name, self.fullname, self.password)







if __name__ == "__main__":
    # IS = record(private = record(agenda = stack(),
    #                              plan   = stack(),
    #                              bel    = set()),
    #             shared  = record(com    = set(),
    #                              qud    = stackset(),
    #                              lu     = record(speaker = Speaker,
    #                                              moves   = set())))