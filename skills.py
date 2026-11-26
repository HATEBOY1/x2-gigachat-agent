# skills.py
from gigachat.models import Function, FunctionParameters

# Определение функции для GigaChat
robot_functions = [
    Function(
        name="wave_hands",
        description="Заставить робота помахать руками, подходит для приветствия или прощания",
        parameters=FunctionParameters(type="object", properties={}, required=[])
    ),
    Function(
        name="walk_forward",
        description="Заставить робота идти вперед на указанное расстояние",
        parameters=FunctionParameters(
            type="object",
            properties={
                "distance_m": {"type": "number", "description": "Расстояние в метрах, например 1.0"}
            },
            required=["distance_m"]
        )
    ),
    Function(
        name="turn",
        description="Повернуть робота, положительное значение — вправо, отрицательное — влево",
        parameters=FunctionParameters(
            type="object",
            properties={
                "angle_deg": {"type": "number", "description": "Угол поворота в градусах"}
            },
            required=["angle_deg"]
        )
    ),
    Function(
        name="set_emotion",
        description="Установить выражение лица робота",
        parameters=FunctionParameters(
            type="object",
            properties={
                "emotion": {"type": "string", "enum": ["happy", "sad", "neutral"], "description": "Тип выражения"}
            },
            required=["emotion"]
        )
    ),
    Function(
        name="stop",
        description="Немедленно остановить все движения робота",
        parameters=FunctionParameters(type="object", properties={}, required=[])
    ),
]

# Сопоставление имени функции GigaChat с payload навыка WebSocket протокола Playground
def map_to_robot_skill(function_name: str, args: dict) -> dict:
    mapping = {
        "wave_hands": {"skill": "gesture/wave_hands", "params": {}},
        "walk_forward": {"skill": "movement/walk", "params": {"distanceM": args.get("distance_m", 1.0)}},
        "turn": {"skill": "movement/turn", "params": {"angleDeg": args.get("angle_deg", 0)}},
        "set_emotion": {"skill": "emotion/" + args.get("emotion", "neutral"), "params": {}},
        "stop": {"skill": "movement/stop", "params": {}},
    }
    return mapping.get(function_name)