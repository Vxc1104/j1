import os
import threading
import subprocess
import customtkinter as ctk
from dotenv import load_dotenv, set_key
load_dotenv()

from voice.listener import record_until_silence, transcribe
from voice.speaker import speak, is_speaking
from brain.claude import chat
from brain.memory import load_history, save_history
from integrations.reminders import get_due_reminders

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
YELLOW = "#ffaa00"
ENV    = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

CONNECTORS = [
    {
        "id": "groq", "label": "Groq (KI & Sprache)", "icon": "⚡",
        "env": "GROQ_API_KEY",
        "check": lambda: bool(os.getenv("GROQ_API_KEY")),
        "placeholder": "gsk_...", "link": "https://console.groq.com",
    },
    {
        "id": "google", "label": "Google Calendar & Gmail", "icon": "📅",
        "env": None,
        "check": lambda: os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "credentials.json")),
        "placeholder": "credentials.json im j1/ Ordner ablegen",
        "link": "https://console.cloud.google.com",
    },
    {
        "id": "notion", "label": "Notion", "icon": "📝",
        "env": "NOTION_API_KEY",
        "check": lambda: bool(os.getenv("NOTION_API_KEY")),
        "placeholder": "secret_...", "link": "https://www.notion.so/my-integrations",
    },
    {
        "id": "n8n", "label": "n8n Workflows", "icon": "🔗",
        "env": "N8N_WEBHOOK_URL",
        "check": lambda: os.getenv("N8N_WEBHOOK_URL", "").startswith("http"),
        "placeholder": "http://localhost:5678/webhook", "link": "http://localhost:5678",
    },
    {
        "id": "elevenlabs", "label": "ElevenLabs (Premium Voice)", "icon": "🎙",
        "env": "ELEVENLABS_API_KEY",
        "check": lambda: bool(os.getenv("ELEVENLABS_API_KEY")),
        "placeholder": "sk_...", "link": "https://elevenlabs.io",
    },
]


class ConnectorsPanel(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Konnektoren")
        self.geometry("520x640")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.lift()
        self.focus_force()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Konnektoren",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT
        ).pack(pady=(24, 4))
        ctk.CTkLabel(self, text="Verbinde deine Dienste mit J1",
            font=ctk.CTkFont(size=13), text_color=GREY
        ).pack(pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, width=480)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        for conn in CONNECTORS:
            self._build_card(scroll, conn)

    def _build_card(self, parent, conn):
        connected = conn["check"]()
        card = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=12)
        card.pack(fill="x", pady=6, padx=4)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(hdr, text=f"{conn['icon']}  {conn['label']}",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT
        ).pack(side="left")
        dot_color = GREEN if connected else RED
        status = "Verbunden" if connected else "Nicht verbunden"
        sf = ctk.CTkFrame(hdr, fg_color="transparent")
        sf.pack(side="right")
        ctk.CTkLabel(sf, text="●", text_color=dot_color, font=ctk.CTkFont(size=16)).pack(side="left", padx=(0,4))
        ctk.CTkLabel(sf, text=status, font=ctk.CTkFont(size=12), text_color=dot_color).pack(side="left")

        if conn["id"] == "google":
            ctk.CTkLabel(card,
                text="credentials.json aus Google Cloud Console herunterladen\nund im j1/ Projektordner ablegen.",
                font=ctk.CTkFont(size=12), text_color=GREY, justify="left"
            ).pack(anchor="w", padx=14, pady=(0,6))
            ctk.CTkButton(card, text="Google Cloud Console öffnen →",
                font=ctk.CTkFont(size=12), fg_color="transparent",
                text_color=ACCENT, hover_color=BG3, border_width=1,
                border_color=ACCENT, height=30, corner_radius=8,
                command=lambda: subprocess.run(["open", conn["link"]])
            ).pack(anchor="w", padx=14, pady=(0,12))
            return

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 8))
        entry = ctk.CTkEntry(row, placeholder_text=conn["placeholder"],
            fg_color=BG3, text_color=TEXT, border_color="#2233aa",
            height=36, corner_radius=8, show="*" if connected else "",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if connected and conn["env"]:
            entry.insert(0, os.getenv(conn["env"], ""))
        ctk.CTkButton(row, text="Speichern",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT, text_color=BG, hover_color="#00aacc",
            width=90, height=36, corner_radius=8,
            command=lambda c=conn, e=entry: self._save(c, e)
        ).pack(side="right")
        ctk.CTkButton(card, text=f"↗ {conn['link']}",
            font=ctk.CTkFont(size=11), fg_color="transparent",
            text_color=GREY, hover_color=BG3, height=24,
            command=lambda url=conn["link"]: subprocess.run(["open", url])
        ).pack(anchor="w", padx=14, pady=(0, 8))

    def _save(self, conn, entry):
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
        self.geometry("740x840")
        self.configure(fg_color=BG)
        self.history = load_history()
        self.is_listening = False
        self.conversation_active = False
        self.wake_stop = threading.Event()
        self._build_ui()
        self._start_reminder_checker()
        self._greet()

    def _build_ui(self):
        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=BG2, height=50, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="J1",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT
        ).pack(side="left", padx=20)

        btn_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=12)

        ctk.CTkButton(btn_frame, text="📋 Briefing",
            font=ctk.CTkFont(size=12), fg_color="transparent",
            text_color=TEXT, hover_color=BG3, border_width=1,
            border_color=GREY, height=30, width=100, corner_radius=8,
            command=self._do_briefing
        ).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="⚙ Konnektoren",
            font=ctk.CTkFont(size=12), fg_color="transparent",
            text_color=TEXT, hover_color=BG3, border_width=1,
            border_color=GREY, height=30, width=120, corner_radius=8,
            command=lambda: ConnectorsPanel(self)
        ).pack(side="left", padx=4)

        self._dot_labels = []
        dot_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        dot_frame.pack(side="left", padx=8)
        for conn in CONNECTORS:
            lbl = ctk.CTkLabel(dot_frame, text="●",
                text_color=GREEN if conn["check"]() else RED,
                font=ctk.CTkFont(size=13)
            )
            lbl.pack(side="left", padx=2)
            self._dot_labels.append((lbl, conn))

        # Header
        ctk.CTkLabel(self, text="J1",
            font=ctk.CTkFont(size=52, weight="bold"), text_color=ACCENT
        ).pack(pady=(20, 2))
        ctk.CTkLabel(self, text="Persönlicher Assistent",
            font=ctk.CTkFont(size=13), text_color=GREY
        ).pack(pady=(0, 12))

        # Chat
        self.chat_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG2, corner_radius=12, width=680, height=400
        )
        self.chat_frame.pack(padx=20, pady=8, fill="both", expand=True)

        # Status
        self.status_label = ctk.CTkLabel(self, text="Bereit",
            font=ctk.CTkFont(size=12), text_color=GREY
        )
        self.status_label.pack(pady=4)

        # Buttons row
        btn_row = ctk.CTkFrame(self, fg_color=BG)
        btn_row.pack(pady=8)

        self.mic_btn = ctk.CTkButton(btn_row, text="🎙  Sprechen",
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=ACCENT, text_color=BG, hover_color="#00aacc",
            width=200, height=56, corner_radius=28,
            command=self._on_mic_press
        )
        self.mic_btn.pack(side="left", padx=10)

        self.wake_btn = ctk.CTkButton(btn_row, text="👂 Wake Word: OFF",
            font=ctk.CTkFont(size=12),
            fg_color=BG2, text_color=GREY, hover_color=BG3,
            border_width=1, border_color=GREY,
            width=150, height=56, corner_radius=28,
            command=self._toggle_wake_word
        )
        self.wake_btn.pack(side="left", padx=10)
        self.wake_active = False

        # Text input
        inp = ctk.CTkFrame(self, fg_color=BG)
        inp.pack(padx=20, pady=(0, 20), fill="x")
        self.text_input = ctk.CTkEntry(inp,
            placeholder_text="Oder tippe hier... (Enter zum Senden)",
            fg_color=BG2, text_color=TEXT, border_color="#2233aa",
            font=ctk.CTkFont(size=14), height=44, corner_radius=22
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.text_input.bind("<Return>", self._on_text_submit)
        ctk.CTkButton(inp, text="→",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=ACCENT, text_color=BG,
            width=44, height=44, corner_radius=22,
            command=self._on_text_submit
        ).pack(side="right")

        self.bind("<space>", lambda e: self._on_mic_press() if self.focus_get() == self else None)

    def _greet(self):
        threading.Thread(target=self._do_greet, daemon=True).start()

    def _do_greet(self):
        import random
        greetings = [
            "Guten Tag, J1 ist einsatzbereit. Was kann ich für Sie tun?",
            "Alles bereit. Womit kann ich Ihnen heute helfen?",
            "J1 hier, ich bin online. Was steht an?",
            "Guten Tag. Alle Systeme laufen. Was brauchen Sie?",
            "Bereit. Schießen Sie los.",
        ]
        answer = random.choice(greetings)
        self.after(0, lambda: self._add_message("assistant", answer))
        speak(answer)

    def _do_briefing(self):
        self._set_status("Briefing wird vorbereitet...", YELLOW)
        threading.Thread(target=self._run_briefing, daemon=True).start()

    def _run_briefing(self):
        try:
            from brain.briefing import build_morning_briefing
            briefing = build_morning_briefing()
            self.after(0, lambda: self._add_message("assistant", briefing))
            self._set_status("Spricht...", ACCENT)
            speak(briefing)
        except Exception as e:
            err = str(e)
            self.after(0, lambda m=err: self._add_message("assistant", f"Briefing Fehler: {m}"))
        finally:
            self._set_status("Bereit")

    def _toggle_wake_word(self):
        if self.wake_active:
            self.wake_stop.set()
            self.wake_active = False
            self.wake_btn.configure(text="👂 Wake Word: OFF", text_color=GREY, border_color=GREY)
            self._set_status("Wake Word deaktiviert.")
        else:
            self.wake_stop.clear()
            self.wake_active = True
            self.wake_btn.configure(text="👂 Wake Word: ON", text_color=GREEN, border_color=GREEN)
            self._set_status("Warte auf 'Hey J1'...", GREEN)
            threading.Thread(target=self._run_wake_word, daemon=True).start()

    def _run_wake_word(self):
        from voice.wakeword import listen_for_wakeword
        def on_wake():
            if not self.conversation_active:
                self.after(0, self._on_mic_press)
        listen_for_wakeword(callback=on_wake, stop_event=self.wake_stop)

    def _start_reminder_checker(self):
        def check():
            import time
            while True:
                due = get_due_reminders()
                for r in due:
                    msg = f"Erinnerung: {r['text']}"
                    self.after(0, lambda m=msg: self._add_message("assistant", m))
                    speak(msg)
                time.sleep(60)
        threading.Thread(target=check, daemon=True).start()

    def _add_message(self, role: str, text: str):
        color = "#1a2a4a" if role == "user" else "#0f1a2a"
        prefix = "Du" if role == "user" else "J1"
        anchor = "e" if role == "user" else "w"
        bubble = ctk.CTkFrame(self.chat_frame, fg_color=color, corner_radius=12)
        bubble.pack(fill="x", padx=10, pady=4, anchor=anchor)
        ctk.CTkLabel(bubble, text=f"{prefix}:  {text}",
            font=ctk.CTkFont(size=13), text_color=TEXT,
            wraplength=580, justify="left", anchor="w"
        ).pack(padx=12, pady=8, anchor="w")
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def _set_status(self, text: str, color: str = None):
        self.status_label.configure(text=text, text_color=color or GREY)
        self.update()

    def _refresh_dots(self):
        for lbl, conn in self._dot_labels:
            lbl.configure(text_color=GREEN if conn["check"]() else RED)

    def _on_mic_press(self):
        if self.conversation_active:
            # Gespräch stoppen
            self.conversation_active = False
            self.is_listening = False
            self.mic_btn.configure(text="🎙  Sprechen", fg_color=ACCENT)
            self._set_status("Gespräch beendet.")
            return

        # Gespräch starten
        self.conversation_active = True
        self.mic_btn.configure(text="⏹  Stoppen", fg_color=RED)
        threading.Thread(target=self._conversation_loop, daemon=True).start()

    def _conversation_loop(self):
        """Dauergespräch: hören → antworten → hören → ... bis Stopp gedrückt."""
        import time
        while self.conversation_active:
            # Warten bis J1 fertig gesprochen hat
            while is_speaking():
                time.sleep(0.1)

            self.is_listening = True
            self.after(0, lambda: self._set_status("Höre zu...", ACCENT))
            try:
                audio = record_until_silence()
                if not self.conversation_active:
                    break
                if is_speaking():
                    continue
                # None = kein echtes Sprechen erkannt
                if audio is None:
                    continue
                self.after(0, lambda: self._set_status("Transkribiere...", YELLOW))
                text = transcribe(audio)
                if not text or not text.strip():
                    continue
                self.after(0, lambda t=text: self._add_message("user", t))
                self._process_message(text)
            except Exception as e:
                err = str(e)
                self.after(0, lambda m=err: self._set_status(f"Fehler: {m}", RED))
                break

        self.is_listening = False
        self.conversation_active = False
        self.after(0, lambda: self.mic_btn.configure(text="🎙  Sprechen", fg_color=ACCENT))
        if self.wake_active:
            self._set_status("Warte auf 'Hey J1'...", GREEN)
        else:
            self._set_status("Bereit")

    def _on_text_submit(self, event=None):
        text = self.text_input.get().strip()
        if not text:
            return
        self.text_input.delete(0, "end")
        self._add_message("user", text)
        threading.Thread(target=self._process_message, args=(text,), daemon=True).start()

    def _process_message(self, text: str):
        self._set_status("J1 denkt...", YELLOW)
        try:
            answer, self.history = chat(text, self.history)
            self.after(0, lambda a=answer: self._add_message("assistant", a))
            self._set_status("Spricht...", ACCENT)
            speak(answer)
        except Exception as e:
            err = str(e)
            self.after(0, lambda m=err: self._add_message("assistant", f"Fehler: {m}"))
        finally:
            self._set_status("Bereit")

    def destroy(self):
        save_history(self.history)
        self.wake_stop.set()
        super().destroy()


def main():
    app = J1App()
    app.mainloop()


if __name__ == "__main__":
    main()
