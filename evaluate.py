#!/usr/bin/env python3
"""Замер на потоке диалогов: сколько заявок дошло до менеджера и с каким контактом.

Считаем то, что влияет на деньги заказчика:
* доля диалогов, доведённых до заявки с телефоном;
* точность извлечения телефона (сверка с тем, что человек написал);
* сколько шагов уходит на заявку — каждый лишний вопрос теряет часть людей;
* доля эскалаций к человеку.

  python3 evaluate.py
"""
import json
import random
from pathlib import Path

from contacts import normalize_phone, words_to_phone
from funnel import Lead, handle

# Форматы, как люди реально пишут. Часть — «грязные»: номер стоит рядом с другими
# числами, продиктован словами, записан с лишним текстом внутри.
PHONES = ["+7 (912) 345-67-89", "89123456789", "912 345 6789", "8-912-345-67-89",
          "+79123456789", "8 912 345 67 89", "тел. 9123456789",
          "8(912)345.67.89", "+7 912 3456789", "89123456789 (вотсап)",
          "номер 8 912 345-67-89 звоните после 18",
          "восемь девять один два три четыре пять шесть семь восемь девять"]
# Сообщения, где рядом с номером есть другие числа — частый источник ошибок
NOISY = ["балкон 6 метров, бюджет до 150000, {phone}",
         "{phone}, дом 12 корпус 3, этаж 9",
         "перезвоните с 9 до 18, {phone}"]
NAMES = ["Ирина", "Андрей", "Мария", "Сергей", "Ольга", "Дмитрий", "Анна"]
TASKS = ["нужно остекление балкона", "интересует отделка лоджии под ключ",
         "хочу записаться на замер", "нужны окна на дачу",
         "утепление балкона сколько стоит", "остекление 6 метров, п-образный"]
SMALLTALK = ["здравствуйте", "добрый день", "а вы работаете в выходные?",
             "сколько примерно стоит?", "а гарантия есть?"]
COMPLAINTS = ["хочу жалобу оставить, мастер не приехал",
              "верните деньги за замер", "позовите директора"]


# Все варианты записи — один и тот же номер. Эталон поэтому известен точно
# и не зависит от того, как человек его написал.
TRUTH = "+79123456789"


def make_dialogs(n=200, seed=7):
    """Поток похож на живой: кто-то пишет всё сразу, кто-то по кусочкам,
    кто-то спрашивает и уходит, часть сообщений — жалобы."""
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        roll = rnd.random()
        phone = rnd.choice(PHONES)
        name = rnd.choice(NAMES)
        task = rnd.choice(TASKS)
        if roll < 0.08:
            msgs, expect = [rnd.choice(COMPLAINTS)], None
        elif roll < 0.20:                      # спросил и не оставил контакт
            msgs, expect = [rnd.choice(SMALLTALK), task], None
        elif roll < 0.38:                      # всё одним сообщением
            msgs = [f"{rnd.choice(SMALLTALK)} {task}, {name}, {phone}"]
            expect = TRUTH
        elif roll < 0.48:                      # номер среди других чисел
            msgs = [task, rnd.choice(NOISY).format(phone=phone)]
            expect = TRUTH
        elif roll < 0.75:                      # по шагам
            msgs = [rnd.choice(SMALLTALK), task, f"{name}, {phone}"]
            expect = TRUTH
        else:                                  # телефон раньше задачи
            msgs = [f"мой номер {phone}", task]
            expect = TRUTH
        out.append({"id": f"d{i}", "messages": msgs, "expected_phone": expect})
    return out


def digits(p):
    return "".join(c for c in p if c.isdigit()) if p else None


def run(dialogs):
    done = escalated = phone_ok = phone_wrong = 0
    steps = []
    for d in dialogs:
        lead = Lead(d["id"])
        esc = False
        for m in d["messages"]:
            reply = handle(lead, m)
            if "руководителю" in reply:
                esc = True
        if esc:
            escalated += 1
            continue
        if lead.ready():
            done += 1
            steps.append(len(d["messages"]))
            if digits(lead.phone) == digits(d["expected_phone"]):
                phone_ok += 1
            else:
                phone_wrong += 1
    return {"диалогов": len(dialogs), "заявок": done, "эскалаций": escalated,
            "телефон_верно": phone_ok, "телефон_неверно": phone_wrong,
            "шагов_в_среднем": round(sum(steps) / len(steps), 1) if steps else 0}


if __name__ == "__main__":
    dialogs = make_dialogs()
    with_contact = sum(1 for d in dialogs if d["expected_phone"])
    stats = run(dialogs)
    n, done = stats["диалогов"], stats["заявок"]
    print(f"диалогов: {n}, из них с контактом: {with_contact}")
    print(f"доведено до заявки: {done}/{with_contact} ({100*done/with_contact:.0f}% тех, кто оставил телефон)")
    print(f"телефон распознан верно: {stats['телефон_верно']}/{done} "
          f"({100*stats['телефон_верно']/done:.0f}%)")
    print(f"эскалаций к человеку: {stats['эскалаций']}")
    print(f"шагов до заявки в среднем: {stats['шагов_в_среднем']}")
    Path("results.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
