#!/usr/bin/env python3
"""MELISSA-TTS Desktop: Habla con Melissa o deja que te lea y concluya.

Clic -> pega portapapeles -> detecta idioma -> listo.
Requisitos: pip install edge-tts
Opcional:   AZURE_SPEECH_KEY + AZURE_SPEECH_REGION para voces Azure Neural
"""

import asyncio
import os
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from collections import Counter
from datetime import datetime

TEMP_AUDIO_TTL_SECONDS = 2 * 60 * 60

try:
    import edge_tts
    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

VOICE_PRESETS = {
    "es-MX": {
        "female": {"edge": "es-MX-DaliaNeural", "azure": "es-MX-DaliaNeural", "label": "Espanol MX (Dalia)"},
        "male": {"edge": "es-MX-JorgeNeural", "azure": "es-MX-JorgeNeural", "label": "Espanol MX (Jorge)"},
    },
    "en-US": {
        "female": {"edge": "en-US-JennyNeural", "azure": "en-US-JennyNeural", "label": "English US (Jenny)"},
        "male": {"edge": "en-US-GuyNeural", "azure": "en-US-GuyNeural", "label": "English US (Guy)"},
    },
    "zh-CN": {
        "female": {"edge": "zh-CN-XiaoxiaoNeural", "azure": "zh-CN-XiaoxiaoNeural", "label": "中文 (Xiaoxiao)"},
        "male": {"edge": "zh-CN-YunxiNeural", "azure": "zh-CN-YunxiNeural", "label": "中文 (Yunxi)"},
    },
    "ja-JP": {
        "female": {"edge": "ja-JP-NanamiNeural", "azure": "ja-JP-NanamiNeural", "label": "日本語 (Nanami)"},
        "male": {"edge": "ja-JP-KeitaNeural", "azure": "ja-JP-KeitaNeural", "label": "日本語 (Keita)"},
    },
}

PERSONA_PROFILES = {
    "auto": {"label": "Auto", "gender": "female", "aliases": []},
    "melissa": {"label": "Melissa", "gender": "female", "aliases": ["melissa", "meli"]},
    "memo": {"label": "Memo", "gender": "male", "aliases": ["memo", "guillermo"]},
    "nexo": {"label": "Nexo", "gender": "male", "aliases": ["nexo"]},
    "claude": {"label": "Claude", "gender": "male", "aliases": ["claude"]},
    "operadora": {"label": "Operadora", "gender": "female", "aliases": ["operadora", "asistente"]},
    "analista": {"label": "Analista", "gender": "male", "aliases": ["analista", "auditor"]},
    "general-f": {"label": "General F", "gender": "female", "aliases": []},
    "general-m": {"label": "General M", "gender": "male", "aliases": []},
}

STOP_WORDS_ES = {"el","la","los","las","un","una","unos","unas","de","del","en","con","por","para","que","se","no","es","al","le","ya","o","a","un","su","como","muy","mas","este","esta","esto","eso","esa","ese","pero","sin","sobre","entre","era","hay","puede","tambien","ha","este","ser","desde","todo","son","fue","tiene","puede","hasta","son","dos","hay","pues","bien","tiene","cada","vez","otro","ellos","nos","si","yo","me","mi","tu","te","le","les","nos","nosotro","usted","ustedes","ellos","ellas","lo","los","la","las","ese","esa","eso","aquel","aquella","aquello"}
STOP_WORDS_EN = {"the","a","an","is","are","was","were","be","been","have","has","had","do","does","did","will","would","could","should","may","might","can","shall","to","of","in","for","on","with","at","by","from","as","into","through","during","before","after","above","below","between","out","off","over","under","again","further","then","once","here","there","when","where","why","how","all","each","few","more","most","other","some","such","no","nor","not","only","own","same","so","than","too","very","just","because","but","and","or","if","while","this","that","these","those","it","its","he","she","they","them","their","we","our","you","your","what","which","who"}
STOP_WORDS_ZH = {"的","了","在","是","我","有","和","就","不","人","都","一","这","中","大","为","上","个","国","们","到","说","们","年","要","会","对","地","出","也","时","道","他","它","她","吗","吧","呢","啊","哦","嗯"}
STOP_WORDS_JA = {"の","に","は","を","が","で","と","も","し","から","まで","も","へ","です","ます","た","て","くる","さん","その","この","あの","私","彼","彼女"}

ES_PATTERN = re.compile(r'\b(el|la|los|las|un|una|de|del|en|con|por|para|que|se|es|al|pero|sin|sobre|entre|hay|puede|tambien|tiene|son|fue|hasta|este|esta|esto|eso|esa|ese|como|muy|mas|ya|le|nos|si|yo|me|mi|tu|te|usted)\b', re.IGNORECASE)
EN_PATTERN = re.compile(r'\b(the|is|are|was|were|have|has|had|will|would|could|should|this|that|with|from|they|them|their|which|would|about|been|does|into|more|other|than|when|where|what|your|can|not)\b', re.IGNORECASE)


def detect_lang(text: str) -> str:
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', text))
    has_hiragana = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    has_es_accents = bool(re.search(r'[áéíóúñ¿¡]', text, re.IGNORECASE))
    if has_hiragana:
        return "ja-JP"
    if has_cjk:
        return "zh-CN"
    if has_es_accents:
        return "es-MX"
    es_count = len(ES_PATTERN.findall(text))
    en_count = len(EN_PATTERN.findall(text))
    if es_count > en_count and es_count >= 2:
        return "es-MX"
    return "en-US"


SECTION_PATTERNS = {
    "base": re.compile(r'^\s*base\s*:\s*', re.IGNORECASE),
    "centro": re.compile(r'^\s*centro\s*:\s*', re.IGNORECASE),
    "accion": re.compile(r'^\s*accion\s*:\s*', re.IGNORECASE),
    "veredicto": re.compile(r'^\s*veredicto\s*:\s*', re.IGNORECASE),
}


def get_stop_words(lang: str):
    if lang == "zh-CN":
        return STOP_WORDS_ZH
    if lang == "ja-JP":
        return STOP_WORDS_JA
    if lang == "en-US":
        return STOP_WORDS_EN
    return STOP_WORDS_ES


def split_sentences(text: str):
    chunks = re.split(r'(?<=[.!?。！？])\s+|\n+', text.strip())
    return [chunk.strip(" -\t") for chunk in chunks if len(chunk.strip()) > 8]


def tokenize_text(text: str):
    if re.search(r'[\u4e00-\u9fff\u3040-\u30ff]', text):
        return [char for char in re.findall(r'[\u4e00-\u9fff\u3040-\u30ff]', text)]
    return re.findall(r'\b[\w-]+\b', text.lower())


def build_frequency(sentences, stop_words):
    freq = Counter()
    for sentence in sentences:
        for token in tokenize_text(sentence):
            if token not in stop_words and len(token) > 1:
                freq[token] += 1
    return freq


def score_sentence(sentence: str, freq: Counter, stop_words, index: int) -> float:
    tokens = tokenize_text(sentence)
    if not tokens:
        return 0.0

    score = sum(freq.get(token, 0) for token in tokens if token not in stop_words) / max(len(tokens), 1)
    lower = sentence.lower()
    if index == 0:
        score += 0.4
    if any(marker in lower for marker in ["debe", "hay que", "next", "should", "accion", "veredicto", "critical", "riesgo"]):
        score += 0.5
    if re.search(r'\d', sentence):
        score += 0.15
    return score


def pick_diverse_sentences(sentences, freq: Counter, stop_words, max_sentences: int = 2):
    scored = [(sentence, score_sentence(sentence, freq, stop_words, idx)) for idx, sentence in enumerate(sentences)]
    scored.sort(key=lambda item: item[1], reverse=True)

    selected = []
    selected_tokens = []
    for sentence, _score in scored:
        tokens = set(tokenize_text(sentence))
        if selected_tokens:
            overlap = max(len(tokens & prev) / max(len(tokens | prev), 1) for prev in selected_tokens)
            if overlap > 0.65:
                continue
        selected.append(sentence)
        selected_tokens.append(tokens)
        if len(selected) >= max_sentences:
            break
    return selected or sentences[:1]


def extract_trilineal_sections(text: str):
    sections = {}
    compact = " ".join(text.split())
    pattern = re.compile(
        r'(BASE|CENTRO|ACCION|VEREDICTO)\s*:\s*(.*?)(?=(?:BASE|CENTRO|ACCION|VEREDICTO)\s*:|$)',
        re.IGNORECASE,
    )
    for match in pattern.finditer(compact):
        key = match.group(1).lower()
        value = match.group(2).strip(" |")
        if value:
            sections[key] = value
    return sections


def summarize_passage(text: str, lang: str, max_sentences: int = 2) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return text.strip()
    if len(sentences) == 1:
        return sentences[0]
    stop_words = get_stop_words(lang)
    freq = build_frequency(sentences, stop_words)
    selected = pick_diverse_sentences(sentences, freq, stop_words, max_sentences=max_sentences)
    return " ".join(selected)


def detect_persona(text: str) -> str:
    lowered = text.lower()
    for key, profile in PERSONA_PROFILES.items():
        if key == "auto":
            continue
        for alias in profile["aliases"]:
            if re.search(rf'\b{re.escape(alias)}\b', lowered):
                return key
    return "melissa"


def generate_conclusion(text: str, lang: str = "es-MX") -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""

    labels = {
        "zh-CN": {"conclusion": "结论", "next": "下一步", "base": "基础", "centro": "中心", "accion": "行动", "veredicto": "结论"},
        "ja-JP": {"conclusion": "結論", "next": "次の一手", "base": "基盤", "centro": "中心", "accion": "行動", "veredicto": "評決"},
        "en-US": {"conclusion": "Conclusion", "next": "Next step", "base": "Base", "centro": "Center", "accion": "Action", "veredicto": "Verdict"},
        "es-MX": {"conclusion": "Conclusion", "next": "Proximo paso", "base": "Base", "centro": "Centro", "accion": "Accion", "veredicto": "Veredicto"},
    }
    label_pack = labels.get(lang, labels["es-MX"])

    trilineal = extract_trilineal_sections(text)
    if trilineal:
        ordered = []
        for key in ("base", "centro", "accion", "veredicto"):
            if key in trilineal and trilineal[key]:
                ordered.append(f"{label_pack[key]}: {summarize_passage(trilineal[key], lang, max_sentences=1)}")
        if ordered:
            return " | ".join(ordered)

    sentences = split_sentences(cleaned)
    if not sentences:
        return f"{label_pack['conclusion']}: {cleaned}"

    stop_words = get_stop_words(lang)
    freq = build_frequency(sentences, stop_words)
    selected = pick_diverse_sentences(sentences, freq, stop_words, max_sentences=2)
    action_sentence = next(
        (
            sentence for sentence in sentences
            if any(marker in sentence.lower() for marker in ["debe", "hay que", "next", "should", "necesita", "accion", "paso"])
        ),
        selected[-1],
    )

    lead = selected[0]
    if action_sentence == lead:
        return f"{label_pack['conclusion']}: {lead}"
    return f"{label_pack['conclusion']}: {lead} {label_pack['next']}: {action_sentence}"


def resolve_voice(lang: str, persona_key: str):
    persona = PERSONA_PROFILES.get(persona_key, PERSONA_PROFILES["melissa"])
    gender = persona.get("gender", "female")
    preset = VOICE_PRESETS.get(lang, VOICE_PRESETS["es-MX"])
    return preset.get(gender, preset["female"])


def schedule_auto_delete(file_path: str, delay_seconds: int = TEMP_AUDIO_TTL_SECONDS):
    if not file_path:
        return

    cleanup_code = (
        "import os, sys, time; "
        "path = sys.argv[1]; "
        "delay = int(sys.argv[2]); "
        "time.sleep(delay); "
        "os.remove(path) if os.path.exists(path) else None"
    )
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(
        [sys.executable, "-c", cleanup_code, os.path.abspath(file_path), str(delay_seconds)],
        **kwargs,
    )


class MelissaTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MELISSA-TTS")
        self.root.configure(bg="#1a1a2e")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)

        self.temp_dir = tempfile.mkdtemp(prefix="melissa_tts_")
        self._build_ui()
        self._paste_from_clipboard()

        self.root.bind("<Control-v>", lambda e: self._paste_from_clipboard())
        self.root.bind("<Control-Return>", lambda e: self._habla())
        self.root.bind("<Control-Shift-Return>", lambda e: self._lee_y_concluye())

    def _paste_from_clipboard(self):
        try:
            clip = self.root.clipboard_get()
            current = self.text_input.get("1.0", "end-1c").strip()
            if clip and clip.strip() != current:
                self.text_input.delete("1.0", "end")
                self.text_input.insert("1.0", clip)
                lang = self._get_lang()
                persona_key = self._get_persona()
                voice = resolve_voice(lang, persona_key)
                status_engine = "Azure Neural" if (AZURE_AVAILABLE and os.environ.get("AZURE_SPEECH_KEY")) else "Edge-TTS"
                self._set_status(f"Portapapeles pegado | {voice['label']} | {status_engine}")
        except tk.TclError:
            pass

    def _build_ui(self):
        bg = "#1a1a2e"
        fg = "#e0e0e0"
        accent = "#f5a623"
        btn_bg = "#16213e"
        btn_active = "#0f3460"

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Accent.TButton", background=accent, foreground="#1a1a2e", font=("Segoe UI", 11, "bold"), padding=8)
        style.map("Accent.TButton", background=[("active", btn_active)])
        style.configure("Secondary.TButton", background=btn_bg, foreground=fg, font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Secondary.TButton", background=[("active", btn_active)])
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=accent, font=("Segoe UI", 16, "bold"))
        style.configure("Status.TLabel", background=bg, foreground="#888", font=("Segoe UI", 9))
        style.configure("Hint.TLabel", background=bg, foreground="#555", font=("Segoe UI", 8))

        title_frame = tk.Frame(self.root, bg=bg)
        title_frame.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Label(title_frame, text="MELISSA-TTS", style="Title.TLabel").pack(side="left")
        ttk.Label(title_frame, text="中文 / ES / EN / 日本語", style="TLabel").pack(side="right", padx=8)

        lang_frame = tk.Frame(self.root, bg=bg)
        lang_frame.pack(fill="x", padx=16, pady=4)
        ttk.Label(lang_frame, text="Idioma:").pack(side="left")
        self.lang_var = tk.StringVar(value="es-MX")
        self.lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=list(VOICE_PRESETS.keys()), state="readonly", width=10)
        self.lang_combo.pack(side="left", padx=8)
        self.lang_label = ttk.Label(lang_frame, text=resolve_voice("es-MX", "melissa")["label"], style="TLabel")
        self.lang_label.pack(side="left")
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        self.auto_detect_var = tk.BooleanVar(value=True)
        auto_cb = ttk.Checkbutton(lang_frame, text="Auto", variable=self.auto_detect_var, command=self._on_auto_change)
        auto_cb.pack(side="left", padx=8)

        ttk.Label(lang_frame, text="Persona:").pack(side="left", padx=(12, 0))
        self.persona_var = tk.StringVar(value="auto")
        self.persona_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.persona_var,
            values=list(PERSONA_PROFILES.keys()),
            state="readonly",
            width=12,
        )
        self.persona_combo.pack(side="left", padx=8)
        self.persona_label = ttk.Label(lang_frame, text=PERSONA_PROFILES["auto"]["label"], style="TLabel")
        self.persona_label.pack(side="left")
        self.persona_combo.bind("<<ComboboxSelected>>", self._on_persona_change)

        paste_btn = ttk.Button(lang_frame, text="Pegar (Ctrl+V)", style="Secondary.TButton", command=self._paste_from_clipboard)
        paste_btn.pack(side="right")

        ttk.Label(self.root, text="Escribe o pega tu texto:", style="TLabel").pack(anchor="w", padx=16, pady=(8, 2))
        self.text_input = scrolledtext.ScrolledText(self.root, height=8, wrap="word", bg="#16213e", fg="#e0e0e0",
                                                     insertbackground=accent, font=("Segoe UI", 11),
                                                     relief="flat", bd=0, padx=8, pady=8)
        self.text_input.pack(fill="both", expand=True, padx=16, pady=2)
        self.text_input.bind("<KeyRelease>", self._on_text_change)

        btn_frame = tk.Frame(self.root, bg=bg)
        btn_frame.pack(fill="x", padx=16, pady=6)

        self.btn_habla = ttk.Button(btn_frame, text="HABLA con Melissa (Ctrl+Enter)", style="Accent.TButton", command=self._habla)
        self.btn_habla.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_concluye = ttk.Button(btn_frame, text="LEE y CONCLUYE (Ctrl+Shift+Enter)", style="Secondary.TButton", command=self._lee_y_concluye)
        self.btn_concluye.pack(side="left", expand=True, fill="x", padx=(4, 0))

        ttk.Label(self.root, text="Conclusion / 结论:", style="TLabel").pack(anchor="w", padx=16, pady=(4, 2))
        self.conclusion_box = scrolledtext.ScrolledText(self.root, height=4, wrap="word", bg="#0f3460", fg="#f5a623",
                                                          font=("Segoe UI", 11, "bold"), relief="flat", bd=0, padx=8, pady=8,
                                                          state="disabled")
        self.conclusion_box.pack(fill="both", padx=16, pady=2)

        status_frame = tk.Frame(self.root, bg=bg)
        status_frame.pack(fill="x", padx=16, pady=(2, 0))
        engine_label = "Azure Neural" if (AZURE_AVAILABLE and os.environ.get("AZURE_SPEECH_KEY")) else "Edge-TTS (gratis)"
        self.status_var = tk.StringVar(value=f"Lista | {engine_label}")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        ttk.Label(status_frame, text="Ctrl+V=pegar | Ctrl+Enter=habla | Ctrl+Shift+Enter=concluye", style="Hint.TLabel").pack(side="right")

    def _on_lang_change(self, event=None):
        lang = self.lang_var.get()
        self._update_voice_label(lang=lang)

    def _on_persona_change(self, event=None):
        persona_key = self.persona_var.get()
        self.persona_label.config(text=PERSONA_PROFILES.get(persona_key, PERSONA_PROFILES["auto"])["label"])
        self._update_voice_label()

    def _on_auto_change(self):
        if self.auto_detect_var.get():
            self._on_text_change()

    def _on_text_change(self, event=None):
        if self.auto_detect_var.get():
            text = self.text_input.get("1.0", "end-1c")
            if text.strip():
                lang = detect_lang(text)
                self.lang_var.set(lang)
                self._update_voice_label(lang=lang)

    def _get_lang(self):
        if self.auto_detect_var.get():
            text = self.text_input.get("1.0", "end-1c")
            if text.strip():
                return detect_lang(text)
        return self.lang_var.get()

    def _get_persona(self):
        selected = self.persona_var.get()
        if selected != "auto":
            return selected
        text = self.text_input.get("1.0", "end-1c")
        return detect_persona(text)

    def _get_voice(self, lang):
        persona_key = self._get_persona()
        resolved = resolve_voice(lang, persona_key)
        provider = "azure" if (AZURE_AVAILABLE and os.environ.get("AZURE_SPEECH_KEY")) else "edge"
        return resolved[provider]

    def _get_voice_label(self, lang):
        return resolve_voice(lang, self._get_persona())["label"]

    def _update_voice_label(self, lang=None):
        effective_lang = lang or self._get_lang()
        self.lang_label.config(text=self._get_voice_label(effective_lang))

    def _set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _set_conclusion(self, text):
        self.conclusion_box.config(state="normal")
        self.conclusion_box.delete("1.0", "end")
        self.conclusion_box.insert("1.0", text)
        self.conclusion_box.config(state="disabled")

    def _play_audio(self, filepath):
        try:
            os.startfile(filepath)
        except Exception:
            if sys.platform == "win32":
                os.system(f'start "" "{filepath}"')

    def _synthesize(self, text, lang, output_path):
        if AZURE_AVAILABLE and os.environ.get("AZURE_SPEECH_KEY"):
            self._synthesize_azure(text, lang, output_path)
        else:
            asyncio.run(self._synthesize_edge(text, lang, output_path))

    def _synthesize_azure(self, text, lang, output_path):
        key = os.environ.get("AZURE_SPEECH_KEY")
        region = os.environ.get("AZURE_SPEECH_REGION", "eastus")
        voice = self._get_voice(lang)

        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_voice_name = voice
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = synthesizer.speak_text_async(text).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"Azure TTS failed: {result.cancellation_details.reason}")

    async def _synthesize_edge(self, text, lang, output_path):
        voice = self._get_voice(lang)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def _habla(self):
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("MELISSA-TTS", "Escribe algo primero.")
            return
        lang = self._get_lang()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.temp_dir, f"melissa_habla_{timestamp}.mp3")

        self.btn_habla.config(state="disabled")
        self.btn_concluye.config(state="disabled")
        engine = "Azure" if (AZURE_AVAILABLE and os.environ.get("AZURE_SPEECH_KEY")) else "Edge-TTS"
        persona_label = PERSONA_PROFILES.get(self._get_persona(), PERSONA_PROFILES["melissa"])["label"]
        self._set_status(f"Sintetizando ({persona_label} | {self._get_voice_label(lang)} | {engine})...")

        def worker():
            try:
                self._synthesize(text, lang, output_path)
                schedule_auto_delete(output_path)
                self.root.after(0, lambda: self._set_status(f"Reproduciendo... ({engine})"))
                self.root.after(500, lambda: self._play_audio(output_path))
                self.root.after(0, lambda: self._set_status(f"Lista | {persona_label} | {self._get_voice_label(lang)} | {engine}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error TTS", str(e)))
                self.root.after(0, lambda: self._set_status(f"Error: {e}"))
            finally:
                self.root.after(0, lambda: self.btn_habla.config(state="normal"))
                self.root.after(0, lambda: self.btn_concluye.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _lee_y_concluye(self):
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("MELISSA-TTS", "Escribe algo primero.")
            return
        lang = self._get_lang()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.btn_habla.config(state="disabled")
        self.btn_concluye.config(state="disabled")
        persona_label = PERSONA_PROFILES.get(self._get_persona(), PERSONA_PROFILES["melissa"])["label"]
        self._set_status(f"Generando conclusion ({persona_label} | {self._get_voice_label(lang)})...")
        self._set_conclusion("")

        conclusion = generate_conclusion(text, lang)
        self._set_conclusion(conclusion)

        tts_text = conclusion
        output_path = os.path.join(self.temp_dir, f"melissa_concluye_{timestamp}.mp3")
        engine = "Azure" if (AZURE_AVAILABLE and os.environ.get("AZURE_SPEECH_KEY")) else "Edge-TTS"

        self._set_status(f"Sintetizando conclusion ({engine})...")

        def worker():
            try:
                self._synthesize(tts_text, lang, output_path)
                schedule_auto_delete(output_path)
                self.root.after(0, lambda: self._set_status(f"Reproduciendo conclusion ({engine})..."))
                self.root.after(500, lambda: self._play_audio(output_path))
                self.root.after(0, lambda: self._set_status(f"Lista | {persona_label} | Conclusion generada y leida | {engine}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error TTS", str(e)))
                self.root.after(0, lambda: self._set_status(f"Error: {e}"))
            finally:
                self.root.after(0, lambda: self.btn_habla.config(state="normal"))
                self.root.after(0, lambda: self.btn_concluye.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


def main():
    if not EDGE_AVAILABLE and not AZURE_AVAILABLE:
        print("ERROR: Instala al menos uno: pip install edge-tts  o  pip install azure-cognitiveservices-speech")
        sys.exit(1)

    root = tk.Tk()
    app = MelissaTTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()