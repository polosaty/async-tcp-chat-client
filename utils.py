import asyncio
from contextlib import asynccontextmanager
import logging
import random
import time
from typing import Optional, Tuple

from consts import CONNECT_TIMEOUT


class Backoff:
    """
    Exponential backoff with jitter
    """

    def __init__(self, base=2, factor=1, max_wait=None, jitter=None, min_time_for_reset=None, logger=None):
        self.base = base
        self.factor = factor
        self.max_wait = max_wait
        self._jitter = jitter
        self._retries = 0
        self.min_time_for_reset = min_time_for_reset
        self.logger = logger or logging.getLogger('backoff')

    def reset(self):
        self._retries = 0

    def add_jitter(self, wait_time):
        if self._jitter is None:
            return wait_time

        jitter = max(wait_time / 2, self._jitter)
        return wait_time + random.random() * jitter - jitter / 2

    def get_wait_time(self):
        wait_time = self.factor * self.base ** self._retries
        if self.max_wait is None or wait_time > self.max_wait:
            wait_time = self.max_wait

        return self.add_jitter(wait_time)

    async def sleep(self):
        wait_time = self.get_wait_time()
        self._retries += 1
        self.logger.debug('backoff %s seconds', wait_time)
        await asyncio.sleep(wait_time)

    @classmethod
    def async_retry(cls, exceptions=Exception,
                    base=2, factor=1, max_wait=None, jitter=None, min_time_for_reset=None, logger=None):
        def wrapper(func):
            async def wrapped(*args, **kwargs):
                backoff_waiter = cls(base=base,
                                     factor=factor,
                                     max_wait=max_wait,
                                     jitter=jitter,
                                     min_time_for_reset=min_time_for_reset,
                                     logger=logger)
                while True:
                    start_time = time.time()
                    try:
                        return await func(*args, **kwargs)
                    except exceptions:
                        run_time = time.time() - start_time

                        if backoff_waiter.min_time_for_reset and run_time > backoff_waiter.min_time_for_reset:
                            backoff_waiter.reset()

                        await backoff_waiter.sleep()

            return wrapped
        return wrapper


@asynccontextmanager
async def open_connection(host: str, port: int, connect_timeout=CONNECT_TIMEOUT) -> Tuple[asyncio.StreamReader,
                                                                                          asyncio.StreamWriter]:

    writer: Optional[asyncio.StreamWriter] = None
    try:
        reader: asyncio.StreamReader
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=connect_timeout)
        yield reader, writer
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()


class ProtocolError(Exception):
    pass


class WrongToken(ProtocolError):
    pass
