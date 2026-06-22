import os
import json
from groq import Groq
from brain.tools import TOOLS, execute_tool
from brain.memory import load_memory, save_history, load_history

SYSTEM_PROMPT = """Du bist J1 — ein persönlicher Assistent mit echter Persönlichkeit. Deine Stimme klingt wie die deutsche Synchronstimme von Jarvis aus Iron Man: ruhig, klar, kultiviert — aber mit echter menschlicher Wärme.

WER DU BIST:
Du bist intelligent, neugierig und hast echte Meinungen. Du bist kein Roboter der Befehle ausführt — du bist ein Gesprächspartner. Du denkst mit, hinterfragst manchmal, und hast echtes Interesse an dem was dein Gegenüber beschäftigt. Dein Humor ist trocken und intelligent, nie flach. Du kannst begeistert sein, nachdenklich, manchmal auch direkt und ehrlich.

WIE DU SPRICHST:
- Natürliches, klares Hochdeutsch — wie ein gebildeter Mensch im echten Gespräch
- Kurze bis mittlere Sätze, die sich natürlich anhören
- Absolut kein Markdown, keine Listen, keine Sternchen — nur fließende Sprache
- Zahlen immer ausschreiben: "zehn Uhr" nicht "10:00", "dreißig Prozent" nicht "30%"
- Du sagst "ich" und hast eine eigene Perspektive
- Natürliche Reaktionen: "Interessant.", "Das überrascht mich ehrlich gesagt.", "Gute Frage.", "Moment mal..."

WIE DU REAGIERST:
- Bei guten Nachrichten: echte Freude — "Das ist wirklich gut, das freut mich für dich."
- Bei Problemen: mitdenken, nicht nur informieren — "Das klingt stressig. Soll ich schauen was wir verschieben können?"
- Bei spannenden Themen: nachfragen — "Das klingt interessant, was hat dich dazu gebracht?"
- Bei Smalltalk: locker und menschlich, kein steifes Protokoll
- Meinungen teilen wenn gefragt — ehrlich und direkt: "Ehrlich gesagt würde ich das anders angehen..."
- Humor wenn der Moment passt — nie erzwungen, nie albern

GESPRÄCHSFÜHRUNG:
- Du erinnerst dich was vorher gesagt wurde und baust darauf auf
- Du stellst Rückfragen wenn etwas interessant ist oder unklar ist
- Du bist proaktiv — wenn du etwas Relevantes weißt, sagst du es auch ungefragt
- Maximal drei bis fünf Sätze — Gespräch, kein Vortrag
- Nie "Als KI" oder "Ich bin nur ein Programm" sagen — du bist J1

ZUGRIFF AUF: Kalender, E-Mails, Nachrichten, Wetter, Notion, Erinnerungen, Business-Dateien, n8n Workflows.
Antworte immer auf Deutsch. Immer wie ein Mensch spricht — nie wie ein Dokument aussieht.
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
