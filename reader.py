import asyncio
import datetime
import logging
import random

import aiofiles
import configargparse

from utils import closing

logger = logging.getLogger('reader')
CONNECT_TIMEOUT = 3
READ_TIMEOUT = 3


def make_timestamp():
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M")


class Backoff:
    """
    Exponential backoff with jitter
    """

    def __init__(self, base=2, factor=1, max_wait=None, jitter=None):
        self.base = base
        self.factor = factor
        self.max_wait = max_wait
        self._jitter = jitter
        self._retries = 0

    def reset(self):
        self._retries = 0

    async def backoff(self):
        wait_time = self.jitter(self.expo())
        logger.debug('backoff %s seconds', wait_time)
        await asyncio.sleep(wait_time)

    def jitter(self, wait_time):
        if self._jitter is None:
            return wait_time

        jitter = max(wait_time / 2, self._jitter)
        return wait_time + random.random() * jitter - jitter / 2

    def expo(self):
        while True:
            wait_time = self.factor * self.base ** self._retries
            if self.max_wait is None or wait_time < self.max_wait:
                self._retries += 1
                return wait_time
            else:
                return self.max_wait


async def connect_and_read(host, port, history_file):
    backoff = Backoff(max_wait=60, jitter=1)
    while True:
        try:
            with closing(
                    await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=CONNECT_TIMEOUT)) as (reader, _):

                backoff.reset()

                async with aiofiles.open(history_file, mode='a') as chat_log_file:
                    while not reader.at_eof():
                        line = await asyncio.wait_for(
                            reader.readline(),
                            timeout=READ_TIMEOUT)
                        formated_line = f'[{make_timestamp()}] {line.decode()}'
                        logger.debug(repr(formated_line))

                        await chat_log_file.write(formated_line)
                        await chat_log_file.flush()

        except asyncio.exceptions.TimeoutError:
            await backoff.backoff()
        except Exception as ex:
            logger.error(repr(ex), exc_info=True)


def main():
    args = configargparse.ArgParser(default_config_files=['.settings'])
    args.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    # starts with '--' options can be set in a config file
    args.add('--host', required=False, env_var='HOST', help='host of server')
    args.add('--port', required=False, env_var='PORT', help='port of server')
    args.add('--loglevel', required=False, help='log level')
    args.add('--history', required=False, env_var='HISTORY_FILE', help='history file path')
    options, _ = args.parse_known_args()

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    asyncio.run(connect_and_read(options.host, options.port, options.history))


if __name__ == '__main__':
    main()
