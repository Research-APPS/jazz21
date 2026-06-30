(function () {
  const FN_COLOR = {
    "Tónica":        "#bd93f9",
    "Subdominante":  "#50c8c8",
    "Dominante":     "#ff6b6b",
  };
  const MODO_ES = {
    ionian: "Mayor", dorian: "Dórico", phrygian: "Frigio",
    lydian: "Lidio", mixolydian: "Mixolidio", aeolian: "Menor",
    locrian: "Locrio",
  };
  const QUALITY_CYCLE = ["", "m", "7", "maj7", "m7", "dim", "m7b5"];

  let progressions = [];
  let currentIndex = 0;
  let currentProg = null;
  let selectedIndex = null;
  let suggestions = [];
  let suggestIndex = 0;
  let isPlaying = false;
  let scheduledEvents = [];
  let playbackSession = null;
  let toneReady = false;
  let pyInstance = null;
  let pyHelperReady = false;
  let pyBootPromise = null;
  let paletteLoading = false;
  let paletteError = null;
  let libraryApiAvailable = false;
  let libraryAuthenticated = false;
  let libraryUsername = null;
  let libraryDetailUuid = null;

  const AUDIO_STORAGE_KEY = "jazz21-audio-settings";
  const VOICE_TYPES = ["Synth", "AMSynth", "FMSynth", "MonoSynth", "DuoSynth"];
  const OSC_TYPES = [
    "sine", "triangle", "sawtooth", "square",
    "fatSine", "fatTriangle", "fatSawtooth", "fatSquare", "pulse",
  ];

  const DEFAULT_AUDIO = {
    bpm: 96,
    beatsPerChord: 2,
    loop: true,
    gate: 0.88,
    masterVolume: 0,
    volume: -8,
    voice: "Synth",
    oscillatorType: "triangle",
    harmonicity: 3,
    modulationIndex: 10,
    modulationType: "square",
    maxPolyphony: 32,
    detune: 0,
    envelope: { attack: 0.04, decay: 0.3, sustain: 0.6, release: 1.2 },
    filterEnvelope: { attack: 0.005, decay: 0.1, sustain: 0.3, release: 1.5, baseFrequency: 200, octaves: 4 },
  };

  let audioSettings = loadAudioSettings();
  let audioBarBound = false;

  function loadAudioSettings() {
    try {
      const raw = localStorage.getItem(AUDIO_STORAGE_KEY);
      if (!raw) return { ...DEFAULT_AUDIO, envelope: { ...DEFAULT_AUDIO.envelope }, filterEnvelope: { ...DEFAULT_AUDIO.filterEnvelope } };
      const parsed = JSON.parse(raw);
      return {
        ...DEFAULT_AUDIO,
        ...parsed,
        envelope: { ...DEFAULT_AUDIO.envelope, ...(parsed.envelope || {}) },
        filterEnvelope: { ...DEFAULT_AUDIO.filterEnvelope, ...(parsed.filterEnvelope || {}) },
      };
    } catch {
      return { ...DEFAULT_AUDIO, envelope: { ...DEFAULT_AUDIO.envelope }, filterEnvelope: { ...DEFAULT_AUDIO.filterEnvelope } };
    }
  }

  function saveAudioSettings() {
    try {
      localStorage.setItem(AUDIO_STORAGE_KEY, JSON.stringify(audioSettings));
    } catch (_) { /* quota / private mode */ }
  }

  function voiceClass(name) {
    const map = {
      Synth: Tone.Synth,
      AMSynth: Tone.AMSynth,
      FMSynth: Tone.FMSynth,
      MonoSynth: Tone.MonoSynth,
      DuoSynth: Tone.DuoSynth,
    };
    return map[name] || Tone.Synth;
  }

  function isModulatedVoice() {
    return audioSettings.voice === "AMSynth" || audioSettings.voice === "FMSynth";
  }

  function buildSynthOptions() {
    const opts = {
      volume: audioSettings.volume,
      detune: audioSettings.detune,
      oscillator: { type: audioSettings.oscillatorType },
      envelope: { ...audioSettings.envelope },
    };
    if (isModulatedVoice()) {
      opts.harmonicity = audioSettings.harmonicity;
      opts.modulationIndex = audioSettings.modulationIndex;
      opts.modulation = { type: audioSettings.modulationType };
    }
    if (audioSettings.voice === "MonoSynth") {
      opts.filterEnvelope = { ...audioSettings.filterEnvelope };
    }
    return opts;
  }

  function synthNeedsRebuild() {
    if (!synth) return true;
    return synth._jazz21Voice !== audioSettings.voice
      || synth._jazz21Polyphony !== audioSettings.maxPolyphony
      || synth._jazz21Oscillator !== audioSettings.oscillatorType;
  }

  function applyAudioSettings() {
    if (typeof Tone === "undefined") return;
    Tone.Destination.volume.value = audioSettings.masterVolume;
    if (isPlaying) {
      // Parámetros del sintetizador: prepareSynthForChord en el siguiente acorde
      return;
    }
    if (synthNeedsRebuild()) {
      if (synth) {
        try { synth.releaseAll(); } catch (_) {}
        disposeSynth();
      }
      getSynth();
      return;
    }
    if (!synth) {
      getSynth();
      return;
    }
    try {
      synth.set(buildSynthOptions());
    } catch (_) {
      disposeSynth();
      getSynth();
    }
  }

  function chordDurationSeconds() {
    const { bpm, beatsPerChord } = audioSettings;
    return beatsPerChord * (60 / bpm);
  }

  function progressionLoopDuration(prog) {
    return prog.acordes.length * chordDurationSeconds();
  }

  function updateTransportLoop(prog) {
    if (typeof Tone === "undefined") return;
    Tone.Transport.bpm.value = audioSettings.bpm;
    Tone.Transport.loop = false;
    Tone.Transport.loopStart = 0;
    Tone.Transport.loopEnd = progressionLoopDuration(prog);
  }

  function prepareSynthForChord() {
    if (typeof Tone === "undefined") return;
    Tone.Destination.volume.value = audioSettings.masterVolume;
    if (synthNeedsRebuild()) {
      if (synth) {
        try { synth.releaseAll(); } catch (_) {}
        disposeSynth();
      }
      getSynth();
      return;
    }
    if (!synth) {
      getSynth();
      return;
    }
    try {
      synth.set(buildSynthOptions());
    } catch (_) {
      disposeSynth();
      getSynth();
    }
  }

  function playChordNotes(chord, time) {
    prepareSynthForChord();
    if (!chord.notas?.length || !synth) return;
    synth.triggerAttackRelease(chord.notas, chordDurationSeconds() * audioSettings.gate, time);
  }

  function clearPendingChordBoundary() {
    if (!playbackSession?.pendingEventId || typeof Tone === "undefined") return;
    Tone.Transport.clear(playbackSession.pendingEventId);
    playbackSession.pendingEventId = null;
  }

  function remainingInCurrentChord() {
    if (!playbackSession) return chordDurationSeconds();
    const elapsed = Tone.Transport.seconds - (playbackSession.lastChordStartTime || 0);
    return Math.max(0.02, (playbackSession.activeChordDur || chordDurationSeconds()) - elapsed);
  }

  function scheduleChordBoundary(callback) {
    if (!playbackSession) return;
    clearPendingChordBoundary();
    playbackSession.boundaryCallback = callback;
    const wait = remainingInCurrentChord();
    const id = Tone.Transport.schedule(() => {
      if (playbackSession) playbackSession.pendingEventId = null;
      callback();
    }, `+${wait}`);
    playbackSession.pendingEventId = id;
    scheduledEvents.push(id);
  }

  function playChordStep(immediate) {
    if (!isPlaying || !playbackSession) return;
    const { prog, onStep } = playbackSession;
    const chords = prog.acordes;
    if (!chords.length) return;

    const idx = playbackSession.chordIndex;
    const chord = chords[idx];
    const time = Tone.now() + (immediate ? 0.05 : 0);

    playbackSession.lastChordStartTime = Tone.Transport.seconds;
    playbackSession.activeChordDur = chordDurationSeconds();

    playChordNotes(chord, time);
    Tone.Draw.schedule(() => onStep(idx), time);

    const nextIdx = (idx + 1) % chords.length;
    const finishedCycle = nextIdx === 0;

    if (finishedCycle && !audioSettings.loop) {
      playbackSession.chordIndex = nextIdx;
      scheduleChordBoundary(() => {
        if (playbackSession?.onStop) playbackSession.onStop();
        stopAudio();
      });
      return;
    }

    playbackSession.chordIndex = nextIdx;
    scheduleChordBoundary(() => playChordStep(true));
  }

  function cloneDefaultAudio() {
    return {
      ...DEFAULT_AUDIO,
      envelope: { ...DEFAULT_AUDIO.envelope },
      filterEnvelope: { ...DEFAULT_AUDIO.filterEnvelope },
    };
  }

  function resetAudioSection(sectionId) {
    const d = cloneDefaultAudio();
    switch (sectionId) {
      case "transport":
        audioSettings.bpm = d.bpm;
        audioSettings.beatsPerChord = d.beatsPerChord;
        audioSettings.gate = d.gate;
        audioSettings.loop = d.loop;
        audioSettings.masterVolume = d.masterVolume;
        break;
      case "synth":
        audioSettings.voice = d.voice;
        audioSettings.oscillatorType = d.oscillatorType;
        audioSettings.volume = d.volume;
        audioSettings.detune = d.detune;
        audioSettings.maxPolyphony = d.maxPolyphony;
        break;
      case "envelope":
        audioSettings.envelope = { ...d.envelope };
        break;
      case "modulation":
        audioSettings.harmonicity = d.harmonicity;
        audioSettings.modulationIndex = d.modulationIndex;
        audioSettings.modulationType = d.modulationType;
        break;
      case "filter":
        audioSettings.filterEnvelope = { ...d.filterEnvelope };
        break;
      case "all":
        audioSettings = cloneDefaultAudio();
        break;
      default:
        return;
    }
    saveAudioSettings();
    const bar = document.querySelector(".prog-audio-bar");
    if (bar) syncAudioBarValues(bar);
    onAudioSettingsChanged();
  }

  function onAudioSettingsChanged() {
    applyAudioSettings();
    // Tempo y compases: el acorde actual usa activeChordDur; el siguiente toma chordDurationSeconds().
    // No reprogramar el boundary — evita desincronización al arrastrar sliders.
  }

  function audioSummaryText() {
    return `Tone.js · ${audioSettings.oscillatorType} · ${audioSettings.bpm} BPM`;
  }

  function sectionLegend(title, sectionId) {
    return `
      <legend class="prog-audio-legend">
        <span class="prog-audio-legend-text">${title}</span>
        <button type="button" class="prog-audio-reset" data-audio-reset="${sectionId}" title="Restaurar módulo">↺</button>
      </legend>`;
  }

  function sliderRow(id, label, min, max, step, value, unit = "") {
    return `
      <label class="prog-audio-field" for="${id}">
        <span class="prog-audio-label">${label}</span>
        <input type="range" id="${id}" data-audio-key="${id}" min="${min}" max="${max}" step="${step}" value="${value}" />
        <output class="prog-audio-value" for="${id}">${value}${unit}</output>
      </label>`;
  }

  function selectRow(id, label, options, value) {
    const opts = options.map((o) => {
      const v = typeof o === "string" ? o : o.value;
      const t = typeof o === "string" ? o : o.label;
      return `<option value="${v}"${v === value ? " selected" : ""}>${t}</option>`;
    }).join("");
    return `
      <label class="prog-audio-field" for="${id}">
        <span class="prog-audio-label">${label}</span>
        <select id="${id}" data-audio-key="${id}">${opts}</select>
      </label>`;
  }

  function audioBarHTML() {
    const s = audioSettings;
    const env = s.envelope;
    const fe = s.filterEnvelope;
    return `
      <summary class="prog-audio-summary">
        <span class="prog-audio-summary-label">Audio</span>
        <span class="prog-audio-summary-meta">${audioSummaryText()}</span>
        <button type="button" class="prog-audio-reset prog-audio-reset-all" data-audio-reset="all" title="Restaurar todo">Todo ↺</button>
      </summary>
      <div class="prog-audio-sections">
        <fieldset class="prog-audio-section" data-audio-section="transport">
          ${sectionLegend("Reproducción", "transport")}
          ${sliderRow("bpm", "Tempo (BPM)", 40, 220, 1, s.bpm)}
          ${sliderRow("beatsPerChord", "Compases por acorde", 1, 8, 1, s.beatsPerChord)}
          ${sliderRow("gate", "Duración nota (gate)", 0.25, 1, 0.01, s.gate)}
          <label class="prog-audio-field prog-audio-check">
            <input type="checkbox" data-audio-key="loop" ${s.loop ? "checked" : ""} />
            <span>Bucle continuo</span>
          </label>
          ${sliderRow("masterVolume", "Volumen maestro (dB)", -40, 6, 1, s.masterVolume, " dB")}
        </fieldset>
        <fieldset class="prog-audio-section" data-audio-section="synth">
          ${sectionLegend('Sintetizador · <a href="https://tonejs.github.io/docs/14.7.77/PolySynth" target="_blank" rel="noopener">PolySynth</a>', "synth")}
          ${selectRow("voice", "Voz", VOICE_TYPES, s.voice)}
          ${selectRow("oscillatorType", "Onda (oscillator.type)", OSC_TYPES, s.oscillatorType)}
          ${sliderRow("volume", "Volumen voz (dB)", -40, 6, 1, s.volume, " dB")}
          ${sliderRow("detune", "Detune (cents)", -100, 100, 1, s.detune)}
          ${sliderRow("maxPolyphony", "Polifonía máx.", 1, 64, 1, s.maxPolyphony)}
        </fieldset>
        <fieldset class="prog-audio-section" data-audio-section="envelope">
          ${sectionLegend("Envolvente (envelope)", "envelope")}
          ${sliderRow("attack", "Attack (s)", 0.001, 3, 0.001, env.attack, " s")}
          ${sliderRow("decay", "Decay (s)", 0.001, 3, 0.001, env.decay, " s")}
          ${sliderRow("sustain", "Sustain", 0, 1, 0.01, env.sustain)}
          ${sliderRow("release", "Release (s)", 0.01, 5, 0.01, env.release, " s")}
        </fieldset>
        <details class="prog-audio-advanced">
          <summary>Avanzado · modulación y filtro</summary>
          <fieldset class="prog-audio-section" data-audio-section="modulation" data-voice-mod="${isModulatedVoice() ? "1" : "0"}">
            ${sectionLegend("AMSynth / FMSynth", "modulation")}
            ${sliderRow("harmonicity", "Harmonicity", 0.5, 16, 0.1, s.harmonicity)}
            ${sliderRow("modulationIndex", "Modulation index", 0, 40, 0.5, s.modulationIndex)}
            ${selectRow("modulationType", "Onda modulación", OSC_TYPES, s.modulationType)}
          </fieldset>
          <fieldset class="prog-audio-section" data-audio-section="filter" data-voice-mono="${s.voice === "MonoSynth" ? "1" : "0"}">
            ${sectionLegend("MonoSynth · filterEnvelope", "filter")}
            ${sliderRow("fe_attack", "Filter attack (s)", 0.001, 2, 0.001, fe.attack, " s")}
            ${sliderRow("fe_decay", "Filter decay (s)", 0.001, 2, 0.001, fe.decay, " s")}
            ${sliderRow("fe_sustain", "Filter sustain", 0, 1, 0.01, fe.sustain)}
            ${sliderRow("fe_release", "Filter release (s)", 0.01, 5, 0.01, fe.release, " s")}
            ${sliderRow("fe_baseFrequency", "Base frequency (Hz)", 20, 2000, 1, fe.baseFrequency, " Hz")}
            ${sliderRow("fe_octaves", "Octaves", 0, 8, 0.1, fe.octaves)}
          </fieldset>
        </details>
        <p class="prog-audio-hint">Motor: <a href="https://tonejs.github.io/" target="_blank" rel="noopener">Tone.js</a> 14.7.77 · Los ajustes se guardan en este navegador.</p>
      </div>`;
  }

  function syncAudioBarValues(bar) {
    const s = audioSettings;
    const set = (key, val) => {
      const el = bar.querySelector(`[data-audio-key="${key}"]`);
      if (!el) return;
      if (el.type === "checkbox") el.checked = Boolean(val);
      else el.value = val;
      const out = bar.querySelector(`output[for="${key}"]`);
      if (out) out.textContent = `${val}${out.dataset.unit || ""}`;
    };
    ["bpm", "beatsPerChord", "gate", "masterVolume", "volume", "detune", "maxPolyphony",
      "harmonicity", "modulationIndex"].forEach((k) => set(k, s[k]));
    set("loop", s.loop);
    set("voice", s.voice);
    set("oscillatorType", s.oscillatorType);
    set("modulationType", s.modulationType);
    Object.entries(s.envelope).forEach(([k, v]) => set(k, v));
    set("fe_attack", s.filterEnvelope.attack);
    set("fe_decay", s.filterEnvelope.decay);
    set("fe_sustain", s.filterEnvelope.sustain);
    set("fe_release", s.filterEnvelope.release);
    set("fe_baseFrequency", s.filterEnvelope.baseFrequency);
    set("fe_octaves", s.filterEnvelope.octaves);
    const meta = bar.querySelector(".prog-audio-summary-meta");
    if (meta) meta.textContent = audioSummaryText();
    bar.querySelectorAll("[data-voice-mod]").forEach((el) => {
      el.style.display = isModulatedVoice() ? "" : "none";
    });
    bar.querySelectorAll("[data-voice-mono]").forEach((el) => {
      el.style.display = s.voice === "MonoSynth" ? "" : "none";
    });
  }

  function setAudioFromControl(key, rawValue) {
    const num = Number(rawValue);
    const envelopeKeys = { attack: 1, decay: 1, sustain: 1, release: 1 };
    const filterMap = {
      fe_attack: "attack", fe_decay: "decay", fe_sustain: "sustain",
      fe_release: "release", fe_baseFrequency: "baseFrequency", fe_octaves: "octaves",
    };
    if (key === "loop") {
      audioSettings.loop = Boolean(rawValue);
    } else if (key in envelopeKeys) {
      audioSettings.envelope[key] = num;
    } else if (key in filterMap) {
      audioSettings.filterEnvelope[filterMap[key]] = num;
    } else if (key in DEFAULT_AUDIO && key !== "envelope" && key !== "filterEnvelope") {
      audioSettings[key] = Number.isFinite(num) && rawValue !== "" && typeof DEFAULT_AUDIO[key] === "number"
        ? num
        : rawValue;
    }
    saveAudioSettings();
    onAudioSettingsChanged();
  }

  function bindAudioBar(container, bar) {
    if (audioBarBound) return;
    audioBarBound = true;
    bar.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-audio-reset]");
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      resetAudioSection(btn.dataset.audioReset);
    });
    bar.addEventListener("input", (e) => {
      const el = e.target.closest("[data-audio-key]");
      if (!el) return;
      const key = el.dataset.audioKey;
      const val = el.type === "checkbox" ? el.checked : el.value;
      setAudioFromControl(key, val);
      const out = bar.querySelector(`output[for="${key}"]`);
      if (out && el.type === "range") {
        const unit = out.dataset.unit || "";
        out.textContent = `${el.value}${unit}`;
      }
      if (key === "voice" || key === "oscillatorType" || key === "bpm") {
        syncAudioBarValues(bar);
      }
    });
    bar.addEventListener("change", (e) => {
      const el = e.target.closest("[data-audio-key]");
      if (!el || el.type === "range") return;
      setAudioFromControl(el.dataset.audioKey, el.type === "checkbox" ? el.checked : el.value);
      syncAudioBarValues(bar);
    });
  }

  function ensureAudioBar(container) {
    let bar = container.querySelector(".prog-audio-bar");
    if (!bar) {
      bar = document.createElement("details");
      bar.className = "prog-audio-bar";
      bar.innerHTML = audioBarHTML();
      container.appendChild(bar);
      bindAudioBar(container, bar);
      bar.querySelectorAll("output").forEach((out) => {
        const id = out.getAttribute("for");
        if (id && (id.includes("Volume") || id.includes("bpm") || id.endsWith("s") || id.startsWith("fe_"))) {
          if (id.includes("Volume") || id === "masterVolume" || id === "volume") out.dataset.unit = " dB";
          else if (id === "fe_baseFrequency") out.dataset.unit = " Hz";
          else if (["attack", "decay", "release", "fe_attack", "fe_decay", "fe_release"].includes(id)) out.dataset.unit = " s";
        }
      });
    } else {
      syncAudioBarValues(bar);
    }
    return bar;
  }

  const HELPER_PY = `
import jazz21 as _j, json as _json

def _widget_analizar(tonalidad, simbolos, modo, nombre=""):
    return _json.dumps(_j.progresion_para_ui(tonalidad, simbolos, modo, nombre))

def _widget_sugerencias(tonalidad, simbolos, indice, modo):
    return _json.dumps(_j.sugerencias_contextuales(tonalidad, simbolos, indice, modo))
`;

  // ── Audio ────────────────────────────────────────────────────────────────

  function ensureTone() {
    if (toneReady) return Promise.resolve();
    return new Promise((resolve) => {
      if (typeof Tone !== "undefined") {
        toneReady = true;
        resolve();
        return;
      }
      const s = document.createElement("script");
      s.src = "https://cdnjs.cloudflare.com/ajax/libs/tone/14.7.77/Tone.js";
      s.onload = () => { toneReady = true; resolve(); };
      document.head.appendChild(s);
    });
  }

  let synth = null;

  function disposeSynth() {
    if (synth) {
      try { synth.dispose(); } catch (_) { /* already disposed */ }
      synth = null;
    }
  }

  function getSynth() {
    if (typeof Tone === "undefined") return null;
    if (!synth) {
      synth = new Tone.PolySynth(voiceClass(audioSettings.voice), {
        ...buildSynthOptions(),
        maxPolyphony: audioSettings.maxPolyphony,
      }).toDestination();
      synth._jazz21Voice = audioSettings.voice;
      synth._jazz21Polyphony = audioSettings.maxPolyphony;
      synth._jazz21Oscillator = audioSettings.oscillatorType;
      Tone.Destination.volume.value = audioSettings.masterVolume;
    }
    return synth;
  }

  function stopAudio() {
    isPlaying = false;
    if (typeof Tone !== "undefined") {
      clearPendingChordBoundary();
      Tone.Transport.stop();
      Tone.Transport.cancel();
      Tone.Transport.loop = false;
      scheduledEvents = [];
      const s = getSynth();
      s?.releaseAll();
    }
    playbackSession = null;
    scheduledEvents = [];
  }

  async function playProgression(prog, onStep, onStop) {
    await ensureTone();
    await Tone.start();
    stopAudio();
    isPlaying = true;
    playbackSession = {
      prog,
      onStep,
      onStop: onStop || null,
      chordIndex: 0,
      pendingEventId: null,
      lastChordStartTime: 0,
      activeChordDur: chordDurationSeconds(),
    };
    updateTransportLoop(prog);
    if (!Tone.Transport.state || Tone.Transport.state === "stopped") {
      Tone.Transport.start();
    }
    playChordStep(true);
  }

  // ── Pyodide (lazy) ───────────────────────────────────────────────────────

  async function ensurePyodide() {
    if (pyInstance) return pyInstance;
    if (!globalThis.Jazz21Playground) {
      throw new Error("Pyodide no cargado — recarga la página");
    }
    if (!pyBootPromise) {
      pyBootPromise = (async () => {
        const py = await Jazz21Playground.ensurePyodide(() => {});
        await py.runPythonAsync(HELPER_PY);
        pyInstance = py;
        pyHelperReady = true;
        return py;
      })().catch((err) => {
        pyBootPromise = null;
        throw err;
      });
    }
    return pyBootPromise;
  }

  function simbolosDeProg(prog) {
    return prog.acordes.map((c) => c.simbolo);
  }

  async function reanalizarProg(prog) {
    const py = await ensurePyodide();
    const raw = await py.runPythonAsync(
      `_widget_analizar(${JSON.stringify(prog.tonalidad)}, ${JSON.stringify(simbolosDeProg(prog))}, ${JSON.stringify(prog.modo)}, ${JSON.stringify(prog.nombre || "")})`
    );
    const data = JSON.parse(raw);
    return { ...prog, ...data };
  }

  async function cargarSugerencias(prog, index) {
    try {
      const py = await ensurePyodide();
      const raw = await py.runPythonAsync(
        `_widget_sugerencias(${JSON.stringify(prog.tonalidad)}, ${JSON.stringify(simbolosDeProg(prog))}, ${index}, ${JSON.stringify(prog.modo)})`
      );
      return JSON.parse(raw);
    } catch (err) {
      console.warn("jazz21/Pyodide:", err);
      return sugerenciasLocales(prog, index);
    }
  }

  /** Fallback sin Pyodide: variantes de calidad de la misma raíz. */
  function sugerenciasLocales(prog, index) {
    const sym = prog.acordes[index].simbolo;
    const root = parseRoot(sym);
    const q0 = parseQuality(sym);
    return QUALITY_CYCLE
      .filter((q) => q !== q0)
      .map((q) => ({
        simbolo: root + q,
        grado: null,
        funcion: null,
        tipo_funcion: null,
        diatonico: false,
      }));
  }

  // ── Chord helpers ────────────────────────────────────────────────────────

  function parseRoot(sym) {
    const m = (sym || "").match(/^([A-G](?:#|b)?)/);
    return m ? m[1] : sym;
  }

  function parseQuality(sym) {
    const root = parseRoot(sym);
    return sym.slice(root.length);
  }

  function cycleQuality(sym, dir) {
    const root = parseRoot(sym);
    const q = parseQuality(sym);
    let i = QUALITY_CYCLE.indexOf(q);
    if (i === -1) i = 0;
    i = (i + dir + QUALITY_CYCLE.length) % QUALITY_CYCLE.length;
    return root + QUALITY_CYCLE[i];
  }

  function fnMeta(chord) {
    let fnLabel, fnColor;
    switch (chord.tipo_funcion) {
      case "tonal":
        fnColor = FN_COLOR[chord.funcion] || "var(--muted)";
        fnLabel = chord.funcion;
        break;
      case "dominante_secundaria":
        fnColor = "#ffb86c";
        fnLabel = chord.funcion;
        break;
      case "tritone_substitution":
        fnColor = "#ff79c6";
        fnLabel = chord.funcion || "SubV";
        break;
      case "backdoor_dominant":
        fnColor = "#50fa7b";
        fnLabel = chord.funcion || "Backdoor";
        break;
      case "cambio_tonal":
        fnColor = "#f1fa8c";
        fnLabel = "cambio tonal";
        break;
      case "prestamo_modal": {
        const best = (chord.hints || []).find((h) => h.tipo === "modal");
        fnColor = "#bd93f9";
        fnLabel = best ? `← ${MODO_ES[best.modo.toLowerCase()] || best.modo}` : "préstamo";
        break;
      }
      default:
        if (chord.funcion) {
          fnColor = FN_COLOR[chord.funcion] || "var(--muted)";
          fnLabel = chord.funcion;
        } else if (chord.diatonico) {
          fnColor = "#64d2d2";
          fnLabel = "diatónico";
        } else if (chord.funcion_detalle) {
          fnColor = "#c8902a";
          fnLabel = chord.funcion_detalle;
        } else if ((chord.hints || []).length) {
          const best = chord.hints.find((h) => h.tipo === "modal");
          fnColor = "#bd93f9";
          fnLabel = best ? `← ${MODO_ES[best.modo.toLowerCase()] || best.modo}` : "préstamo";
        } else {
          fnColor = "var(--muted)";
          fnLabel = null;
        }
    }
    return { fnLabel, fnColor };
  }

  function chipMetaLine(chord) {
    const grado = chord.grado || "?";
    const { fnLabel, fnColor } = fnMeta(chord);
    if (fnLabel) {
      return { text: `${grado} · ${fnLabel}`, color: fnColor };
    }
    return { text: grado, color: "var(--muted)" };
  }

  function resumenLinea(chord) {
    const { text } = chipMetaLine(chord);
    return `${chord.simbolo} · ${text}`;
  }

  // ── Render ───────────────────────────────────────────────────────────────

  function cloneProg(prog) {
    return JSON.parse(JSON.stringify(prog));
  }

  function chipHTML(chord, index, total, selected) {
    const arrow = index < total - 1 ? `<span class="prog-arrow">→</span>` : "";
    const { text, color } = chipMetaLine(chord);
    const sel = selected ? " prog-chip-selected" : "";
    const active = chord._active ? " prog-chip-active" : "";

    return `
      <div class="prog-chip-wrap" data-index="${index}" draggable="true">
        <div class="prog-chip${sel}${active}" data-index="${index}" tabindex="0">
          <span class="prog-chip-symbol">${chord.simbolo}</span>
          <span class="prog-chip-meta" style="color:${color}">${text}</span>
        </div>
        <button type="button" class="prog-chip-otra" data-index="${index}" title="Alternativa cercana">↻</button>
      </div>${arrow}`;
  }

  function paletteHTML(chord, loading, error) {
    if (loading) {
      return `<div class="prog-palette"><span class="prog-palette-status">Cargando jazz21…</span></div>`;
    }
    if (error) {
      return `<div class="prog-palette"><span class="prog-palette-status prog-palette-error">${error}</span></div>`;
    }
    const items = suggestions.map((s, i) => {
      const active = i === suggestIndex ? " prog-palette-active" : "";
      const { text } = chipMetaLine(s);
      return `<button type="button" class="prog-palette-btn${active}" data-sym="${s.simbolo}">
        <span class="prog-palette-sym">${s.simbolo}</span>
        <span class="prog-palette-meta">${text}</span>
      </button>`;
    }).join("");

    return `
      <div class="prog-palette" data-index="${selectedIndex}">
        <div class="prog-palette-current">${resumenLinea(chord)}</div>
        <div class="prog-palette-grid">${items || '<span class="prog-palette-status">Sin sugerencias</span>'}</div>
        <p class="prog-palette-hint">Doble clic · editar · ↑↓ calidad · arrastrar · reordenar</p>
      </div>`;
  }

  function renderProg(container, prog) {
    currentProg = prog;
    const modoLabel = MODO_ES[prog.modo] || prog.modo;
    const patronTag = prog.patron ? ` · ${prog.patron.replace(/_/g, " ")}` : "";

    let body = container.querySelector(".prog-body");
    if (!body) {
      container.innerHTML = `<div class="prog-body"></div>`;
      body = container.querySelector(".prog-body");
      ensureAudioBar(container);
    }

    body.innerHTML = `
      <div class="prog-header">
        <span class="prog-nombre">${prog.nombre}</span>
        <span class="prog-meta">${prog.tonalidad} ${modoLabel}${patronTag}</span>
        <div class="prog-btns">
          <button class="prog-btn prog-play" type="button">▶ Reproducir</button>
          ${libraryApiAvailable ? `<button class="prog-btn prog-save" type="button" title="${libraryAuthenticated ? (libraryDetailUuid ? "Guardar cambios" : "Guardar en tu library") : "Inicia sesión para guardar"}">${libraryAuthenticated ? "☆ Guardar" : "☆ Entrar y guardar"}</button>` : ""}
          ${libraryDetailUuid ? "" : '<button class="prog-btn prog-otra" type="button">↻ Otra</button>'}
        </div>
      </div>
      <div class="prog-chips">
        ${prog.acordes.map((c, i) => chipHTML(c, i, prog.acordes.length, i === selectedIndex)).join("")}
      </div>
      <div class="prog-palette-slot">
        ${selectedIndex !== null ? paletteHTML(prog.acordes[selectedIndex], paletteLoading, paletteError) : ""}
      </div>
    `;

    bindProgEvents(container, prog);
    ensureAudioBar(container);
  }

  function bindProgEvents(container, prog) {
    const chips = container.querySelectorAll(".prog-chip");
    const playBtn = container.querySelector(".prog-play");
    const saveBtn = container.querySelector(".prog-save");
    const otraBtn = container.querySelector(".prog-otra");
    const paletteSlot = container.querySelector(".prog-palette-slot");

    playBtn.addEventListener("click", async () => {
      if (isPlaying) {
        stopAudio();
        playBtn.textContent = "▶ Reproducir";
        chips.forEach((c) => c.classList.remove("prog-chip-active"));
        return;
      }
      playBtn.textContent = "■ Parar";
      await playProgression(
        prog,
        (stepIndex) => {
          chips.forEach((c) => c.classList.remove("prog-chip-active"));
          chips[stepIndex]?.classList.add("prog-chip-active");
        },
        () => {
          playBtn.textContent = "▶ Reproducir";
          chips.forEach((c) => c.classList.remove("prog-chip-active"));
        }
      );
    });

    otraBtn?.addEventListener("click", () => {
      stopAudio();
      selectedIndex = null;
      suggestions = [];
      currentIndex = (currentIndex + 1) % progressions.length;
      currentProg = cloneProg(progressions[currentIndex]);
      renderProg(container, currentProg);
    });

    saveBtn?.addEventListener("click", () => saveCurrentProgression());

    container.querySelectorAll(".prog-chip").forEach((chip) => {
      const idx = Number(chip.dataset.index);

      chip.addEventListener("click", (e) => {
        if (e.target.closest(".prog-chip-edit")) return;
        selectChip(container, idx);
      });

      chip.addEventListener("dblclick", (e) => {
        e.preventDefault();
        startInlineEdit(container, idx);
      });

      chip.addEventListener("keydown", (e) => {
        if (selectedIndex !== idx) return;
        if (e.key === "Enter") {
          e.preventDefault();
          startInlineEdit(container, idx);
        } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
          e.preventDefault();
          const dir = e.key === "ArrowUp" ? 1 : -1;
          const next = cycleQuality(prog.acordes[idx].simbolo, dir);
          applyChord(container, idx, next);
        } else if (e.key === "Escape") {
          deselectChip(container);
        }
      });

      chip.addEventListener("wheel", (e) => {
        if (selectedIndex !== idx) return;
        e.preventDefault();
        const dir = e.deltaY < 0 ? 1 : -1;
        applyChord(container, idx, cycleQuality(prog.acordes[idx].simbolo, dir));
      }, { passive: false });
    });

    container.querySelectorAll(".prog-chip-otra").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const idx = Number(btn.dataset.index);
        await cycleSuggestion(container, idx);
      });
    });

    // Drag reorder
    let dragFrom = null;
    container.querySelectorAll(".prog-chip-wrap").forEach((wrap) => {
      wrap.addEventListener("dragstart", (e) => {
        dragFrom = Number(wrap.dataset.index);
        e.dataTransfer.effectAllowed = "move";
      });
      wrap.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
      });
      wrap.addEventListener("drop", async (e) => {
        e.preventDefault();
        const to = Number(wrap.dataset.index);
        if (dragFrom === null || dragFrom === to) return;
        const syms = simbolosDeProg(currentProg);
        const [moved] = syms.splice(dragFrom, 1);
        syms.splice(to, 0, moved);
        await applySymbols(container, syms, to);
        dragFrom = null;
      });
    });

  }

  async function selectChip(container, index) {
    if (selectedIndex === index) {
      deselectChip(container);
      return;
    }
    selectedIndex = index;
    suggestions = [];
    suggestIndex = 0;
    paletteError = null;
    paletteLoading = true;
    renderProg(container, currentProg);
    try {
      suggestions = await cargarSugerencias(currentProg, index);
    } catch (err) {
      suggestions = sugerenciasLocales(currentProg, index);
      paletteError = err.message || "Sin análisis completo";
    } finally {
      paletteLoading = false;
      renderProg(container, currentProg);
      bindPalette(container);
    }
  }

  function deselectChip(container) {
    selectedIndex = null;
    suggestions = [];
    paletteError = null;
    paletteLoading = false;
    renderProg(container, currentProg);
  }

  function bindPalette(container) {
    container.querySelectorAll(".prog-palette-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sym = btn.dataset.sym;
        if (selectedIndex !== null && sym) {
          applyChord(container, selectedIndex, sym);
        }
      });
    });
  }

  async function cycleSuggestion(container, index) {
    if (selectedIndex !== index || !suggestions.length) {
      await selectChip(container, index);
    }
    if (!suggestions.length) return;
    suggestIndex = (suggestIndex + 1) % suggestions.length;
    const sym = suggestions[suggestIndex].simbolo;
    await applyChord(container, index, sym, { keepSuggestions: true });
    try {
      suggestions = await cargarSugerencias(currentProg, index);
    } catch (_) {
      suggestions = sugerenciasLocales(currentProg, index);
    }
    suggestIndex = Math.max(0, suggestions.findIndex((s) => s.simbolo === sym));
    if (suggestIndex < 0) suggestIndex = 0;
    renderProg(container, currentProg);
    bindPalette(container);
  }

  function startInlineEdit(container, index) {
    const chip = container.querySelector(`.prog-chip[data-index="${index}"]`);
    if (!chip) return;
    const sym = currentProg.acordes[index].simbolo;
    const symbolEl = chip.querySelector(".prog-chip-symbol");
    const input = document.createElement("input");
    input.type = "text";
    input.className = "prog-chip-edit";
    input.value = sym;
    symbolEl.replaceWith(input);
    input.focus();
    input.select();

    const commit = async () => {
      const val = input.value.trim();
      if (val && val !== sym) {
        await applyChord(container, index, val);
      } else {
        renderProg(container, currentProg);
      }
    };

    input.addEventListener("blur", commit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        input.blur();
      } else if (e.key === "Escape") {
        renderProg(container, currentProg);
      }
    });
  }

  async function applyChord(container, index, sym, opts) {
    const syms = simbolosDeProg(currentProg);
    syms[index] = sym;
    await applySymbols(container, syms, index, opts);
  }

  async function applySymbols(container, syms, selectAfter, opts = {}) {
    stopAudio();
    paletteLoading = !opts.keepSuggestions;
    if (!opts.keepSuggestions) paletteError = null;
    try {
      const py = await ensurePyodide();
      const raw = await py.runPythonAsync(
        `_widget_analizar(${JSON.stringify(currentProg.tonalidad)}, ${JSON.stringify(syms)}, ${JSON.stringify(currentProg.modo)}, ${JSON.stringify(currentProg.nombre || "")})`
      );
      const data = JSON.parse(raw);
      currentProg = { ...currentProg, ...data };
      selectedIndex = selectAfter;
      if (!opts.keepSuggestions) {
        suggestions = await cargarSugerencias(currentProg, selectAfter);
        suggestIndex = 0;
      }
    } catch (e) {
      console.warn("Re-análisis:", e);
      currentProg.acordes = syms.map((s) => ({
        simbolo: s,
        notas: [],
        grado: null,
        funcion: null,
        tipo_funcion: null,
        diatonico: false,
        hints: [],
      }));
      if (!opts.keepSuggestions) {
        suggestions = sugerenciasLocales(currentProg, selectAfter);
        paletteError = "Modo local — ejecuta: python -m build --wheel -o site/wheels";
      }
    } finally {
      paletteLoading = false;
    }
    renderProg(container, currentProg);
    bindPalette(container);
    container.querySelector(`.prog-chip[data-index="${selectAfter}"]`)?.focus();
  }

  // ── Library (Django local) ───────────────────────────────────────────────

  function getCsrfToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  async function detectLibraryApi() {
    try {
      const r = await fetch("/api/csrf/", { credentials: "same-origin" });
      if (!r.ok) return false;
      const data = await r.json();
      libraryAuthenticated = Boolean(data.authenticated);
      libraryUsername = data.username || null;
      return Boolean(data.csrfToken);
    } catch {
      return false;
    }
  }

  function injectLibraryNav() {
    const nav = document.querySelector(".site-header .nav-links");
    if (!nav || !libraryApiAvailable || nav.querySelector(".library-nav-link")) return;
    const link = document.createElement("a");
    link.className = "library-nav-link";
    link.href = libraryAuthenticated ? "/profile/" : "/login/";
    link.textContent = libraryAuthenticated
      ? (libraryUsername ? `Perfil (${libraryUsername})` : "Perfil")
      : "Entrar";
    nav.insertBefore(link, nav.firstChild);
  }

  function buildSavePayload(prog) {
    return {
      saved_from: "widget",
      title: prog.nombre,
      key: prog.tonalidad,
      mode: prog.modo,
      chords: prog.acordes.map((c) => c.simbolo),
      progression: prog,
      selected_chord_index: selectedIndex,
      widget_state: {
        selected_key: prog.tonalidad,
        selected_mode: prog.modo,
        current_progression: prog,
        selected_chord_index: selectedIndex,
        filters: {},
        ui_state: {},
      },
    };
  }

  async function saveCurrentProgression() {
    if (!libraryAuthenticated) {
      window.location.href = `/login/?next=${encodeURIComponent(location.pathname)}`;
      return;
    }
    const payload = buildSavePayload(currentProg);
    const url = libraryDetailUuid
      ? `/progressions/${libraryDetailUuid}/save/`
      : "/progressions/save/";
    const r = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });
    if (r.status === 401 || r.status === 403) {
      window.location.href = `/login/?next=${encodeURIComponent(location.pathname)}`;
      return;
    }
    if (!r.ok) {
      console.error("save failed", await r.text());
      paletteError = "No se pudo guardar — revisa la consola";
      const widget = document.getElementById("prog-widget");
      if (widget) renderProg(widget, currentProg);
      return;
    }
    const data = await r.json();
    if (libraryDetailUuid) {
      paletteError = null;
      const widget = document.getElementById("prog-widget");
      if (widget) renderProg(widget, currentProg);
      return;
    }
    window.location.href = data.url;
  }

  // ── Init ─────────────────────────────────────────────────────────────────

  async function init() {
    const container = document.getElementById("prog-widget");
    if (!container) return;

    libraryApiAvailable = await detectLibraryApi();
    injectLibraryNav();

    libraryDetailUuid = container.dataset.libraryUuid || null;
    const bootstrapEl = document.getElementById("prog-widget-bootstrap");

    if (bootstrapEl) {
      const bootstrap = JSON.parse(bootstrapEl.textContent);
      currentProg = cloneProg(bootstrap.progression);
      if (bootstrap.selected_chord_index != null) {
        selectedIndex = bootstrap.selected_chord_index;
      }
      renderProg(container, currentProg);
      document.addEventListener("click", (e) => {
        if (selectedIndex === null) return;
        if (!e.target.closest(".prog-widget")) {
          deselectChip(container);
        }
      });
      return;
    }

    try {
      const res = await fetch("js/progressions.json");
      progressions = await res.json();
    } catch (_) {
      container.innerHTML = "";
      return;
    }

    if (!progressions.length) { container.innerHTML = ""; return; }

    currentIndex = Math.floor(Math.random() * progressions.length);
    currentProg = cloneProg(progressions[currentIndex]);
    renderProg(container, currentProg);

    document.addEventListener("click", (e) => {
      if (selectedIndex === null) return;
      if (!e.target.closest(".prog-widget")) {
        deselectChip(container);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
