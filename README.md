# Scrapper

## Запуск

### Dev-режим (разработка)

```bash
docker compose -f docker-compose.dev.yml up --build
```

Hot-reload: изменения в коде подхватываются автоматически.

### Production-режим

```bash
docker compose up --build
```

### Остановка

```bash
docker compose down
```

Интерфейс: **http://localhost:3000**
