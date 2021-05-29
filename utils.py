"""Shared utils module."""

import asyncio
from contextlib import asynccontextmanager
import logging
import random
import time
from typing import Optional, Tuple, Union

from async_timeout import timeout

from consts import CONNECT_TIMEOUT


class Backoff:
    """Exponential backoff with jitter."""

    def __init__(self, base=2, factor=1, max_wait=None, jitter=None, min_time_for_reset=None, logger=None):
        """Initiate backoff parameters."""
        self.base = base
        self.factor = factor
        self.max_wait = max_wait
        self._jitter = jitter
        self._retries = 0
        self.min_time_for_reset = min_time_for_reset
        self.logger = logger or logging.getLogger('backoff')

    def reset(self):
        """Reset retry counter."""
        self._retries = 0

    def add_jitter(self, wait_time):
        """Add jitter to time.

        wait_time ± random(0..self._jitter/2)
        """
        if self._jitter is None:
            return wait_time

        jitter = min(wait_time / 2, self._jitter)
        return wait_time + random.random() * jitter - jitter / 2

    def get_wait_time(self):
        """Calculate wait time as function of self._retries."""
        wait_time = self.factor * self.base ** self._retries
        if self.max_wait is None or wait_time > self.max_wait:
            wait_time = self.max_wait

        return self.add_jitter(wait_time)

    async def sleep(self):
        """Asynchronous sleep."""
        wait_time = self.get_wait_time()
        self._retries += 1
        self.logger.debug('backoff %s seconds', wait_time)
        await asyncio.sleep(wait_time)

    @classmethod
    def async_retry(cls, exception=Union[Exception, Tuple[Exception]],
                    base=2, factor=1, max_wait=None, jitter=None, min_time_for_reset=None, logger=None):
        """Make decorator to retry with backoff."""
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
                    except exception:
                        run_time = time.time() - start_time

                        if backoff_waiter.min_time_for_reset and run_time > backoff_waiter.min_time_for_reset:
                            backoff_waiter.reset()

                        await backoff_waiter.sleep()

            return wrapped
        return wrapper


def call_if_callable(func):
    """Check if func is callable and run it with exception handling."""
    if callable(func):
        try:
            func()
        except Exception as ex:
            logging.warning('%r raised exception %r', func, ex)


@asynccontextmanager
async def open_connection(
        host: str, port: int,
        connect_timeout=CONNECT_TIMEOUT,
        on_connecting=None,
        on_connected=None,
        on_closed=None) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Make connection and close it after __aexit__."""
    call_if_callable(on_connecting)

    writer: Optional[asyncio.StreamWriter] = None
    try:
        async with timeout(connect_timeout):
            reader: asyncio.StreamReader
            reader, writer = await asyncio.open_connection(host, port)

        call_if_callable(on_connected)

        yield reader, writer
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()

        call_if_callable(on_closed)


class ProtocolError(Exception):
    """Exception for protocol problems."""


class WrongToken(ProtocolError):
    """Exception for protocol problems with token."""
