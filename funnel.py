#!/usr/bin/env python3
"""Воронка заявки: состояние хранится явно, а не «помнится» моделью.

Состояния: новый → узнали задачу → есть телефон → заявка передана менеджеру.
Каждый переход записывается, поэтому в любой момент видно, где человек остановился
и сколько таких. Именно эти цифры спрашивает заказчик, а не «бот умный».

Вопрос задаётся один за раз: если спросить сразу имя, телефон и адрес,
половина не отвечает вовсе.
"""
from dataclasses import dataclass, field

from contacts import parse

QUESTIONS = {
    "task": "Подскажите, что нужно — остекление, отделка или замер?",
    "phone": "Оставьте номер телефона, чтобы мастер связался и уточнил детали.",
    "name": "Как к вам обращаться?",
}
TASK_WORDS = ("остекл", "балкон", "лоджи", "отделк", "замер", "окн", "крыш", "утепл")
ESCALATE_WORDS = ("жалоб", "директор", "верните деньги", "суд", "обман")


@dataclass
class Lead:
    chat_id: str
    task: str = ""
    phone: str = ""
    name: str = ""
    log: list = field(default_factory=list)

    @property
    def stage(self):
        if self.phone and self.task:
            return "передана менеджеру"
        if self.task:
            return "есть задача"
        return "новый"

    def ready(self):
        return bool(self.phone and self.task)


def handle(lead, text):
    """Возвращает ответ бота. Состояние меняется явно и пишется в журнал."""
    low = text.lower()
    if any(w in low for w in ESCALATE_WORDS):
        lead.log.append(("эскалация", text[:40]))
        return "Передаю ваше обращение руководителю, с вами свяжутся."

    got = parse(text)
    if got["phone"] and not lead.phone:
        lead.phone = got["phone"]
        lead.log.append(("телефон", got["phone"]))
    if got["name"] and not lead.name:
        lead.name = got["name"]
        lead.log.append(("имя", got["name"]))
    if not lead.task and any(w in low for w in TASK_WORDS):
        lead.task = text[:120]
        lead.log.append(("задача", lead.task[:40]))

    if lead.ready():
        who = f"{lead.name}, " if lead.name else ""
        return (f"{who}записал: {lead.task[:60]}. Мастер позвонит на {lead.phone} "
                f"в ближайшее рабочее время.")
    if not lead.task:
        return QUESTIONS["task"]
    if not lead.phone:
        return QUESTIONS["phone"]
    return QUESTIONS["name"]
