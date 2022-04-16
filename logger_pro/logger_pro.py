from dataclasses import dataclass, field
from datetime import datetime
from functools import update_wrapper, partial
from inspect import isclass, iscoroutinefunction, iscoroutine, isasyncgenfunction, isasyncgen
from io import TextIOBase
from os import makedirs
from os.path import abspath, dirname
from sys import stderr, setprofile, exc_info, version_info
from traceback import format_exception, format_stack
from types import FrameType, new_class
from typing import Union, Type, Callable

from .serialization import SerializeError, dump_dill, dump_pickle, dill_protocol, pickle_protocol

__all__ = ['Logger', 'global_buffer', 'InitTypeError', 'Buffer']


class _MyInt(int):
    name = ''

    def __new__(cls, name, x):
        obj = super().__new__(cls, x)
        return obj

    def __init__(self, name, _):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'{_MyStr(self.__class__.__qualname__) - self.__class__.__name__}{self.__str__()}'


class _MyStr(str):
    def __sub__(self, other):
        if not isinstance(other, str) or self[-len(other):] != other:
            raise TypeError(f'''unsupported operand type(s) for -: '{type(self)}' and '{type(other)}''')
        else:
            return self[:-len(other)]


class Buffer:
    def __init__(self):
        self.buffer = ''
        self._add = False

    def clear(self) -> None:
        self.buffer = ''
        self.is_add()

    def add(self, data: str) -> None:
        self.buffer += data
        self._add = True

    def get(self) -> str:
        return self.buffer

    def is_add(self) -> bool:
        r = self._add
        self._add = False
        return r


@dataclass(repr=False, eq=False)
class Logger:
    LogLevel = new_class('LogLevel', (_MyInt,))
    SerializeType = new_class('SerializeType', (_MyInt,))

    ERROR = LogLevel('ERROR', 3)
    WARNING = LogLevel('WARNING', 2)
    INFO = LogLevel('INFO', 1)
    DEBUG = LogLevel('DEBUG', 0)
    NO_LOG = LogLevel('NO_LOG', -1)

    NO_BIN = SerializeType('NO_BIN', 0)
    PICKLE = SerializeType('PICKLE', 1)
    DILL = SerializeType('DILL', 2)
    ONLY_DILL = SerializeType('ONLY_DILL', 3)

    default_serialize = DILL
    default_raise_error = ()
    default_ignore_error = (StopIteration, StopAsyncIteration)
    default_out_file = stderr
    default_logger_method = True
    default_pickle_protocol = pickle_protocol
    default_dill_protocol = dill_protocol

    level: LogLevel
    serialize: SerializeType = field(default_factory=lambda: Logger.default_serialize)
    raise_error: tuple[Type[BaseException]] = field(default_factory=lambda: Logger.default_raise_error)
    ignore_error: tuple[Type[BaseException]] = field(default_factory=lambda: Logger.default_ignore_error)
    out_file: Union[str, TextIOBase, Buffer] = field(default_factory=lambda: Logger.default_out_file)
    logger_method: bool = field(default_factory=lambda: Logger.default_logger_method)
    pickle_protocol: int = field(default_factory=lambda: Logger.default_pickle_protocol)
    dill_protocol: int = field(default_factory=lambda: Logger.default_dill_protocol)

    def __post_init__(self):
        if not isinstance(self.level, self.LogLevel):
            raise InitTypeError(f"Parameter 'level' must be an instance of 'Logger.LogLevel', not {type(self.level)}")

        if not (isinstance(self.raise_error, tuple) and
                all([issubclass(elem, BaseException) for elem in self.raise_error])):
            raise InitTypeError(f"Parameter 'raise_error' must be an instance of 'tuple of BaseException'")

        if not (isinstance(self.ignore_error, tuple) and
                all([issubclass(elem, BaseException) for elem in self.ignore_error])):
            raise InitTypeError(f"Parameter 'ignore_error' must be an instance of 'tuple of BaseException'")

        if not isinstance(self.out_file, (str, TextIOBase, Buffer)):
            raise InitTypeError(f"Parameter 'out_file' must be an instance of 'str' or 'TextIOBase'")
        if isinstance(self.out_file, str):
            try:
                file = filename(self.out_file)
                makedirs(dirname(file), exist_ok=True)
                open(file, mode='a', encoding='utf-8').close()
            except (OSError, TypeError, ValueError) as e:
                raise InitTypeError(f"Parameter 'out_file' must be point to a writable file ({e})")
        if isinstance(self.out_file, TextIOBase):
            if not self.out_file.writable():
                raise InitTypeError(f"Parameter 'out_file' must be a writable")

        if not isinstance(self.logger_method, bool):
            raise InitTypeError(f"Parameter 'logger_method' must be an instance of 'bool', "
                                f"not {type(self.logger_method)}")

    def __call__(self, func):
        if is_async(func):
            new_func = _AsyncLogger(func, self)
        else:
            new_func = _Logger(func, self)
        if self.logger_method and isclass(func):
            method_logger(self, new_func, func)
        return new_func


@dataclass(repr=False, eq=False)
class _Logger:
    class _Locals(dict):
        def __init__(self, parent: Logger):
            super().__init__()
            self.parent = parent

        def new(self, new) -> None:
            self.clear()
            self.update(new)

        def __str__(self) -> str:
            parent = self.parent
            if self.get('__getstate__', None) is not None and isinstance(self.get('__getstate__', None), list):
                try:
                    getstate = self['__getstate__']
                    serialize = {}
                    repr_str = {}
                    for key, value in self.items():
                        if key in getstate:
                            serialize[key] = value
                        else:
                            repr_str[key] = value
                except Exception:
                    repr_str = {}
                    serialize = dict(self)
            else:
                repr_str = {}
                serialize = dict(self)

            if parent.serialize == parent.ONLY_DILL:
                try:
                    return 'dill: ' + dump_dill(serialize, parent.dill_protocol) + self.repr_str(repr_str)
                except SerializeError:
                    return 'standard: ' + super().__str__()
            if parent.serialize >= parent.PICKLE:
                try:
                    return 'pickle: ' + dump_pickle(serialize, parent.pickle_protocol) + self.repr_str(repr_str)
                except SerializeError:
                    pass
            if parent.serialize >= parent.DILL:
                try:
                    return 'dill: ' + dump_dill(serialize, parent.dill_protocol) + self.repr_str(repr_str)
                except SerializeError:
                    pass
            return 'standard: ' + super().__str__()

        @staticmethod
        def repr_str(data: dict) -> str:
            if data != {}:
                return '+ standard: ' + data.__str__()
            return ''

    func: Callable
    parent: Logger

    def __post_init__(self):
        update_wrapper(self, self.func)
        self.level = self.parent.level
        self.logger_pro = True
        self.locals = self._Locals(self.parent)
        self.buffer = ''

    def __call__(self, *args, **kwargs):
        parent = self.parent
        if parent.level == parent.NO_LOG:
            return self.func(*args, **kwargs)

        has_print = False
        if parent.level <= parent.INFO:
            self.print(f'{self.func.__name__} start\n', end=True)
            has_print = True

        setprofile(self.tracer)
        result = 'Not successful finish'
        try:
            result = self.func(*args, **kwargs)
            setprofile(None)
        except parent.ignore_error:
            setprofile(None)
            raise
        except Exception as e:
            setprofile(None)
            self.print(e)
            has_print = True
            if isinstance(e, parent.raise_error):
                raise
        except BaseException as e:
            setprofile(None)
            if parent.level <= parent.WARNING:
                self.print(e)
                has_print = True
            raise
        else:
            setprofile(None)
        finally:
            if parent.level <= parent.INFO:
                self.print(f'''{self.func.__name__} stop
return: {result}''')
                has_print = True
            if parent.level <= parent.DEBUG:
                self.print(self.locals)
                has_print = True
            if has_print:
                self.print('\n', end=True, time=False)
        return result

    def tracer(self, frame: FrameType, event: str, _):
        if event == 'return':
            self.locals.new(frame.f_locals.copy())

    def __get__(self, instance, owner):
        p = partial(self, instance)
        p.__setattr__('logger_pro', self.logger_pro)
        return p

    def print(self, *values: Union[str, _Locals, BaseException], end: bool = False, time: bool = True) -> None:
        global global_buffer
        if time:
            self.buffer += timestamp() + ': '
        for value in values:
            if isinstance(value, BaseException):
                self.buffer += self.error_str(value)
            else:
                self.buffer += str(value) + '\n'
        if end:
            try:
                try_print(self.buffer, file=self.parent.out_file)
            except PrintError:
                self.buffer += '\n'
                global_buffer.add(self.buffer)
            self.buffer = ''

    @staticmethod
    def error_str(exception: Union[BaseException, Type[BaseException]]) -> str:
        if version_info.minor >= 10:
            err = format_exception(exception)
            st = format_stack()[3:-2]
            return ''.join([err[0]] + st + err[1:])
        else:
            st = format_exception(*exc_info())
            return ''.join(st)


class _AsyncLogger(_Logger):
    async def __call__(self, *args, **kwargs):
        parent = self.parent
        if parent.level == parent.NO_LOG:
            return await self.func(*args, **kwargs)

        has_print = False
        if parent.level <= parent.INFO:
            self.print(f'{self.func.__name__} start\n', end=True)
            has_print = True

        setprofile(self.tracer)
        result = 'Not successful finish'
        try:
            result = await self.func(*args, **kwargs)
            setprofile(None)
        except parent.ignore_error:
            setprofile(None)
            raise
        except Exception as e:
            setprofile(None)
            self.print(e)
            has_print = True
            if isinstance(e, parent.raise_error):
                raise
        except BaseException as e:
            setprofile(None)
            if parent.level <= parent.WARNING:
                self.print(e)
                has_print = True
            raise
        else:
            setprofile(None)
        finally:
            if parent.level <= parent.INFO:
                self.print(f'''{self.func.__name__} stop
return: {result}''')
                has_print = True
            if parent.level <= parent.DEBUG:
                self.print(self.locals)
                has_print = True
            if has_print:
                self.print('\n', end=True, time=False)
        return result


class PrintError(Exception):
    pass


class InitTypeError(TypeError):
    pass


def method_logger(parent: Logger, class_new, class_):
    for attr_name in dir(class_):
        attr = getattr(class_new, attr_name, None)
        if attr_name[:2] != '__' and callable(attr) and not getattr(attr, 'logger_pro', False) and not isclass(attr):
            setattr(class_new, attr_name, Logger(level=parent.level,
                                                 raise_error=parent.raise_error,
                                                 ignore_error=parent.ignore_error,
                                                 out_file=parent.out_file,
                                                 logger_method=parent.logger_method,
                                                 pickle_protocol=parent.pickle_protocol,
                                                 dill_protocol=parent.dill_protocol,
                                                 serialize=parent.serialize)(attr))


def is_async(func):
    return iscoroutinefunction(func) or iscoroutine(func) or isasyncgenfunction(func) or isasyncgen(func)


def try_print(*argv, file: Union[str, TextIOBase] = stderr, sep=' ', end='\n'):
    try:
        if isinstance(file, TextIOBase):
            print(*argv, sep=sep, end=end, file=file)
            file.flush()
        elif isinstance(file, Buffer):
            file.add(''.join([sep.join(argv), end]))
        else:
            file = filename(file)
            makedirs(dirname(file), exist_ok=True)
            with open(file, mode='a', encoding='utf-8') as f:
                print(*argv, sep=sep, end=end, file=f)
    except (OSError, TypeError, ValueError):
        print(f'logger-pro не смог записать в файл {file}', file=stderr)
        raise PrintError


def filename(file):
    return abspath(datetime.now().strftime(file))


def timestamp():
    return datetime.now().strftime('%H:%M:%S %d-%m-%Y')


global_buffer = Buffer()
