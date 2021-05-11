"""Chat message writer module."""

import asyncio
import logging

import configargparse

from utils import open_connection
from utils import ProtocolError
from utils import WrongToken

logger = logging.getLogger('sender')


async def connect_and_send(host, port, token, message):
    """Connect to chat server, login and send message."""
    async with open_connection(host, port) as (reader, writer):

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith(
                'Hello %username%! Enter your personal hash or leave it empty to create new account.\n'):
            raise ProtocolError(f'wrong hello message {line!r}')

        token_message = f'{token}\n'
        logger.debug('< %r', token_message)
        writer.write(token_message.encode())
        await writer.drain()

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith('{') or token not in decoded_line:
            raise WrongToken(f'cant login {line!r}')

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', decoded_line)
        if not decoded_line.startswith('Welcome to chat! Post your message below. End it with an empty line.\n'):
            raise ProtocolError(f'wrong welcome message {line!r}')

        logger.debug('< %r', message)
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()

        line = await reader.readline()
        logger.debug('> %r', line)
        if not line.decode().startswith(
                'Message send. Write more, end message with an empty line.\n'):
            raise ProtocolError(f'wrong confirm message {line!r}')

        logger.debug(f'message <{message}> sent')


def main():
    """Parse args and run send message process."""
    args = configargparse.ArgParser(
        prog='writer.py',
        ignore_unknown_config_file_keys=True,
        default_config_files=['.settings'])
    args.add('-c', '--config', is_config_file=True, help='config file path')
    args.add('--write_host', env_var='WRITE_HOST', help='host of server to write')
    args.add('--write_port', env_var='WRITE_PORT', help='port of server to write')
    args.add('--write_token', env_var='TOKEN', help='port of server')
    args.add('--message', required=True, help='message for chat')
    args.add('--loglevel', help='log level')

    options = args.parse_args()
    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    logger.debug(options)

    asyncio.run(
        connect_and_send(
            options.write_host,
            options.write_port,
            options.write_token,
            options.message))


if __name__ == '__main__':
    main()
