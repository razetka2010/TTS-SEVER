---
name: tts-sever
description: Maintains the ТТС-Север Django ticketing app (requests queue, roles, tech panel, polling). Use when editing this repo, fixing request numbering or permissions, or changing templates under templates/requests/.
disable-model-invocation: true
---

# ТТС-Север (проект заявок)

## Стек и расположение

- Django; приложения `apps.requests`, `apps.accounts`.
- Заявки: модель `Request` в `apps/requests/models.py`.
- Шаблоны: `templates/requests/` (`list.html`, `tech_dashboard.html`, `tv_board.html`, `create.html`, `includes/filter_bar.html`).
- Фоновое обновление карточек: `requests_api_state` + `static/js/main.js` (polling).

## Экран TV

- URL: `/requests/tv/<TV_BOARD_SECRET>/` — **без входа**, секрет из `settings.TV_BOARD_SECRET` (.env `TV_BOARD_SECRET`, не короче 12 символов). Неверный ключ → 404.
- Polling: `scope=tv` + GET-параметр `tv_secret` (как на странице). Остальные `scope` API требуют авторизации.
- Полная ссылка для закладки показывается в «Аналитике» администратору.

## Роли

- `user` — только свои заявки, создание заявки (`create_request`).
- `tech_admin` — техпанель (`tech_dashboard`), закрепление заявки при сохранении если не `admin`.
- `admin` — все заявки, может править любую активную в техпанели.

## Два номера заявки

- **`owner_number`** — порядковый номер **у автора** (заполняется в `save()` при создании, см. `Max("owner_number")` по `created_by_id`).
- **`pk`** — системный уникальный идентификатор в БД.

Отображение:

- Пользователь в «Мои заявки»: основной бейдж — личный № (`owner_number`), рядом текст «в системе №`pk`» для связи с техниками.
- Техпанель и список «Заявки» для персонала: основной номер — **`pk`**, чтобы не было дублей «№1» у разных авторов.

## SQLite

После удаления всех заявок сбрасывается `sqlite_sequence` для таблицы заявок (`_reset_sqlite_request_sequence_if_empty`), чтобы следующий `id` снова начинался с 1. На других СУБД поведение по умолчанию.

## Принципы правок

- Менять только то, что относится к задаче; повторять стиль шаблонов и форм проекта.
- При изменении полей карточки учитывать polling: `data-request-pk`, `data-role` для бейджа, комментария, назначения.
