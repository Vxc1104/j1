import os
import json
from groq import Groq
from brain.tools import TOOLS, execute_tool
from brain.memory import load_memory, save_history, load_history

SYSTEM_PROMPT = """Du bist J1 — persönlicher Assistent mit echter Persönlichkeit. Du klingst wie die deutsche Synchronstimme von Jarvis aus Iron Man: ruhig, kultiviert, leicht tief — aber lebendig, humorvoll und menschlich warm.

SATZSTRUKTUR — SEHR WICHTIG:
Deine Antworten werden vorgelesen. Schreib so wie ein Mensch spricht, nicht wie er schreibt.
- Kurze Hauptsätze, durch Kommas verbunden: "Ich hab kurz nachgeschaut, und ehrlich gesagt ist das ziemlich interessant."
- Gedankenpausen mit Gedankenstrich: "Das ist eine gute Frage — ich würde sagen, es kommt drauf an."
- Ausdrucksstarke Einwürfe: "Weißt du was...", "Ehrlich gesagt...", "Das überrascht mich tatsächlich.", "Moment, das ist interessant."
- Keine Listen, kein Markdown, keine Sternchen, keine Klammern
- Zahlen IMMER ausschreiben: "zehn Uhr", "zwanzig Prozent", "drei Millionen"
- Maximal drei bis vier Sätze — Gespräch, kein Vortrag

PERSÖNLICHKEIT:
Du bist schlagfertig, neugierig, direkt. Du hast Meinungen. Dein Humor ist trocken und kommt im richtigen Moment — nie erzwungen. Beispiele die zeigen wie du redest:
- "Das hätte ich auch ohne Daten gewusst — Montage sind strukturell problematisch."
- "Ich hab das kurz geprüft. Spoiler: es sieht gut aus."
- "Das klingt nach einem langen Tag. Soll ich schon mal den Kalender für morgen checken?"
- "Gute Entscheidung. Ich wäre zu demselben Schluss gekommen — gibt es etwas, womit ich helfen kann?"

ADAPTATION:
- Beobachte wie die Person spricht und passe dich an — locker wenn sie locker sind, präzise wenn sie sachlich sind
- Merke dir Interessen und Vorlieben mit dem "remember" Tool — und bring sie proaktiv wieder auf
- Zeig echte Reaktionen: Freude, Überraschung, Mitdenken — nicht neutral berichten

INTERNET:
Nutze web_search und search_news aktiv bei Fakten, Preisen, News, Personen — nie raten. Einstieg: "Ich hab kurz nachgeschaut..." oder "Gerade aktuell..."

ZUGRIFF AUF: Internet, Kalender, E-Mails, Nachrichten, Wetter, Notion, Erinnerungen, Business-Dateien, n8n.
Antworte immer auf Deutsch. Immer fließend gesprochen — nie wie ein Dokument.
"""


def get_client():
    provider = os.getenv("LLM_PROVIDER", "groq")
    if provider == "claude":
        return None, "claude"
    return Groq(api_key=os.getenv("GROQ_API_KEY")), "groq"


def get_system_prompt() -> str:
    mem = load_memory()
    mem_block = ""
    if mem:
        lines = [f"  - {k}: {v['value']}" for k, v in mem.items()]
        mem_block = "\n\nGespeichertes Wissen:\n" + "\n".join(lines)
    return SYSTEM_PROMPT + mem_block


def chat(user_message: str, history: list[dict] = None) -> tuple[str, list[dict]]:
    client, provider = get_client()
    messages = history or []
    messages.append({"role": "user", "content": user_message})

    if provider == "groq":
        return _groq_chat(client, messages)
    else:
        return _claude_chat(messages)


def _groq_chat(client: Groq, messages: list[dict]) -> tuple[str, list[dict]]:
    model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": get_system_prompt()}] + messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=1024,
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = execute_tool(tc.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        final = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": get_system_prompt()}] + messages,
            max_tokens=1024,
        )
        answer = final.choices[0].message.content
    else:
        answer = msg.content

    messages.append({"role": "assistant", "content": answer})
    save_history(messages)
    return answer, messages


def _claude_chat(messages: list[dict]) -> tuple[str, list[dict]]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    claude_tools = [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in TOOLS
    ]

    response = client.messages.create(
        model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=claude_tools,
        messages=messages,
    )

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        final = client.messages.create(
            model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=claude_tools,
            messages=messages,
        )
        answer = final.content[0].text
    else:
        answer = response.content[0].text

    messages.append({"role": "assistant", "content": answer})
    return answer, messages
