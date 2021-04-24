# async-tcp-chat-client

Учебный проект по курсу [Асинхронный питон](https://dvmn.org/modules/async-python).
В проекте реализованы подключение к чату по протоколу TCP с последующим чтением переписки и запись в файл (по умолчанию chat.log).
Также реализованы регистрация пользователя и отправка сообщений в чат от имени зарегистрированного пользователя.

## Установка в virtualenv

Для установки потребуется python 3.9+ (теоретически должно работать на python 3.7, но это не тестировалось) и [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)

Скачиваем проект:

```shell
git clone git@github.com:polosaty/async-tcp-chat-client.git
# или git clone https://github.com/polosaty/async-tcp-chat-client.git
cd async-tcp-chat-client
```

Создаем виртуальное окружение, активируем его и устанавливаем в него зависимости:

```shell
virtualenv .env
source .env/bin/activate
pip install -r ./requirements.txt
```

### После установки зависимостей

Можно читать сообщения из чата:

```shell
python reader.py
```

Можно зарегистрировать нового пользователя:

```shell
python register.py writer_nickname
```

И отправлять от его имени сообщения в чат:

```shell
python writer.py --message Сообщение
```

## Установка в docker

Для установки потребуется docker + docker-compose

Скачиваем проект:
```shell
git clone git@github.com:polosaty/async-tcp-chat-client.git
# или git clone https://github.com/polosaty/async-tcp-chat-client.git
cd async-tcp-chat-client
```

Собираем образ:
```shell
docker-compose buld app
```

### После сборки образа

Можно читать сообщения из чата:

```shell
docker-compose run --rm app
```

Можно зарегистрировать нового пользователя:

```shell
docker-compose run --rm app python register.py writer_nickname
```

И отправлять от его имени сообщения в чат:

```shell
docker-compose run --rm app  python writer.py --message Сообщение
```

## Настройки

Все настройки можно задавать несколькими путями:
1. файл конфигурации `.settings` (в нем уже заданы дефолтные настройки 
   а, также в него сохраняется токен при регистрации нового пользователя)
2. переменные окружения
3. параметры командной строки для каждой из команд (подборнее `--help`)
