import pickle
from base64 import b85decode, b85encode

import dill

__all__ = ['SerializeError', 'load_pickle', 'load_dill']


class SerializeError(RuntimeError):
    pass


def dump_pickle(obj, protocol=pickle.DEFAULT_PROTOCOL) -> str:
    try:
        return b85encode(pickle.dumps(obj, protocol=protocol)).decode()
    except Exception:
        raise SerializeError


def dump_dill(obj, protocol=dill.DEFAULT_PROTOCOL) -> str:
    try:
        return b85encode(dill.dumps(obj, protocol=protocol)).decode()
    except Exception:
        raise SerializeError


def load_pickle(obj: str):
    try:
        return pickle.loads(b85decode(obj.encode()))
    except Exception:
        raise SerializeError


def load_dill(obj: str):
    try:
        return dill.loads(b85decode(obj.encode()))
    except Exception:
        raise SerializeError


pickle_protocol = pickle.DEFAULT_PROTOCOL
dill_protocol = dill.DEFAULT_PROTOCOL
