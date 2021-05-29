"""Chat registration gui application."""

import asyncio
import logging
from tkinter import messagebox
import tkinter as tk

import anyio
import configargparse

import gui
from gui import update_tk
from register import connect_and_register
from register import save_token
import utils

logger = logging.getLogger('register-gui')


async def register_nickname_and_exit(write_host, write_port, events_queue):
    """
    Receive writer_nickname from events_queue and register it on chat server.

    After registration shows message box about token saving.
    And close application.
    """
    writer_nickname = await events_queue.get()
    token = await connect_and_register(
        write_host,
        write_port,
        writer_nickname,
    )

    save_token(token)
    messagebox.showinfo('Токен сохранен', 'Регистрация успешно завершена.')
    raise gui.TkAppClosed


def process_nickname(input_field, events_queue):
    """Take text from input box and put it to queue."""
    text = input_field.get()
    events_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def draw_register_gui(events_queue: asyncio.Queue):
    """Render application gui."""
    root = tk.Tk()

    root.title('Регистрация нового пользователя')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)
    input_field.focus_set()
    input_field.bind("<Return>", lambda event: process_nickname(input_field, events_queue))

    send_button = tk.Button(input_frame)
    send_button["text"] = "Зарегистрировать"
    send_button["command"] = lambda: process_nickname(input_field, events_queue)
    send_button.pack(side="left")

    label = tk.Label(root_frame, text="Введите имя пользователя", width=15, height=3)
    label.pack(side="top", fill=tk.BOTH, expand=True)

    async with anyio.create_task_group() as tg:
        tg.start_soon(update_tk, root_frame)


async def main(write_host, write_port):
    """Init and start chat registration gui application."""
    events_queue = asyncio.Queue()
    async with anyio.create_task_group() as tg:
        tg.start_soon(draw_register_gui, events_queue)
        tg.start_soon(register_nickname_and_exit, write_host, write_port, events_queue)


if __name__ == '__main__':
    args = configargparse.ArgParser(
        prog='app.py',
        ignore_unknown_config_file_keys=True,
        default_config_files=['.settings']
    )
    args.add('-c', '--config', is_config_file=True, help='config file path')
    args.add('--write_host', env_var='WRITE_HOST', help='host of server to write')
    args.add('--write_port', env_var='WRITE_PORT', help='port of server to write')
    args.add('--loglevel', help='log level')
    options = args.parse_args()

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(options.write_host, options.write_port))
    except (utils.WrongToken, utils.ProtocolError) as ex:
        messagebox.showerror('Проблема', f'Регистрация завершилась с ошибкой: {ex!r}.')
    except (gui.TkAppClosed, KeyboardInterrupt):
        pass
