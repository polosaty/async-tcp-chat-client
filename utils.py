from contextlib import contextmanager


@contextmanager
def closing(things):
    try:
        yield things
    finally:
        for thing in things:
            if callable(getattr(thing, 'close', None)):
                thing.close()


class ProtocolError(Exception):
    pass


class WrongToken(ProtocolError):
    pass
