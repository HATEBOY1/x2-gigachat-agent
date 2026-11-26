# gigachat_client.py
import os
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole, ChatCompletion
from skills import robot_functions

class GigaChatAgentLLM:
    def __init__(self):
        self.client = GigaChat(
            base_url="https://api.giga.chat/v1",
            credentials=os.getenv("GIGACHAT_CREDENTIALS"),
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,  # В production замените на путь к сертификату НУЦ Минцифры
            model="GigaChat-2-Pro",  # Или GigaChat-2-Max
        )
        self.system_prompt = (
            "Ты — дружелюбный человекоподобный робот. Отвечай кратко и естественно на русском языке. "
            "Когда пользователь просит выполнить действие, вызывай соответствующую функцию. "
            "Если просто разговаривает — отвечай текстом без вызова функций."
        )

    def chat(self, user_text: str, history: list = None) -> ChatCompletion:
        messages = [Messages(role=MessagesRole.SYSTEM, content=self.system_prompt)]
        if history:
            messages.extend(history)
        messages.append(Messages(role=MessagesRole.USER, content=user_text))

        payload = Chat(
            messages=messages,
            functions=robot_functions,
            function_call="auto",  # Позволяет модели автоматически решать, вызывать ли функцию
        )
        return self.client.chat(payload)