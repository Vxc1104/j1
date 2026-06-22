import threading
import customtkinter as ctk
from dotenv import load_dotenv
load_dotenv()

from voice.listener import record_until_silence, transcribe
from voice.speaker import speak
from brain.claude import chat

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#00d4ff"
BG = "#0a0a0f"
BG2 = "#111118"
TEXT = "#e0e8ff"


class J1App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("J1 — Persönlicher Assistent")
        self.geometry("700x800")
        self.configure(fg_color=BG)
        self.history = []
        self.is_listening = False
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkLabel(
            self, text="J1", font=ctk.CTkFont(size=48, weight="bold"),
            text_color=ACCENT
        )
        header.pack(pady=(30, 5))

        subtitle = ctk.CTkLabel(
            self, text="Persönlicher Assistent",
            font=ctk.CTkFont(size=14), text_color="#5566aa"
        )
        subtitle.pack(pady=(0, 20))

        # Chat log
        self.chat_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG2, corner_radius=12,
            width=640, height=400
        )
        self.chat_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Status
        self.status_label = ctk.CTkLabel(
            self, text="Bereit",
            font=ctk.CTkFont(size=13), text_color="#5566aa"
        )
        self.status_label.pack(pady=5)

        # Mic button
        self.mic_btn = ctk.CTkButton(
            self, text="🎙  Sprechen",
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=ACCENT, text_color=BG,
            hover_color="#00aacc",
            width=200, height=60, corner_radius=30,
            command=self._on_mic_press
        )
        self.mic_btn.pack(pady=15)

        # Text input
        input_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        input_frame.pack(padx=20, pady=(0, 20), fill="x")

        self.text_input = ctk.CTkEntry(
            input_frame, placeholder_text="Oder tippe hier...",
            fg_color=BG2, text_color=TEXT, border_color="#2233aa",
            font=ctk.CTkFont(size=14), height=45, corner_radius=22
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.text_input.bind("<Return>", self._on_text_submit)

        send_btn = ctk.CTkButton(
            input_frame, text="→",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=ACCENT, text_color=BG,
            width=45, height=45, corner_radius=22,
            command=self._on_text_submit
        )
        send_btn.pack(side="right")

    def _add_message(self, role: str, text: str):
        is_user = role == "user"
        color = "#1a2a4a" if is_user else "#0f1a2a"
        align = "e" if is_user else "w"
        prefix = "Du: " if is_user else "J1: "

        bubble = ctk.CTkFrame(self.chat_frame, fg_color=color, corner_radius=12)
        bubble.pack(fill="x", padx=10, pady=4, anchor=align)

        label = ctk.CTkLabel(
            bubble, text=f"{prefix}{text}",
            font=ctk.CTkFont(size=13), text_color=TEXT,
            wraplength=540, justify="left", anchor="w"
        )
        label.pack(padx=12, pady=8, anchor="w")

    def _set_status(self, text: str, color: str = "#5566aa"):
        self.status_label.configure(text=text, text_color=color)
        self.update()

    def _on_mic_press(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.mic_btn.configure(text="⏹  Aufnahme...", fg_color="#ff4455")
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
            self._set_status(f"Fehler: {e}", "#ff4455")
        finally:
            self.is_listening = False
            self.after(0, lambda: self.mic_btn.configure(
                text="🎙  Sprechen", fg_color=ACCENT
            ))

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
            self._set_status("Bereit", "#5566aa")


def main():
    app = J1App()
    app.mainloop()


if __name__ == "__main__":
    main()
