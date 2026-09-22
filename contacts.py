#!/usr/bin/env python3
"""Извлечение контакта из свободного текста — то, на чём ломается приём заявок.

Люди пишут телефон как угодно: «+7 (912) 345-67-89», «89123456789», «912 345 6789»,
«восемь девятьсот...», с приписками «звоните после 18». Имя приходит в том же
сообщении и без разделителя. Всё это надо разобрать, иначе заявка уходит менеджеру
без номера и теряется.
"""
import re

# Телефон: 11 цифр с 7/8 впереди либо 10 цифр начиная с 9.
PHONE_CHARS = re.compile(r"[\d\-\s()+.]{10,25}")
DIGITS = re.compile(r"\d")
WORD_DIGITS = {
    "ноль": "0", "один": "1", "два": "2", "три": "3", "четыре": "4",
    "пять": "5", "шесть": "6", "семь": "7", "восемь": "8", "девять": "9",
}
NAME_MARKERS = re.compile(
    r"(?:меня зовут|это|я|мо[её] имя)\s+([А-ЯЁ][а-яё]{2,15})", re.I)
NAME_SOLO = re.compile(r"\b([А-ЯЁ][а-яё]{2,15})\b")
NOT_NAMES = {"Здравствуйте", "Добрый", "Привет", "Спасибо", "Хочу", "Можно",
             "Нужен", "Нужна", "Нужно", "Надо", "Когда", "Сколько", "Записаться",
             "Перезвоните", "Позвоните", "Балкон", "Окна", "Лоджия", "Меня",
             "Телефон", "Номер", "Остекление", "Отделка", "Замер", "Свяжитесь",
             "Интересует", "Подскажите", "Хотел", "Хотела", "Ещё", "Еще"}


def normalize_phone(raw):
    d = "".join(DIGITS.findall(raw))
    if len(d) == 11 and d[0] in "78":
        d = "7" + d[1:]
    elif len(d) == 10 and d[0] == "9":
        d = "7" + d
    else:
        return None
    return "+" + d


def words_to_phone(text):
    """«восемь девятьсот двенадцать...» — редко, но встречается в голосовых расшифровках."""
    found = []
    for w in re.findall(r"[а-яё]+", text.lower()):
        if w in WORD_DIGITS:
            found.append(WORD_DIGITS[w])
    return normalize_phone("".join(found)) if len(found) >= 10 else None


# Сначала ищем номер по форме, а не первую попавшуюся цепочку цифр: в сообщении
# рядом стоят метраж, бюджет, номер дома и часы работы, и «до 150000» легко принять
# за телефон. Поэтому кандидаты сортируем — сперва те, что начинаются с +7, 8 или 9.
STRICT_PHONE = re.compile(
    r"(?:\+7|\b8|\b7)[\s\-.()]*\d{3}[\s\-.()]*\d{3}[\s\-.()]*\d{2}[\s\-.()]*\d{2}"
    r"|\b9\d{2}[\s\-.()]*\d{3}[\s\-.()]*\d{2}[\s\-.()]*\d{2}\b")


def extract_phone(text):
    m = STRICT_PHONE.search(text)
    if m:
        phone = normalize_phone(m.group(0))
        if phone:
            return phone
    for chunk in PHONE_CHARS.findall(text):
        phone = normalize_phone(chunk)
        if phone:
            return phone
    return words_to_phone(text)


def extract_name(text, has_phone=None):
    """Имя по маркеру берём всегда. Одиночное слово с заглавной — только если
    в этом же сообщении есть телефон: «Андрей, 8912...» — имя, а «Нужно
    остекление» — начало фразы, и принимать его за имя нельзя."""
    m = NAME_MARKERS.search(text)
    if m and m.group(1) not in NOT_NAMES:
        return m.group(1)
    if has_phone is None:
        has_phone = bool(extract_phone(text))
    if not has_phone:
        return None
    for cand in NAME_SOLO.findall(text):
        if cand not in NOT_NAMES:
            return cand
    return None


def parse(text):
    phone = extract_phone(text)
    return {"phone": phone, "name": extract_name(text, has_phone=bool(phone))}


if __name__ == "__main__":
    samples = [
        "Здравствуйте! Меня зовут Ирина, нужен замер балкона, +7 (912) 345-67-89",
        "89123456789 Андрей, перезвоните после 18",
        "можно записаться? 912 345 6789",
        "Телефон восемь девять один два три четыре пять шесть семь восемь девять",
        "Сколько стоит остекление 6 метров?",
    ]
    for s in samples:
        print(f"{s[:55]:57s} → {parse(s)}")
