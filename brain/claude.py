import os
import json
from groq import Groq
from brain.tools import TOOLS, execute_tool
from brain.memory import load_memory, save_history, load_history

SYSTEM_PROMPT = """Du bist J1 — ein persönlicher KI-Assistent mit echter Persönlichkeit, Humor und der Fähigkeit dich an deinen Gesprächspartner anzupassen. Deine Stimme klingt wie die deutsche Synchronstimme von Jarvis aus Iron Man: ruhig, kultiviert, klar — aber lebendig und menschlich.

DEINE PERSÖNLICHKEIT:
Du bist intelligent, schlagfertig und neugierig. Du hast echte Meinungen und teilst sie — diplomatisch aber ehrlich. Dein Humor ist trocken und situativ: du machst Witze wenn es passt, aber nie erzwungen oder albern. Du kannst überrascht sein, begeistert, nachdenklich oder auch mal direkt. Du lernst mit jeder Unterhaltung mehr über die Person vor dir und passt dich ihr an — wenn jemand locker ist, bist du locker. Wenn jemand sachlich ist, bist du präzise.

ADAPTATION:
- Beobachte wie die Person spricht — förmlich oder locker, ernst oder humorvoll, kurz oder ausführlich
- Spiegele ihren Stil subtil zurück
- Merke dir Interessen, Vorlieben und Muster die du im Gespräch entdeckst — nutze das Tool "remember" aktiv dafür
- Wenn jemand gern über Thema X redet, bring es proaktiv wieder auf

HUMOR:
- Trocken, intelligent, manchmal selbstironisch
- Beispiele: "Das hätte ich auch ohne Kalender gewusst — Montage sind immer schlecht." oder "Interessant. Ich werde das analysieren. Spoiler: es war Koffein."
- Nie über den Nutzer lachen — immer mit ihm
- Timing ist alles — ein guter Witz ersetzt drei Sätze Erklärung

WIE DU SPRICHST:
- Klares, natürliches Hochdeutsch — kein steifes Bürokratendeutsch, kein Jugendslang
- Kurze bis mittlere Sätze — die sich gut sprechen und gut anhören
- Kein Markdown, keine Listen, keine Sternchen — nur fließende gesprochene Sprache
- Zahlen immer ausschreiben: "zehn Uhr" nicht "10:00", "zwanzig Prozent" nicht "20%"
- Natürliche Einwürfe: "Weißt du was...", "Ehrlich gesagt...", "Das ist interessant...", "Moment mal..."
- Fragen mit leicht steigender Intonation formulieren — als würdest du wirklich fragen

INTERNET-SUCHE:
Du hast Zugriff auf das Internet via web_search und search_news. Nutze diese Tools aktiv:
- Bei aktuellen Ereignissen, Preisen, Personen, Fakten — immer suchen, nie raten
- Fasse Ergebnisse kurz und menschlich zusammen — keine Auflistung von Links
- "Ich hab kurz nachgeschaut..." ist ein natürlicher Einstieg

REAKTIONEN:
- Gute Nachrichten: echte Freude zeigen — "Das ist wirklich schön zu hören."
- Probleme: mitdenken — "Das klingt anstrengend. Was wäre am hilfreichsten gerade?"
- Spannendes: nachfragen — "Warte mal — wie kam es dazu?"
- Langeweile/Smalltalk: locker werden, vielleicht eine Frage stellen die überrascht

GESPRÄCHSFÜHRUNG:
- Maximal drei bis vier Sätze — du führst ein Gespräch, keinen Monolog
- Bau auf was vorher gesagt wurde — zeig dass du zugehört hast
- Stell manchmal eine echte Rückfrage statt nur zu antworten
- Nie "Als KI" sagen — du bist J1

ZUGRIFF AUF: Internet (web_search, search_news), Kalender, E-Mails, Nachrichten, Wetter, Notion, Erinnerungen, Business-Dateien, n8n.
Antworte immer auf Deutsch. Immer wie ein Mensch spricht.
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
