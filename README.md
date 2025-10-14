# VK Payment Bot

VK-бот для автоматического сбора контактов, приема оплат через YooKassa и выдачи доступа к материалам.

1) Установить зависимости:
   pip install -r requirements.txt

2) Настроить .env (см. README секцию в проекте)

3) Создать БД PostgreSQL (см. инструкции)

4) Запустить:
   python main.py

5) Настроить Callback API в сообществе VK на https://<BASE_URL>/vk_callback
   Настроить webhook в YooKassa на https://<BASE_URL>/yookassa_webhook
