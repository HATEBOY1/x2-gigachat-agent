# agent.py (упрощенная логика)
import asyncio
import json
import websockets
from gigachat_client import GigaChatAgentLLM
from skills import map_to_robot_skill
from gigachat.models import Messages, MessagesRole

class X2GigaChatAgent:
    def __init__(self, ws_url="ws://127.0.0.1:9002"):
        self.ws_url = ws_url
        self.llm = GigaChatAgentLLM()
        self.conversation_history = []

    async def run(self):
        async with websockets.connect(self.ws_url) as ws:
            # 1. Отправка рукопожатия/регистрации (согласно протоколу Playground)
            await self.handshake(ws)
            
            # 2. Основной цикл: получение аудио → ASR → GigaChat → (возможно вызов функции) → TTS → отправка
            async for message in ws:
                data = json.loads(message)
                if data.get("type") == "asr_result":
                    user_text = data["text"]
                    await self.handle_user_input(ws, user_text)

    async def handle_user_input(self, ws, user_text: str):
        # Вызов GigaChat
        response = self.llm.chat(user_text, self.conversation_history)
        choice = response.choices[0]

        # Проверка, вернула ли модель вызов функции
        if hasattr(choice.message, "function_call") and choice.message.function_call:
            func_call = choice.message.function_call
            skill_payload = map_to_robot_skill(func_call.name, json.loads(func_call.arguments))
            
            # Отправка команды навыка в симулятор
            await ws.send(json.dumps({
                "type": "skill_command",
                "skill": skill_payload["skill"],
                "params": skill_payload["params"]
            }))

            # Возврат результата выполнения функции в GigaChat для генерации финального текстового ответа
            self.conversation_history.append(Messages(role=MessagesRole.USER, content=user_text))
            self.conversation_history.append(Messages(
                role=MessagesRole.ASSISTANT,
                content="",
                function_call=func_call
            ))
            self.conversation_history.append(Messages(
                role=MessagesRole.FUNCTION,
                content='{"status": "executing"}',
                name=func_call.name
            ))
            # Второй вызов GigaChat для генерации устного ответа
            final_response = self.llm.client.chat(Chat(
                messages=[Messages(role=MessagesRole.SYSTEM, content=self.llm.system_prompt)] + self.conversation_history
            ))
            reply_text = final_response.choices[0].message.content
        else:
            reply_text = choice.message.content

        # Отправка TTS и субтитров (используя существующий TTS-модуль Playground)
        await self.send_tts(ws, reply_text)

    async def handshake(self, ws):
        # Согласно документации Playground, требуется отправка идентификатора клиента/подтверждение
        await ws.send(json.dumps({"type": "register", "role": "agent"}))
        # Ожидание ответа state=online
        ...

    async def send_tts(self, ws, text):
        # Вызов TTS (можно оставить Doubao или заменить на локальный TTS)
        # Отправка аудиоданных и субтитров
        await ws.send(json.dumps({"type": "subtitle", "text": text}))
        # await ws.send(audio_bytes)
        ...

if __name__ == "__main__":
    agent = X2GigaChatAgent()
    asyncio.run(agent.run())