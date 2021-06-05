"""Register new nick name module."""

import asyncio
import json
import logging

import configargparse

from utils import open_connection
from utils import ProtocolError
from utils import WrongToken

logger = logging.getLogger('register')


async def connect_and_register(host, port, nickname):
    """Connect to chat server and try to register nickname."""
    async with open_connection(host, port) as (reader, writer):

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith(
                'Hello %username%! Enter your personal hash or leave it empty to create new account.\n'):
            raise ProtocolError(f'wrong hello message {line!r}')

        token_message = '\n'
        logger.debug('< %r', token_message)
        writer.write(token_message.encode())
        await writer.drain()

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith('Enter preferred nickname below:\n'):
            raise ProtocolError(f'wrong prompt message {line!r}')

        register_nickname_message = f'{nickname}\n'
        logger.debug('< %r', register_nickname_message)
        writer.write(register_nickname_message.encode())
        await writer.drain()

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith('{') or 'account_hash' not in decoded_line:
            raise WrongToken(f'cant register {line!r}')

        token_json = json.loads(decoded_line)
        token = token_json.get('account_hash')

        if not token:
            raise WrongToken(f'token not found in register answer {token_json!r}')

        return token


def save_token(token):
    """Save token to config file."""
    # создаем отдельный парсер без ignore_unknown_config_file_keys, чтобы не испортить конфиг
    config_saver = configargparse.ArgParser(default_config_files=['.token'])
    # добавляем параметр write_token в known_args
    config_saver.add('--write_token', required=True, env_var='TOKEN')
    # и перечитывем TOKEN из переменных окружения
    options, _ = config_saver.parse_known_args(env_vars={'TOKEN': token})
    # сохраняем конфиг с writer_token
    config_saver.write_config_file(options, ['.token'], exit_after=False)


def main():
    """Parse args, run register process and save token."""
    args = configargparse.ArgParser(prog='register.py',
                                    ignore_unknown_config_file_keys=True,
                                    default_config_files=['.settings'])
    args.add('-c', '--config', is_config_file=True, help='config file path')
    args.add('--write_host', env_var='WRITE_HOST', help='host of server to write')
    args.add('--write_port', env_var='WRITE_PORT', help='port of server to write')
    args.add('--loglevel', help='log level')
    args.add('writer_nickname', help='nickname to register')

    options = args.parse_args()

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    logger.debug(options)

    token = asyncio.run(
        connect_and_register(
            options.write_host,
            options.write_port,
            options.writer_nickname,
        ))

    save_token(token)
    logger.debug('exiting')


if __name__ == '__main__':
    main()
