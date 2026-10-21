# Old Calculator — локальний Docker-інстанс

Securinets · автор: [kristoferUA](https://github.com/kristoferUA)

[English](instance.md) · [Українська](instance.uk.md)

Linux-сервіс із відтворенням дослідженого протоколу Old Calculator на порту **4873**. Усередині є арифметика з дробами, читання вибраної комірки, 16 раундів, перевірені формати помилок та налаштовуваний прапор. Додано копію робочого солвера для локального запуску.

[До повного врайтапу](../README.uk.md)

## Швидкий запуск

Потрібен Docker Engine. Швидкий запуск використовує плагін Compose; нижче також наведені команди самого Docker Engine для Linux. Солвер можна запускати всередині контейнера, тому встановлювати Python на хості не потрібно.

Клонуй репозиторій і виконай наведені команди. Для розпакованого комплекту почни з його готової папки:

```bash
git clone https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup.git Securinets-old-calculator
cd Securinets-old-calculator
cp .env.example .env
docker compose up -d --build --wait
```

Підключення вручну:

```bash
nc 127.0.0.1 4873
```

Проходження всіх 16 раундів та отримання прапора:

```bash
docker compose exec -T --workdir /tmp calculator \
  python /app/solve.py --run --host 127.0.0.1 \
  --trace /tmp/local_trace.jsonl
```

Наприкінці з'явиться рядок `FLAG: Securinets{...}`. Перед основною сесією солвер окремо перевіряє точність показу 42-бітного дробу.

Збереження журналу на хості:

```bash
docker compose exec -T calculator cat /tmp/local_trace.jsonl > local_trace.jsonl
```

Для цього файла у `/tmp` використовуй виведення через `cat`. Після пересоздання контейнера тимчасовий журнал зникає.

## Готовий образ для Linux amd64

Повний комплект містить `release-assets/old-calculator-linux-amd64.tar.gz`. З кореня репозиторію:

```bash
docker load -i release-assets/old-calculator-linux-amd64.tar.gz
docker compose up -d --no-build --wait
```

Архів для GitHub містить файли репозиторію. Для окремо клонованого коду образ можна отримати з опублікованого GitHub Release, коли він буде доступний, і покласти в `release-assets/`. Порядок публікації описано в [publishing.md](publishing.md).

Імпорт образу дозволяє запустити сервіс без завантаження базового образу. Для іншої архітектури процесора збирай із Dockerfile.

## Запуск через Docker Engine

Ці команди підходять для Linux з установленим Docker Engine:

```bash
cp .env.example .env
docker run -d --name old-calculator-local --restart unless-stopped \
  -p 127.0.0.1:4873:4873 --env-file .env \
  --read-only --tmpfs /tmp:rw,mode=1777 --init \
  --cap-drop ALL --security-opt no-new-privileges:true \
  old-calculator-local:latest
docker exec -w /tmp old-calculator-local \
  python /app/solve.py --run --host 127.0.0.1 --trace /tmp/local_trace.jsonl
```

Перед цим імпортуй готовий образ або збери його командою `docker build -t old-calculator-local:latest .`. Зовнішній порт для `docker run` змінюється в аргументі `-p`. Щоб застосувати нові змінні середовища, пересоздай контейнер цього проєкту:

```bash
docker rm -f old-calculator-local
```

Потім повтори команду розгортання. Зберегти тимчасовий журнал можна через `docker exec old-calculator-local cat /tmp/local_trace.jsonl > local_trace.jsonl`.

## Відтворення записаної сесії

Режим `recorded` використовує функції, аргументи перевірки та початкові значення `x[0]` і `x[99]`, прочитані з живого інстансу 21 жовтня 2026 року:

```bash
docker compose -f compose.yaml -f compose.recorded.yaml up -d --wait
docker compose exec -T --workdir /tmp calculator \
  python /app/solve.py --run --host 127.0.0.1 \
  --sample-indices 0 99 --trace /tmp/recorded_trace.jsonl
```

Для цих індексів запаковані дроби й аргументи перевірки відтворюють досліджені 16 раундів. Інші 98 початкових елементів не були прочитані з оригіналу: вони заповнюються локальними детермінованими значеннями, які відповідають тій самій функції.

Повернення до випадкового режиму, якщо в `.env` встановлено `CALCULATOR_MODE=random`:

```bash
docker compose up -d --wait
```

## Налаштування

Зміни `.env`, потім виконай `docker compose up -d --force-recreate --wait`.

| Змінна | Типове значення | Призначення |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Адреса хоста, на якій Docker публікує порт |
| `HOST_PORT` | `4873` | Зовнішній TCP-порт; усередині контейнера залишається `4873` |
| `CALCULATOR_MODE` | `random` | `random` або `recorded` |
| `CALCULATOR_SEED` | порожньо | Необов'язковий seed для повторюваних локальних даних |
| `FLAG` | Прапор оригінального Old Calculator | Результат після 16 правильних відповідей |

Для власного прапора з доданим солвером використовуй звичну форму `Securinets{your_value}`. Сервіс повертає налаштований рядок.

У режимі `random` коефіцієнти вибираються з `1..16`, а входи й аргументи — з `0..255` через `SystemRandom`. Якщо вказати seed, кожне нове з'єднання отримує незалежний `random.Random(seed)` і повторювану послідовність. Точний генератор випадкових чисел оригіналу невідомий.

Якщо з фіксованим seed пара виявиться неоднозначною, вона повторюватиметься після перепідключення. Зміни seed або вибери індекси через `--sample-indices FIRST SECOND`. Комірка `98` використовується солвером для проміжного результату.

## Солвер на хості

За наявності Python 3.12:

```bash
python3 solve.py --run --host 127.0.0.1 --port 4873 --trace local_trace.jsonl
```

Ця копія за замовчуванням підключається до `127.0.0.1`; додані параметри `--host`, `--port` і `--sample-indices`. Пакування 42 бітів і відновлення коефіцієнтів збережені.

## Доступ до Linux-хоста через SSH

Відкрий тунель із клієнтського комп'ютера до Linux-хоста, де працює сервіс:

```bash
ssh -N -L 14873:127.0.0.1:4873 user@linux-host
```

Залиш з'єднання відкритим і звертайся до перенаправленого порту на клієнтському комп'ютері:

```bash
python3 solve.py --run --host 127.0.0.1 --port 14873 --trace forwarded_trace.jsonl
```

## Керування

```bash
docker compose ps
docker compose logs --tail 50 calculator
docker compose restart calculator
docker compose down
```

Щоб змінити зовнішній порт, установи `HOST_PORT=14873`; команда солвера всередині контейнера залишається такою самою.

## Що саме відтворюється

Підтверджені запрошення й пробіли, арифметика, дробовий показ, вкладені JSON-помилки, переходи між раундами та закриття з'єднань реалізовані за [записами протоколу](../reference/PROTOCOL.md).

Для невстановлених деталей зроблено явний вибір: усі 100 елементів оновлюються на початку раунду; нетипові JSON-значення й незавершений рядок при EOF обробляються звичайною логікою Python; додаткового таймера сесії чи ліміту операцій немає. Генерація випадкових даних залежить від вибраного локального режиму.

У каталозі `reference/` збережено докази дослідження, у `fixtures/` — записаний сценарій, у `examples/` — результати локального проходження. Сервіс використовує лише стандартну бібліотеку Python, ліцензія — MIT.
