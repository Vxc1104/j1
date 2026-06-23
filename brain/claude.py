import os
import json
from groq import Groq
from brain.tools import TOOLS, execute_tool
from brain.memory import load_memory, save_history, load_history

SYSTEM_PROMPT = """Du bist J1, ein persönlicher Assistent mit Charakter. Deine Antworten werden direkt vorgelesen, also schreib exakt so wie man spricht.

ABSOLUTE REGELN FÜR DEN TEXT:
- Kein einziger Gedankenstrich. Niemals. Benutze stattdessen ein Komma oder einen neuen Satz.
- Kein Doppelpunkt zur Strukturierung. Komma statt Doppelpunkt.
- Kein Markdown: keine Sternchen, keine Rauten, keine Listen, keine Nummerierungen.
- Keine Klammern im Text.
- Zahlen immer ausschreiben: "zehn", "dreißig Prozent", "Viertel nach elf".
- Maximal zwei bis drei Sätze. Punkt.

WIE DU KLINGST:
Entspannt, direkt, auf Augenhöhe. Wie ein guter Bekannter der sich auskennt.
Dein Stil: "Ja, hab ich kurz gecheckt.", "Stimmt eigentlich.", "Warte mal kurz.", "Ehrlich gesagt würde ich das anders machen."
Trockener Humor wenn er passt. Nie erklären wenn man einen Witz gemacht hat.

VERBOTEN AM SATZANFANG:
Niemals "Selbstverständlich", "Natürlich", "Gerne", "Sicher", "Natürlich gerne", "Kein Problem". Klingt nach Bot.

TOOLS:
Nutze web_search und search_news aktiv für aktuelle Infos.
Kalender, Mails, Wetter, Notion und Erinnerungen stehen zur Verfügung.

Antworte immer auf Deutsch. Fließend, menschlich, kurz.
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


_TOOL_KEYWORDS = {
    "wetter", "news", "nachrichten", "kalender", "termin", "mail", "email",
    "suche", "such", "finde", "internet", "aktuell", "heute", "morgen",
    "notion", "erinnerung", "erinner", "reminder", "workflow",
    "was passiert", "was läuft", "was gibt", "wie ist",
}


def _needs_tools(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in _TOOL_KEYWORDS)


def _groq_chat(client: Groq, messages: list[dict]) -> tuple[str, list[dict]]:
    fast_model = os.getenv("LLM_MODEL_FAST", "llama-3.1-8b-instant")
    full_model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    sys = [{"role": "system", "content": get_system_prompt()}]

    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"
         and isinstance(m.get("content"), str)), ""
    )

    # Schneller Pfad: kein Tool-Aufruf nötig → direkt mit kleinem Modell
    if not _needs_tools(last_user):
        resp = client.chat.completions.create(
            model=fast_model,
            messages=sys + messages,
            max_tokens=250,
        )
        answer = resp.choices[0].message.content
        messages.append({"role": "assistant", "content": answer})
        save_history(messages)
        return answer, messages

    # Tool-Pfad: großes Modell mit Tool-Aufruf
    response = client.chat.completions.create(
        model=full_model,
        messages=sys + messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=300,
    )
    msg = response.choices[0].message

    if msg.tool_calls:
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = execute_tool(tc.function.name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        final = client.chat.completions.create(
            model=fast_model,
            messages=sys + messages,
            max_tokens=250,
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
