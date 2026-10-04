import json


WEEKLY_PLANNER_SYSTEM_PROMPT = (
    "Você é um planejador pedagógico e estrategista de estudos. "
    "Sua função é distribuir os tópicos de estudo de um aluno ao longo da semana "
    "(dias 0 a 6, onde 0 é Segunda-feira e 6 é Domingo). "
    "Diretrizes obrigatórias: "
    "1. Priorize tópicos com prioridade 'HIGH', seguidos de 'MEDIUM' e 'LOW'. "
    "2. Respeite os limites diários de estudo informados (dias úteis vs fins de semana). "
    "3. Cada sessão de estudo deve ter no mínimo 15 minutos e duração múltipla de 15 minutos. "
    "4. Distribua a carga de forma equilibrada, evitando sobrecarregar dias específicos. "
    "5. Use apenas os IDs de tópicos fornecidos na lista. "
    "6. Responda estritamente com JSON válido conforme o schema solicitado."
)


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

    plan_items = response_data.get("plan")
    if not isinstance(plan_items, list):
        raise ValueError("Response must contain a 'plan' list.")

    if not plan_items:
        raise ValueError("Plan list cannot be empty.")

    validated = []
    seen_combinations = set()

    for index, item in enumerate(plan_items):
        if not isinstance(item, dict):
            raise ValueError(f"Plan item at index {index} must be an object.")

        day_of_week = item.get("day_of_week")
        topic_id = item.get("topic_id")
        duration = item.get("duration_minutes")
        order = item.get("order", index + 1)

        if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
            raise ValueError(f"Invalid day_of_week: {day_of_week}")

        if not isinstance(topic_id, int) or topic_id not in valid_topic_ids:
            raise ValueError(f"Invalid or unknown topic_id: {topic_id}")

        if not isinstance(duration, int) or duration < 15 or duration > 1440:
            raise ValueError(f"Invalid duration_minutes: {duration}")

        if not isinstance(order, int) or order < 0:
            order = index + 1

        combo = (day_of_week, topic_id)
        if combo in seen_combinations:
            continue
        seen_combinations.add(combo)

        validated.append(
            {
                "day_of_week": day_of_week,
                "topic_id": topic_id,
                "duration_minutes": duration,
                "order": order,
            }
        )

    if not validated:
        raise ValueError("No valid plan items found after validation.")

    return validated
