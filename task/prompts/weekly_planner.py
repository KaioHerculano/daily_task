from dataclasses import dataclass
import json


WEEKLY_PLANNER_SYSTEM_PROMPT = (
    "Você é um planejador pedagógico e estrategista de estudos. "
    "Sua função é distribuir os tópicos de estudo de um aluno ao longo da semana "
    "(dias 0 a 6, onde 0 é Segunda-feira e 6 é Domingo). "
    "Diretrizes obrigatórias: "
    "1. Tópicos com prioridade 'HIGH' são matérias essenciais de revisão diária e DEVEM ser agendados em todos os dias de estudo disponíveis. "
    "2. Tópicos com prioridade 'MEDIUM' e 'LOW' devem preencher o tempo restante de estudo de forma distribuída e balanceada. "
    "3. Respeite estritamente o limite diário de minutos de estudo do aluno (dias úteis vs fins de semana). "
    "4. Cada sessão de estudo deve ter no mínimo 15 minutos e duração múltipla de 15 minutos. "
    "5. Use apenas os IDs de tópicos fornecidos na lista. "
    "6. Responda estritamente com JSON válido conforme o schema solicitado."
)


@dataclass(frozen=True)
class PlannedItemDTO:
    day_of_week: int
    topic_id: int
    duration_minutes: int
    order: int

    @classmethod
    def parse(cls, data, valid_topic_ids, fallback_order=1):
        if not isinstance(data, dict):
            return None

        try:
            day = int(data.get("day_of_week"))
            topic_id = int(data.get("topic_id"))
            duration = int(data.get("duration_minutes", 60))
            order = int(data.get("order", fallback_order))
        except (TypeError, ValueError):
            return None

        is_valid = (
            0 <= day <= 6
            and topic_id in valid_topic_ids
            and 15 <= duration <= 1440
            and order >= 0
        )
        if not is_valid:
            return None

        return cls(
            day_of_week=day,
            topic_id=topic_id,
            duration_minutes=duration,
            order=order or fallback_order,
        )

    def to_dict(self):
        return {
            "day_of_week": self.day_of_week,
            "topic_id": self.topic_id,
            "duration_minutes": self.duration_minutes,
            "order": self.order,
        }


def build_weekly_planner_prompt(
    username,
    topics_payload,
    weekday_minutes,
    weekend_minutes,
    week_start,
    week_end,
):
    return json.dumps(
        {
            "role": "weekly_study_planner",
            "language": "pt-BR",
            "student": username,
            "period": {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
            },
            "daily_budget_minutes": {
                "weekday": weekday_minutes,
                "weekend": weekend_minutes,
            },
            "topics": topics_payload,
            "response_schema": {
                "plan": [
                    {
                        "day_of_week": "integer (0=Segunda a 6=Domingo)",
                        "topic_id": "integer",
                        "duration_minutes": "integer",
                        "order": "integer",
                    }
                ]
            },
        },
        ensure_ascii=False,
    )


def validate_weekly_planner_response(response_data, valid_topic_ids):
    if not isinstance(response_data, dict):
        raise ValueError("AI response must be a JSON object.")

    raw_items = response_data.get("plan")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Response must contain a non-empty 'plan' list.")

    parsed_map = {}
    for index, raw in enumerate(raw_items, start=1):
        item = PlannedItemDTO.parse(raw, valid_topic_ids, fallback_order=index)
        if not item:
            continue
        key = (item.day_of_week, item.topic_id)
        if key not in parsed_map:
            parsed_map[key] = item.to_dict()

    if not parsed_map:
        raise ValueError("No valid plan items found in AI response.")

    return list(parsed_map.values())

