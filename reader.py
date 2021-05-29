"""Chat reader module."""

import asyncio
from asyncio.exceptions import TimeoutError
import datetime
import logging

import aiofiles
from async_timeout import timeout
import configargparse

from consts import CONNECT_TIMEOUT
from consts import READ_TIMEOUT
from utils import Backoff
from utils import open_connection

logger = logging.getLogger('reader')


def make_timestamp():
    """Make formatted current time string."""
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M")


@Backoff.async_retry(exception=TimeoutError, max_wait=60, jitter=1, logger=logger,
                     min_time_for_reset=max(CONNECT_TIMEOUT, READ_TIMEOUT) + 1)
async def connect_and_read(host, port, history_file):
    """Connect to chat server, read and save all messages to history_file."""
    async with open_connection(host, port) as (reader, _):

        async with aiofiles.open(history_file, mode='a') as chat_log_file:
            while not reader.at_eof():
                async with timeout(READ_TIMEOUT):
                    line = await reader.readline()

                formatted_line = f'[{make_timestamp()}] {line.decode()}'
                logger.debug(repr(formatted_line))

                await chat_log_file.write(formatted_line)
                await chat_log_file.flush()


def main():
    """Parse args and run reader."""
    args = configargparse.ArgParser(
        prog='reader.py',
        ignore_unknown_config_file_keys=True,
        default_config_files=['.settings']
    )
    args.add('-c', '--config', is_config_file=True, help='config file path')
    args.add('--read_host', env_var='READ_HOST', help='host of server to read')
    args.add('--read_port', env_var='READ_PORT', help='port of server to read')
    args.add('--loglevel', help='log level')
    args.add('--history', env_var='HISTORY_FILE', help='history file path')
    options = args.parse_args()

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    try:
        asyncio.run(connect_and_read(options.read_host, options.read_port, options.history))
    except KeyboardInterrupt:
        logger.debug('Reader stopped')


if __name__ == '__main__':
    main()
