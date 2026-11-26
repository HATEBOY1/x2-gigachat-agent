import os
from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

# Добавляем model="GigaChat-2"
client = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"), 
    model="GigaChat-2",
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False
)

try:
    response = client.chat("Помаши рукой")
    print("Ответ GigaChat:", response.choices[0].message.content)
except Exception as e:
    print("Ошибка подключения:", e)