Проект Foodgram.
https://foodandmemes.serveminecraft.net/

Foodgram - это онлайн-сервис для публикации рецептов. Пользователи могут создавать свои рецепты, добавлять их в избранное и корзину покупок, а также подписываться на других авторов рецептов. Проект включает модели для работы с рецептами, ингредиентами и тегами, а также систему подписок и избранных рецептов.

Инструкция по запуску в Docker

Клонируйте репозиторий:
git clone https://github.com/Beeta-test/foodgram

Перейдите в директорию проекта:
cd foodgram

Соберите и запустите контейнеры:
sudo docker compose -f docker-compose.production.yml up

Примените миграции, соберите статику и создайте суперпользователя:
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
Проект будет доступен по адресу http://localhost/.

Стек технологий
Python 3.10
Django 3.9
Django REST Framework
PostgreSQL
Docker
Gunicorn - WSGI сервер
Nginx - веб-сервер
Djoser - библиотека для управления пользователями и авторизацией

Как наполнить БД данными
python manage.py loadstatikdata
sudo docker-compose exec backend python manage.py loadstatikdata.json
Вы также можете добавить теги и рецепты через админ-панель, доступную по адресу http://localhost/admin/.


Документация API доступна по адресу:
http://localhost/api/docs/
Находясь в папке infra, выполните команду docker-compose up. При выполнении этой команды контейнер frontend, описанный в docker-compose.yml, подготовит файлы, необходимые для работы фронтенд-приложения, а затем прекратит свою работу.

Пример запросов и ответов
Получение списка рецептов

Запрос:
GET /api/recipes/

Ответ:
{
  "count": 100,
  "next": "http://localhost/api/recipes/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "tags": [
        {
          "id": 1,
          "name": "Завтрак",
          "slug": "breakfast"
        }
      ],
      "author": {
        "email": "user@example.com",
        "id": 1,
        "username": "user1",
        "first_name": "User",
        "last_name": "Test"
      },
      "ingredients": [
        {
          "id": 1,
          "name": "Яйцо",
          "amount": 2,
          "measurement_unit": "шт"
        }
      ],
      "is_favorited": false,
      "is_in_shopping_cart": false,
      "name": "Яичница",
      "image": "http://localhost/media/recipes/egg_dish.jpg",
      "text": "Рецепт приготовления яичницы.",
      "cooking_time": 10
    }
  ]
}

Добавление рецепта в избранное

Запрос:
POST /api/recipes/1/favorite/

Ответ:
{
  "id": 1,
  "name": "Яичница"
}

Авторство
Проект разработан Maxism Cherdansev.(https://github.com/Beeta-test)
