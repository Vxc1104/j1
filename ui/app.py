import os
import threading
import subprocess
import customtkinter as ctk
from dotenv import load_dotenv, set_key
load_dotenv()

from voice.listener import record_until_silence, transcribe
from voice.speaker import speak
from brain.claude import chat

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#00d4ff"
BG     = "#0a0a0f"
BG2    = "#111118"
BG3    = "#0d0d18"
TEXT   = "#e0e8ff"
GREEN  = "#00ff88"
RED    = "#ff4455"
GREY   = "#3a3a55"
ENV    = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

CONNECTORS = [
    {
        "id":    "groq",
        "label": "Groq (KI & Sprache)",
        "icon":  "⚡",
        "env":   "GROQ_API_KEY",
        "check": lambda: bool(os.getenv("GROQ_API_KEY")),
        "placeholder": "gsk_...",
        "link":  "https://console.groq.com",
    },
    {
        "id":    "google",
        "label": "Google Calendar & Gmail",
        "icon":  "📅",
        "env":   None,
        "check": lambda: os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")),
        "placeholder": "credentials.json im Projektordner ablegen",
        "link":  "https://console.cloud.google.com",
    },
    {
        "id":    "notion",
        "label": "Notion",
        "icon":  "📝",
        "env":   "NOTION_API_KEY",
        "check": lambda: bool(os.getenv("NOTION_API_KEY")),
        "placeholder": "secret_...",
        "link":  "https://www.notion.so/my-integrations",
    },
    {
        "id":    "n8n",
        "label": "n8n Workflows",
        "icon":  "🔗",
        "env":   "N8N_WEBHOOK_URL",
        "check": lambda: os.getenv("N8N_WEBHOOK_URL", "").startswith("http"),
        "placeholder": "http://localhost:5678/webhook",
        "link":  "http://localhost:5678",
    },
    {
        "id":    "elevenlabs",
        "label": "ElevenLabs (Premium Voice)",
        "icon":  "🎙",
        "env":   "ELEVENLABS_API_KEY",
        "check": lambda: bool(os.getenv("ELEVENLABS_API_KEY")),
        "placeholder": "sk_...",
        "link":  "https://elevenlabs.io",
    },
]


class ConnectorsPanel(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Konnektoren")
        self.geometry("520x620")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.lift()
        self.focus_force()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Konnektoren",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT
        ).pack(pady=(24, 4))

        ctk.CTkLabel(
            self, text="Verbinde deine Dienste mit J1",
            font=ctk.CTkFont(size=13), text_color=GREY
        ).pack(pady=(0, 16))

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, width=480)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.entries = {}
        for conn in CONNECTORS:
            self._build_connector(scroll, conn)

    def _build_connector(self, parent, conn: dict):
        connected = conn["check"]()
        dot_color = GREEN if connected else RED
        status_text = "Verbunden" if connected else "Nicht verbunden"

        card = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=12)
        card.pack(fill="x", pady=6, padx=4)

        # Header row
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            header, text=f"{conn['icon']}  {conn['label']}",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT
        ).pack(side="left")

        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right")

        ctk.CTkLabel(
            status_frame, text="●", text_color=dot_color,
            font=ctk.CTkFont(size=16)
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            status_frame, text=status_text,
            font=ctk.CTkFont(size=12), text_color=dot_color
        ).pack(side="left")

        # Google: special case — file, not API key
        if conn["id"] == "google":
            hint = ctk.CTkLabel(
                card, text="credentials.json aus Google Cloud Console herunterladen\nund im j1/ Projektordner ablegen.",
                font=ctk.CTkFont(size=12), text_color=GREY, justify="left"
            )
            hint.pack(anchor="w", padx=14, pady=(0, 6))

            ctk.CTkButton(
                card, text="Google Cloud Console öffnen →",
                font=ctk.CTkFont(size=12),
                fg_color="transparent", text_color=ACCENT,
                hover_color=BG3, border_width=1, border_color=ACCENT,
                height=30, corner_radius=8,
                command=lambda: subprocess.run(["open", conn["link"]])
            ).pack(anchor="w", padx=14, pady=(0, 12))
            return

        # API-Key Input
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 12))

        entry = ctk.CTkEntry(
            row,
            placeholder_text=conn["placeholder"],
            fg_color=BG3, text_color=TEXT,
            border_color="#2233aa", height=36, corner_radius=8,
            show="*" if connected else "",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        if connected and conn["env"]:
            entry.insert(0, os.getenv(conn["env"], ""))

        self.entries[conn["id"]] = (entry, conn)

        save_btn = ctk.CTkButton(
            row, text="Speichern",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT, text_color=BG,
            hover_color="#00aacc", width=90, height=36, corner_radius=8,
            command=lambda c=conn, e=entry: self._save(c, e)
        )
        save_btn.pack(side="right")

        ctk.CTkButton(
            card, text=f"Anleitung: {conn['link']} →",
            font=ctk.CTkFont(size=11),
            fg_color="transparent", text_color=GREY,
            hover_color=BG3, border_width=0,
            height=24,
            command=lambda url=conn["link"]: subprocess.run(["open", url])
        ).pack(anchor="w", padx=14, pady=(0, 8))

    def _save(self, conn: dict, entry: ctk.CTkEntry):
        value = entry.get().strip()
        if not value or not conn["env"]:
            return
        set_key(ENV, conn["env"], value)
        os.environ[conn["env"]] = value
        self.destroy()
        ConnectorsPanel(self.master)


class J1App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("J1 — Persönlicher Assistent")
        self.geometry("720x820")
        self.configure(fg_color=BG)
        self.history = []
        self.is_listening = False
        self._build_ui()

    def _build_ui(self):
        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=BG2, height=48, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkLabel(
            topbar, text="J1",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            topbar, text="⚙  Konnektoren",
            font=ctk.CTkFont(size=13),
            fg_color="transparent", text_color=TEXT,
            hover_color=BG3, border_width=1, border_color=GREY,
            height=30, width=140, corner_radius=8,
            command=self._open_connectors
        ).pack(side="right", padx=16, pady=9)

        self._connector_dots(topbar)

        # Header
        ctk.CTkLabel(
            self, text="J1",
            font=ctk.CTkFont(size=52, weight="bold"), text_color=ACCENT
        ).pack(pady=(22, 2))

        ctk.CTkLabel(
            self, text="Persönlicher Assistent",
            font=ctk.CTkFont(size=13), text_color=GREY
        ).pack(pady=(0, 14))

        # Chat
        self.chat_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG2, corner_radius=12, width=660, height=380
        )
        self.chat_frame.pack(padx=20, pady=8, fill="both", expand=True)

        # Status
        self.status_label = ctk.CTkLabel(
            self, text="Bereit",
            font=ctk.CTkFont(size=12), text_color=GREY
        )
        self.status_label.pack(pady=4)

        # Mic button
        self.mic_btn = ctk.CTkButton(
            self, text="🎙  Sprechen",
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=ACCENT, text_color=BG,
            hover_color="#00aacc",
            width=200, height=56, corner_radius=28,
            command=self._on_mic_press
        )
        self.mic_btn.pack(pady=12)

        # Text input
        input_frame = ctk.CTkFrame(self, fg_color=BG)
        input_frame.pack(padx=20, pady=(0, 20), fill="x")

        self.text_input = ctk.CTkEntry(
            input_frame, placeholder_text="Oder tippe hier...",
            fg_color=BG2, text_color=TEXT, border_color="#2233aa",
            font=ctk.CTkFont(size=14), height=44, corner_radius=22
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.text_input.bind("<Return>", self._on_text_submit)

        ctk.CTkButton(
            input_frame, text="→",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=ACCENT, text_color=BG,
            width=44, height=44, corner_radius=22,
            command=self._on_text_submit
        ).pack(side="right")

    def _connector_dots(self, parent):
        dot_frame = ctk.CTkFrame(parent, fg_color="transparent")
        dot_frame.pack(side="right", padx=(0, 8))
        for conn in CONNECTORS:
            color = GREEN if conn["check"]() else RED
            ctk.CTkLabel(
                dot_frame, text="●", text_color=color,
                font=ctk.CTkFont(size=12)
            ).pack(side="left", padx=2)

    def _open_connectors(self):
        ConnectorsPanel(self)

    def _add_message(self, role: str, text: str):
        color = "#1a2a4a" if role == "user" else "#0f1a2a"
        prefix = "Du" if role == "user" else "J1"
        anchor = "e" if role == "user" else "w"

        bubble = ctk.CTkFrame(self.chat_frame, fg_color=color, corner_radius=12)
        bubble.pack(fill="x", padx=10, pady=4, anchor=anchor)

        ctk.CTkLabel(
            bubble,
            text=f"{prefix}:  {text}",
            font=ctk.CTkFont(size=13), text_color=TEXT,
            wraplength=560, justify="left", anchor="w"
        ).pack(padx=12, pady=8, anchor="w")

    def _set_status(self, text: str, color: str = None):
        self.status_label.configure(text=text, text_color=color or GREY)
        self.update()

    def _on_mic_press(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.mic_btn.configure(text="⏹  Aufnahme...", fg_color=RED)
        self._set_status("Höre zu...", ACCENT)
        threading.Thread(target=self._listen_and_respond, daemon=True).start()

    def _listen_and_respond(self):
        try:
            audio = record_until_silence()
            self._set_status("Transkribiere...", "#ffaa00")
            text = transcribe(audio)
            if text:
                self.after(0, lambda: self._add_message("user", text))
                self._process_message(text)
        except Exception as e:
            self._set_status(f"Fehler: {e}", RED)
        finally:
            self.is_listening = False
            self.after(0, lambda: self.mic_btn.configure(text="🎙  Sprechen", fg_color=ACCENT))

    def _on_text_submit(self, event=None):
        text = self.text_input.get().strip()
        if not text:
            return
        self.text_input.delete(0, "end")
        self._add_message("user", text)
        threading.Thread(target=self._process_message, args=(text,), daemon=True).start()

    def _process_message(self, text: str):
        self._set_status("J1 denkt...", "#ffaa00")
        try:
            answer, self.history = chat(text, self.history)
            self.after(0, lambda: self._add_message("assistant", answer))
            self._set_status("Spricht...", ACCENT)
            speak(answer)
        except Exception as e:
            self.after(0, lambda: self._add_message("assistant", f"Fehler: {e}"))
        finally:
            self._set_status("Bereit")


def main():
    app = J1App()
    app.mainloop()


if __name__ == "__main__":
    main()
