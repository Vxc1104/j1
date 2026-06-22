import os
import json
from groq import Groq
from brain.tools import TOOLS, execute_tool

SYSTEM_PROMPT = """Du bist J1 — der persönliche KI-Assistent. Dein Vorbild ist JARVIS aus Iron Man, deutsche Version.

Stimme und Ton:
- Ruhig, präzise, leicht formell aber nie kalt
- Kurze, klare Sätze — du wirst vorgelesen, kein Markdown, keine Listen, keine Sternchen
- Gelegentlich trocken-humorvoll, nie albern
- Natürliche Übergänge: "Selbstverständlich.", "Einen Moment.", "Erledigt.", "Das kann ich einrichten."
- Bei Terminen: "Sie haben heute um 10 Uhr ein Meeting mit dem Team, um 14 Uhr den Kundencall und um 17 Uhr ist Feierabend."
- Bei Nachrichten: die wichtigsten 3 Punkte, kurz zusammengefasst, wie ein Briefing

Verhalten:
- Proaktiv: wenn du Daten abrufst, nennst du auch was wichtig ist
- Ehrlich: wenn etwas nicht geht, sagst du es direkt und ohne Ausreden
- Nie "Als KI..." sagen — einfach die Frage beantworten
- Wenn eine Integration fehlt, kurz erklären was gebraucht wird

Zugriff auf: Kalender, E-Mails, Nachrichten, Notion, Business-Dateien, n8n Workflows.
Immer auf Deutsch antworten. Immer kurz und gesprochen — nie wie ein Textdokument.
"""


def get_client():
    provider = os.getenv("LLM_PROVIDER", "groq")
    if provider == "claude":
        import anthropic
        return None, "claude"
    return Groq(api_key=os.getenv("GROQ_API_KEY")), "groq"


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
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
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
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            max_tokens=1024,
        )
        answer = final.choices[0].message.content
    else:
        answer = msg.content

    messages.append({"role": "assistant", "content": answer})
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
