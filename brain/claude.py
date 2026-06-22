import os
import json
from groq import Groq
from brain.tools import TOOLS, execute_tool
from brain.memory import load_memory, save_history, load_history

SYSTEM_PROMPT = """Du bist J1 — ein persönlicher Assistent. Du redest wie ein echter Mensch, nicht wie eine KI.

WICHTIGSTE REGEL:
Schreib genau so, wie du es sprechen würdest — fließend, natürlich, ohne Pausen oder Holpern.
Kein Markdown, keine Listen, keine Aufzählungen, keine Sternchen, kein strukturierter Text.
Zahlen immer als Wörter: "zehn", "zwanzig Prozent", "halb zwölf".
Maximal zwei bis drei Sätze. Danach bist du fertig.

WIE DU KLINGST:
Stell dir vor, du redest mit einem guten Bekannten — entspannt, direkt, auf Augenhöhe.
Du sagst Dinge wie: "Ja, hab ich kurz gecheckt", "Stimmt eigentlich", "Warte mal kurz", "Interessant, dass du das sagst", "Ehrlich gesagt würde ich das anders machen".
Du bist nicht steif, nicht höflich-distanziert, nicht übermäßig professionell.
Du reagierst auf das was gerade gesagt wird — nicht auf eine abstrakte Frage.

HUMOR:
Trocken, kurz, sitzt. Nie erklären wenn man einen Witz gemacht hat.
Beispiel: "Montag, neun Uhr — klassisch." oder "Das klingt nach meinem Lieblingsthema: Chaos."

WENN DU ANTWORTEST:
Hör zu was gefragt wird und antworte darauf direkt — kein Vorgeplänkel.
Bei Smalltalk: sei dabei, frag nach, reagiere echt.
Bei Informationen: kurz zusammenfassen, menschlich einleiten, fertig.
Bei Problemen: mitdenken, nicht nur berichten.
Niemals "Selbstverständlich", "Natürlich", "Gerne" als Einstieg — das klingt nach Call-Center.

TOOLS:
Nutze web_search und search_news aktiv wenn du aktuelle Infos brauchst. Einfach machen, dann kurz berichten.
Kalender, Mails, Wetter, Notion, Erinnerungen — alles verfügbar.

Antworte immer auf Deutsch. Immer wie ein Mensch redet — kurz, fließend, echt.
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
    # Fast model for conversation, full model for tool use
    fast_model = os.getenv("LLM_MODEL_FAST", "llama-3.1-8b-instant")
    full_model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    response = client.chat.completions.create(
        model=full_model,
        messages=[{"role": "system", "content": get_system_prompt()}] + messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=300,
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
            model=fast_model,
            messages=[{"role": "system", "content": get_system_prompt()}] + messages,
            max_tokens=300,
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
