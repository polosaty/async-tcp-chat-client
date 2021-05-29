import asyncio
from asyncio.exceptions import CancelledError
from asyncio.exceptions import TimeoutError
from contextlib import asynccontextmanager
import json
import logging
import os
import time
from tkinter import messagebox
from typing import Optional, Tuple, Type, Union

import aiofiles
import aiofiles.os
import anyio
import anyio.abc
from async_timeout import timeout
import configargparse

from consts import CONNECT_TIMEOUT
from consts import IDLE_TIMEOUT
from consts import READ_TIMEOUT
import gui
from reader import make_timestamp
import utils
from utils import Backoff
from writer import send_message

logger = logging.getLogger('app')
watchdog_logger = logging.getLogger('watchdog')


@Backoff.async_retry(exception=(TimeoutError, CancelledError), max_wait=60, jitter=1, logger=logger,
                     min_time_for_reset=max(CONNECT_TIMEOUT, READ_TIMEOUT) + 1)
async def read_msgs(host: str, port: int,
                    status_updates_queue: asyncio.Queue,
                    watchdog_queue: asyncio.Queue,
                    *out_queues: asyncio.Queue):
    """Connect to chat server, read and save all messages to history_file and queue."""

    async with open_connection_with_status(
            host, port,
            status_updates_queue=status_updates_queue,
            connection_status_enum=gui.ReadConnectionStateChanged
    ) as (reader, writer):

        while not reader.at_eof():
            async with timeout(READ_TIMEOUT):
                line = await reader.readline()

            message = line.decode().rstrip()

            watchdog_queue.put_nowait('New message in chat')

            for queue in out_queues:
                queue.put_nowait(message)
                queue.task_done()


async def save_messages(filepath: str, queue: asyncio.Queue):
    async with aiofiles.open(filepath, mode='a') as chat_log_file:
        while True:
            message = await queue.get()

            formated_line = f'[{make_timestamp()}] {message}\n'
            logger.debug(repr(formated_line))

            await chat_log_file.write(formated_line)
            await chat_log_file.flush()


async def authorize_writer(token, reader, writer, status_updates_queue, watchdog_queue):
    line = await reader.readline()
    decoded_line = line.decode()
    logger.debug('> %r', line)
    if not decoded_line.startswith(
            'Hello %username%! Enter your personal hash or leave it empty to create new account.\n'):
        raise utils.ProtocolError(f'wrong hello message {line!r}')

    watchdog_queue.put_nowait('Prompt before auth')

    token_message = f'{token}\n'
    logger.debug('< %r', token_message)
    writer.write(token_message.encode())
    await writer.drain()

    line = await reader.readline()
    login_response_json = line.decode()
    logger.debug('> %r', line)
    if not login_response_json.startswith('{') or token not in login_response_json:
        raise utils.WrongToken(f'cant login {line!r}')

    login_response = json.loads(login_response_json)

    line = await reader.readline()
    decoded_line = line.decode()
    logger.debug('> %r', decoded_line)
    if not decoded_line.startswith('Welcome to chat! Post your message below. End it with an empty line.\n'):
        raise utils.ProtocolError(f'wrong welcome message {line!r}')

    if login_response:
        nickname = login_response.get('nickname')
        logger.debug('Выполнена авторизация. Пользователь %r.', nickname)
        status_updates_queue.put_nowait(gui.NicknameReceived(nickname))
        watchdog_queue.put_nowait('Authorization done')


ConnectionStatusEnum = Union[Type[gui.ReadConnectionStateChanged],
                             Type[gui.SendingConnectionStateChanged]]


@asynccontextmanager
async def open_connection_with_status(
        host: str, port: int,
        status_updates_queue: asyncio.Queue,
        connection_status_enum: ConnectionStatusEnum,
        connect_timeout=CONNECT_TIMEOUT,
) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Make connection and close it after __aexit__.
        And report status to status_updates_queue.
    """

    status_updates_queue.put_nowait(connection_status_enum.INITIATED)

    writer: Optional[asyncio.StreamWriter] = None
    try:
        async with timeout(connect_timeout):
            reader: asyncio.StreamReader
            reader, writer = await asyncio.open_connection(host, port)

        status_updates_queue.put_nowait(connection_status_enum.ESTABLISHED)

        yield reader, writer
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()

        status_updates_queue.put_nowait(connection_status_enum.CLOSED)


@Backoff.async_retry(exception=(TimeoutError, CancelledError), max_wait=60, jitter=1, logger=logger,
                     min_time_for_reset=CONNECT_TIMEOUT + 1)
async def send_msgs(
        host: str, port: int, token: str,
        sending_queue: asyncio.Queue,
        status_updates_queue: asyncio.Queue,
        watchdog_queue: asyncio.Queue):

    async with open_connection_with_status(
            host, port,
            connection_status_enum=gui.SendingConnectionStateChanged,
            status_updates_queue=status_updates_queue,
    ) as (reader, writer):

        await authorize_writer(token, reader, writer, status_updates_queue, watchdog_queue)

        while True:
            try:
                with timeout(IDLE_TIMEOUT) as timeout_context:
                    message = await sending_queue.get()
                    logger.debug('Пользователь написал: %r', )
                    await send_message(message, reader, writer)
                    watchdog_queue.put_nowait('Message sent')

            except TimeoutError:
                if not timeout_context.expired:
                    raise
                await send_message('', reader, writer)
                watchdog_queue.put_nowait('Ping message sent')


async def load_history(filepath: str, queue: asyncio.Queue, tail_size=10240):
    """Загружает "хвост" файла в очередь."""

    async with aiofiles.open(filepath, mode='r') as chat_log_file:
        file_size = (await aiofiles.os.stat(filepath)).st_size
        if file_size > tail_size:
            await chat_log_file.seek(file_size - tail_size, os.SEEK_SET)

        # Пытаемся найти границу символа
        # Иногда seek попадает на середину символа
        try:
            message = await chat_log_file.readline()
        except UnicodeDecodeError:
            await chat_log_file.seek(file_size - tail_size - 1, os.SEEK_SET)
            message = await chat_log_file.readline()

        while message:
            # намеренно пропускаем первую строку
            # т.к. она, весьма вероятно, прочиталась не целиком
            message = await chat_log_file.readline()
            await queue.put(message.rstrip())


async def watch_for_connection(watchdog_queue):
    while True:
        message = None
        try:
            async with timeout(READ_TIMEOUT * 2) as timeout_context:
                message = await watchdog_queue.get()
        except TimeoutError:
            if not timeout_context.expired:
                raise
            watchdog_logger.debug('[%d] 1s timeout is elapsed', time.time())
            raise ConnectionError()
        if message:
            watchdog_logger.debug('[%d] Connection is alive. Source: %r', time.time(), message)


@Backoff.async_retry(exception=(ConnectionError, TimeoutError), max_wait=60, jitter=1, logger=logger,
                     min_time_for_reset=CONNECT_TIMEOUT + 1)
async def handle_connection(*coroutines):
    tg: anyio.abc.TaskGroup
    async with anyio.create_task_group() as tg:
        for coroutine in coroutines:
            tg.start_soon(coroutine)


async def main(options):
    messages_queue = asyncio.Queue()
    messages_log_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    async with anyio.create_task_group() as tg:
        tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
        tg.start_soon(load_history, options.history, messages_queue)
        tg.start_soon(save_messages, options.history, messages_log_queue)

        tg.start_soon(
            handle_connection,
            lambda: read_msgs(options.read_host, options.read_port,
                              status_updates_queue,
                              watchdog_queue,
                              messages_queue,
                              messages_log_queue),
            lambda: send_msgs(options.write_host, options.write_port, options.write_token,
                              sending_queue, status_updates_queue, watchdog_queue),
            lambda: watch_for_connection(watchdog_queue))


if __name__ == '__main__':
    args = configargparse.ArgParser(
        prog='app.py',
        ignore_unknown_config_file_keys=True,
        default_config_files=['.settings']
    )
    args.add('-c', '--config', is_config_file=True, help='config file path')
    args.add('--read_host', env_var='READ_HOST', help='host of server to read')
    args.add('--read_port', env_var='READ_PORT', help='port of server to read')
    args.add('--write_host', env_var='WRITE_HOST', help='host of server to write')
    args.add('--write_port', env_var='WRITE_PORT', help='port of server to write')
    args.add('--write_token', env_var='TOKEN', help='port of server')
    args.add('--loglevel', help='log level')
    args.add('--history', env_var='HISTORY_FILE', help='history file path')
    options = args.parse_args()

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)
        watchdog_logger.setLevel(options.loglevel)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(options))
        # loop.run_until_complete(gui.draw_register_gui())
    except utils.WrongToken:
        messagebox.showerror('Неверный токен', 'Проверьте токен, сервер его не узнал.')
    except (gui.TkAppClosed, KeyboardInterrupt):
        pass
