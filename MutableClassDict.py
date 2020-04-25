from collections.abc import MutableMapping

# taken from:  https://stackoverflow.com/questions/21361106/how-would-i-implement-a-dict-with-abstract-base-classes-in-python
# You should copy this file somewhere into your source directory (it will search automatically),
# to help with the argparse conversion.
# The argparse parser and parse_args() will be converted to specifying props of this class.

class MutableClassDict(MutableMapping):
    '''
    Mapping that works like both a dict and a mutable object, i.e.
    d = MutableClassDict(foo='bar')
    and
    d.foo returns 'bar'
    '''
    # ``__init__`` method required to create instance from class.
    def __init__(self, *args, **kwargs):
        '''Use the object dict'''
        self.__dict__.update(*args, **kwargs)
    # The next five methods are requirements of the ABC.
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    def __getitem__(self, key):
        return self.__dict__[key]
    def __delitem__(self, key):
        del self.__dict__[key]
    def __iter__(self):
        return iter(self.__dict__)
    def __len__(self):
        return len(self.__dict__)
    # The final two methods aren't required, but nice for demo purposes:
    def __str__(self):
        '''returns simple dict representation of the mapping'''
        return str(self.__dict__)
    def __repr__(self):
        '''echoes class, id, & reproducible representation in the REPL'''
        return '{}, D({})'.format(super().__repr__(), self.__dict__)

if __name__ == '__main__':
  aa = MutableClassDict()
  aa.learn_rate = 0.001
  aa.arch = 'ResNet'
  print(str(aa))
  bb = aa.__dict__
  print(str(bb))
