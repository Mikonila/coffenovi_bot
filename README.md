# Coffee Novi Bot

Телеграм-бот на `aiogram v3`, который читает таблицу `HercegNovi Standards.xlsx`, хранит готовые русские карточки напитков в `data/drink_cards.json`, а после выбора отправляет фото и инструкцию по приготовлению.

## Что уже сделано

- Парсинг листа `Drinks` напрямую из `xlsx`, без `openpyxl`.
- Автоматическое извлечение фото из `xl/media/*` в `assets/images`.
- Восстановление соответствия `напиток -> фото` по координатам изображений на листе.
- Загрузка фото в `Cloudinary` через API с кэшированием URL в `data/cloudinary_urls.json`.
- Меню категорий и напитков на inline-кнопках.
- Экспорт готовых русских карточек напитков в `data/drink_cards.json`.
- Загрузка карточек из `data/drink_cards.json` без перевода на лету в боте.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Заполните в `.env`:

- `BOT_TOKEN`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

## Загрузка фото в Cloudinary

Один раз выполните:

```bash
python -m app.sync_assets
```

Скрипт:

- извлечет все используемые изображения из Excel
- загрузит недостающие файлы в `Cloudinary`
- сохранит итоговые URL в `data/cloudinary_urls.json`

## Экспорт карточек напитков

Один раз выполните:

```bash
python -m app.export_cards
```

Скрипт:

- прочитает лист `Drinks` из Excel
- переведет и соберет карточки всех напитков
- сохранит готовые тексты в `data/drink_cards.json`

## Запуск бота

```bash
python -m app.bot
```

## Деплой

Есть готовый скрипт [deploy.sh](/home/valerya/Документы/Bots/CoffeNovi_bot/deploy.sh:1). Он отправляет на сервер:

- код из `app/`
- `requirements.txt`
- `HercegNovi Standards.xlsx`
- `data/drink_cards.json`
- ваш текущий `.env`
- `data/cloudinary_urls.json`, если файл уже существует

Добавьте в ваш `.env`:

```env
DEPLOY_HOST=138.249.149.55
DEPLOY_USER=root
DEPLOY_PATH=/opt/coffee-novi-bot
DEPLOY_SERVICE=coffee-novi-bot
```

Опционально:

```env
DEPLOY_PORT=22
DEPLOY_PYTHON=python3
DEPLOY_RUN_USER=root
```

После этого запуск простой:

```bash
./deploy.sh
```

Скрипт сам создает `/etc/systemd/system/<DEPLOY_SERVICE>.service`, включает его в автозапуск и после загрузки всегда перезапускает сервис.

Если хотите, чтобы бот сам догружал недостающие изображения в `Cloudinary` на старте, включите:

```env
AUTO_UPLOAD_TO_CLOUDINARY=true
```

## Деплой на Railway через GitHub

Для Railway в репозитории есть [railway.toml](/home/valerya/Документы/Bots/CoffeNovi_bot/railway.toml:1). Railway прочитает его при деплое из GitHub, установит зависимости из `requirements.txt` и запустит бота командой:

```bash
python -m app.bot
```

Подключение:

1. Запушьте проект в GitHub.
2. В Railway выберите `New Project` -> `Deploy from GitHub repo`.
3. Выберите репозиторий `Mikonila/coffenovi_bot`.
4. В Variables добавьте:

```env
BOT_TOKEN=...
ADMIN_USER_IDS=123456789
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
AUTO_UPLOAD_TO_CLOUDINARY=true
```

`AUTO_UPLOAD_TO_CLOUDINARY=true` нужен для Railway, потому что локальные `assets/images/` и `data/cloudinary_urls.json` не хранятся в GitHub. При старте контейнера бот извлечет изображения из Excel и создаст Cloudinary-кэш заново.

## Поведение бота

1. `/start` показывает разделы напитков.
2. Пользователь выбирает раздел.
3. Пользователь выбирает напиток.
4. Бот присылает фото и текст из `data/drink_cards.json`:
   - объем
   - состав
   - способ приготовления
   - подачу
