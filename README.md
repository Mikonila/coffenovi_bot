# Coffee Novi Bot

Телеграм-бот на `aiogram v3`, который читает таблицу `HercegNovi Standards.xlsx`, показывает категории напитков на русском языке, а после выбора отправляет фото и инструкцию по приготовлению.

## Что уже сделано

- Парсинг листа `Drinks` напрямую из `xlsx`, без `openpyxl`.
- Автоматическое извлечение фото из `xl/media/*` в `assets/images`.
- Восстановление соответствия `напиток -> фото` по координатам изображений на листе.
- Загрузка фото в `Cloudinary` через API с кэшированием URL в `data/cloudinary_urls.json`.
- Меню категорий и напитков на inline-кнопках.
- Русская локализация названий разделов, напитков и типовых описаний из Excel.

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

## Запуск бота

```bash
python -m app.bot
```

## Деплой

Есть готовый скрипт [deploy.sh](/home/valerya/Документы/Bots/CoffeNovi_bot/deploy.sh:1). Он отправляет на сервер:

- код из `app/`
- `requirements.txt`
- `HercegNovi Standards.xlsx`
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

## Деплой на Railway

Для Railway добавлены:

- [railway.toml](/home/valerya/Документы/Bots/CoffeNovi_bot/railway.toml:1) с явной командой запуска `python -m app.bot`.
- [.railwayignore](/home/valerya/Документы/Bots/CoffeNovi_bot/.railwayignore:1), чтобы не загружать локальный `venv`, `.env`, кэши и временно извлеченные картинки.
- [deploy_railway.sh](/home/valerya/Документы/Bots/CoffeNovi_bot/deploy_railway.sh:1) для деплоя через Railway CLI.

В Railway добавьте переменные окружения:

```env
BOT_TOKEN=...
ADMIN_USER_IDS=123456789
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
AUTO_UPLOAD_TO_CLOUDINARY=true
```

`AUTO_UPLOAD_TO_CLOUDINARY=true` важен для Railway: `assets/images/` и `data/cloudinary_urls.json` не отправляются в деплой, поэтому бот извлечет картинки из Excel и создаст Cloudinary-кэш при старте контейнера.

Первый запуск через CLI:

```bash
npm install -g @railway/cli
railway login
railway link
./deploy_railway.sh
```

Если деплоите через GitHub-интеграцию Railway, достаточно подключить репозиторий: Railway прочитает `railway.toml`, установит зависимости из `requirements.txt` и запустит `python -m app.bot`.

## Поведение бота

1. `/start` показывает разделы напитков.
2. Пользователь выбирает раздел.
3. Пользователь выбирает напиток.
4. Бот присылает фото и текст:
   - объем
   - состав
   - способ приготовления
   - подачу
