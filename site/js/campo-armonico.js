(function () {
  const DEBOUNCE_MS = 300;

  const FN_CLASS = {
    "Tónica":       "tonica",
    "Subdominante": "subdominante",
    "Dominante":    "dominante",
  };

  // Modos por familia, igual que CHORDIA jazz-mode-depth-catalog
  const MODES = {
    major: [
      { id: "ionian",     label: "Jónico"    },
      { id: "lydian",     label: "Lidio"      },
      { id: "mixolydian", label: "Mixolidio"  },
    ],
    minor: [
      { id: "dorian",   label: "Dórico"  },
      { id: "aeolian",  label: "Eólico"  },
      { id: "phrygian", label: "Frigio"  },
      { id: "locrian",  label: "Locrio"  },
    ],
  };

  // Nombres de modo para los hints (clave music21 → español)
  const MODO_ES = {
    "Dorian":     "Dórico",
    "Phrygian":   "Frigio",
    "Lydian":     "Lidio",
    "Mixolydian": "Mixolidio",
    "Aeolian":    "Eólico",
    "Locrian":    "Locrio",
  };

  // ——— Cálculo de notas de escala (puro JS, sin Pyodide) ———
  const _CHROM_SHARP = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
  const _CHROM_FLAT  = ["C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"];
  const _FLAT_ROOTS  = new Set(["F","Bb","Eb","Ab","Db","Gb"]);
  const _MODE_IVLS   = {
    ionian:     [0,2,4,5,7,9,11],
    dorian:     [0,2,3,5,7,9,10],
    phrygian:   [0,1,3,5,7,8,10],
    lydian:     [0,2,4,6,7,9,11],
    mixolydian: [0,2,4,5,7,9,10],
    aeolian:    [0,2,3,5,7,8,10],
    locrian:    [0,1,3,5,6,8,10],
  };

  // Intervalo desde la tónica del modo hasta la tónica de la escala mayor padre.
  // Ej: C Dórico → padre Bb mayor (C está a 2 semis de Bb) → offset 2
  const _MODE_PARENT_OFFSET = {
    ionian: 0, dorian: 2, phrygian: 4, lydian: 5,
    mixolydian: 7, aeolian: 9, locrian: 11,
  };
  // PCs de las claves con bemoles: F Bb Eb Ab Db (excluimos Gb para no chocar con F#)
  const _FLAT_PARENT_PCS = new Set([5, 10, 3, 8, 1]);

  function _rootPc(root) {
    const i = _CHROM_SHARP.indexOf(root);
    return i !== -1 ? i : _CHROM_FLAT.indexOf(root);
  }

  function _useFlats(root, mode) {
    if (_FLAT_ROOTS.has(root)) return true;       // la raíz ya es bemol
    const rpc    = _rootPc(root);
    const offset = _MODE_PARENT_OFFSET[mode] || 0;
    const parentPc = (rpc - offset + 12) % 12;   // clave mayor padre
    return _FLAT_PARENT_PCS.has(parentPc);
  }

  function scaleNotes(root, mode) {
    const useFlats = _useFlats(root, mode);
    const chrom    = useFlats ? _CHROM_FLAT : _CHROM_SHARP;
    const rootIdx  = chrom.indexOf(root) !== -1 ? chrom.indexOf(root) : _rootPc(root);
    if (rootIdx === -1) return [];
    return (_MODE_IVLS[mode] || _MODE_IVLS.ionian).map(i => chrom[(rootIdx + i) % 12]);
  }

  // ——— Playground sincronizado ———
  // modos con función armónica completa (Ionian=Mayor, Aeolian=Menor)
  const FUNCTIONAL_MODES = new Set(["ionian", "aeolian"]);

  function buildPlaygroundCode(tonal, mode, modeLabel) {
    const isFunctional = FUNCTIONAL_MODES.has(mode);
    const modoArg = mode === "ionian" ? "" : `, "${mode}"`;   // omitir si es el default

    if (isFunctional) {
      return (
`import jazz21                               # cargamos la librería

tonalidad = "${tonal}"                          # tonalidad elegida${mode === "aeolian" ? `\nmodo      = "${mode}"                          # menor natural (eólico)` : ""}

# notas de la escala
print("Escala:", " · ".join(jazz21.notas_de(tonalidad${modoArg})))

# acordes diatónicos con función inferida
for acorde in jazz21.triadas_de(tonalidad${modoArg}):
    notas   = ", ".join(acorde["notas"])       # notas del acorde
    funcion = acorde["funcion"]               # función armónica
    grado   = acorde["grado"]                 # grado romano
    print(f'{grado:<6} {acorde["simbolo"]:<8} {funcion:<14}  [{notas}]')`
      );
    }
    return (
`import jazz21                               # cargamos la librería

tonalidad = "${tonal}"                          # tónica
modo      = "${mode}"                          # ${modeLabel}

# notas de la escala modal
print("Escala:", " · ".join(jazz21.notas_de(tonalidad, modo)))

# triadas del campo modal (terceras diatónicas automáticas)
for acorde in jazz21.triadas_de(tonalidad, modo):
    notas = ", ".join(acorde["notas"])         # notas del acorde
    grado = acorde["grado"]                   # grado modal (bIII, #IV…)
    print(f'{grado:<6} {acorde["simbolo"]:<8}  [{notas}]')`
    );
  }

  // ——— Código → UI (sync inverso al pulsar Ejecutar) ———
  function syncUIFromCode() {
    const pg = document.querySelector("[data-playground]");
    const cm = pg?._cm;
    if (!cm) return;
    const code = cm.getValue();

    // leer tonalidad = "X"
    const tMatch = code.match(/^tonalidad\s*=\s*["']([A-Ga-g][b#]?)["']/m);
    if (tMatch) {
      const t = tMatch[1];
      const opt = [...(tonalSelect?.options || [])].find(o => o.value === t || o.text === t);
      if (opt && tonalSelect.value !== t) {
        tonalSelect.value = t;
        renderEscalaNotas();
        if (acordesInput?.value?.trim()) scheduleAnalisis();
      }
    }

    // leer modo = "X"
    const mMatch = code.match(/^modo\s*=\s*["']([a-z]+)["']/m);
    if (mMatch) {
      const m = mMatch[1];
      if (m !== selectedMode && _MODE_IVLS[m]) {
        selectedMode   = m;
        selectedFamily = ["ionian","lydian","mixolydian"].includes(m) ? "major" : "minor";
        document.querySelectorAll(".modo-family-btn").forEach(b =>
          b.classList.toggle("active", b.dataset.family === selectedFamily)
        );
        renderModoChips();
        renderEscalaNotas();
        if (acordesInput?.value?.trim()) scheduleAnalisis();
      }
    }
  }

  function updatePlaygroundCode() {
    const pg = document.querySelector("[data-playground]");
    const cm = pg?._cm;
    if (!cm) return;
    const tonal     = tonalSelect?.value || "C";
    const modeEntry = (MODES[selectedFamily] || []).find(m => m.id === selectedMode);
    const modeLabel = modeEntry?.label || "Jónico";
    cm.setValue(buildPlaygroundCode(tonal, selectedMode, modeLabel));
  }

  function renderEscalaNotas() {
    const el = document.getElementById("campo-escala-notas");
    if (!el) return;
    const notes = scaleNotes(tonalSelect?.value || "C", selectedMode);
    el.innerHTML = notes.map((n, i) =>
      `<span class="esc-nota${i === 0 ? " esc-tonica" : ""}">${n}</span>`
    ).join(`<span class="esc-sep">·</span>`);
  }

  let pyInstance    = null;
  let debounceTimer = null;
  let helperReady   = false;
  let selectedFamily = "major";
  let selectedMode   = "ionian";

  function $(id) { return document.getElementById(id); }

  const tonalSelect  = $("tonalidad-select");
  const acordesInput = $("acordes-input");
  const statusEl     = $("campo-status");
  const resultadoEl  = $("campo-resultado");
  const modoChipsEl  = $("modo-chips");

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  // ——— Helper Python (se define una sola vez) ———
  const HELPER_PY = `
import jazz21 as _j, json as _json

def _analizar_campo(tonalidad, acordes, modo="ionian"):
    out = []
    for a in acordes:
        try:
            out.append(_j.analizar_en_tonalidad(tonalidad, a, modo))
        except Exception as e:
            out.append({"simbolo": a, "diatonico": False,
                        "notas": [], "intervalos": [], "hints": [], "error": str(e)})
    return _json.dumps(out)
`;

  async function ensureHelper() {
    if (!helperReady) {
      await pyInstance.runPythonAsync(HELPER_PY);
      helperReady = true;
    }
  }

  // ——— Modo UI ———
  function renderModoChips() {
    const chips = MODES[selectedFamily] || [];
    modoChipsEl.innerHTML = chips.map(({ id, label }) => {
      const active = id === selectedMode ? " modo-chip-active" : "";
      return `<button class="modo-chip${active}" data-mode="${id}">${label}</button>`;
    }).join("");

    modoChipsEl.querySelectorAll(".modo-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedMode = btn.dataset.mode;
        renderModoChips();
        renderEscalaNotas();
        updatePlaygroundCode();
        if (acordesInput.value.trim()) scheduleAnalisis();
      });
    });
  }

  function initFamilyToggle() {
    document.querySelectorAll(".modo-family-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedFamily = btn.dataset.family;
        selectedMode = selectedFamily === "major" ? "ionian" : "aeolian";
        document.querySelectorAll(".modo-family-btn").forEach((b) =>
          b.classList.toggle("active", b === btn)
        );
        renderModoChips();
        renderEscalaNotas();
        updatePlaygroundCode();
        if (acordesInput.value.trim()) scheduleAnalisis();
      });
    });
    renderModoChips();
    renderEscalaNotas();
  }

  // ——— Análisis ———
  async function analizar() {
    if (!pyInstance || !helperReady) return;

    const tonalidad = tonalSelect.value;
    const acordes   = (acordesInput.value || "").trim().split(/[\s,]+/).filter(Boolean);

    if (!acordes.length) { renderVacio(); return; }

    try {
      const raw  = await pyInstance.runPythonAsync(
        `_analizar_campo(${JSON.stringify(tonalidad)}, ${JSON.stringify(acordes)}, ${JSON.stringify(selectedMode)})`
      );
      renderChips(JSON.parse(raw));
    } catch (e) {
      resultadoEl.innerHTML = `<span class="campo-error">${e.message || String(e)}</span>`;
    }
  }

  // ——— Render ———
  function renderVacio() {
    resultadoEl.innerHTML =
      '<p class="campo-placeholder">Escribe acordes separados por espacios…</p>';
  }

  function buildDetail(a) {
    const rows = [];

    if (a.notas?.length) {
      const fuera = new Set(a.notas_fuera || []);
      // color del badge que describe por qué están fuera
      const hintColor = (() => {
        const first = (a.hints || [])[0];
        if (!first) return null;
        return first.tipo === "modal" ? "#bd93f9" : "#50c8c8";
      })();
      const notasHtml = a.notas.map(n => {
        if (fuera.has(n) && hintColor) {
          return `<span style="color:${hintColor};font-weight:700">${n}</span>`;
        }
        return `<span>${n}</span>`;
      }).join(`<span class="esc-sep"> · </span>`);
      rows.push(`<div class="chip-detail-row">
        <span class="chip-detail-label">Notas</span>
        <span class="chip-detail-val">${notasHtml}</span>
      </div>`);
    }
    if (a.intervalos?.length) {
      rows.push(`<div class="chip-detail-row">
        <span class="chip-detail-label">Intervalos</span>
        <span class="chip-detail-val">${a.intervalos.join(" · ")}</span>
      </div>`);
    }

    if (!a.diatonico) {
      // función: dominante secundaria, o desconocida
      if (a.funcion) {
        rows.push(`<div class="chip-detail-row">
          <span class="chip-detail-label">Función</span>
          <span class="chip-detail-val chip-fn-secdom">${a.funcion}${a.funcion_detalle ? ` · <em>${a.funcion_detalle}</em>` : ""}</span>
        </div>`);
      } else {
        rows.push(`<div class="chip-detail-row chip-fn-unknown">
          <span class="chip-detail-label">Función</span>
          <span class="chip-detail-val">— <em>requiere contexto</em></span>
        </div>`);
      }

      // procedencia modal
      const hints = (a.hints || []).map((h) => {
        if (h.tipo === "modal") {
          const es = MODO_ES[h.modo] || h.modo;
          return `<span class="chip-hint chip-hint-modal">Préstamo · ${tonalSelect.value} ${es}</span>`;
        }
        if (h.tipo === "relativo") {
          return `<span class="chip-hint chip-hint-rel">Relativo menor · ${h.tonica}m</span>`;
        }
        return "";
      }).filter(Boolean);

      if (hints.length) {
        rows.push(`<div class="chip-detail-row chip-detail-label" style="margin-top:0.4rem">Procedencia modal</div>`);
        rows.push(`<div class="chip-hints">${hints.join("")}</div>`);
      }
    }

    return rows.join("");
  }

  function renderChips(data) {
    resultadoEl.innerHTML = data.map((a) => {
      let cls, metaTx;
      if (a.diatonico) {
        cls    = a.funcion ? `chip-${FN_CLASS[a.funcion] || "tonica"}` : "chip-modal";
        metaTx = a.funcion ? `${a.grado} · ${a.funcion}` : a.grado;
      } else if (a.funcion) {
        // dominante secundaria u otra función inequívoca fuera de la escala
        cls    = "chip-secdom";
        metaTx = a.funcion;
      } else {
        cls    = "chip-nodia";
        metaTx = "⚠ no diatónico";
      }

      return `<div class="campo-chip ${cls}">
        <div class="chip-face">
          <span class="chip-simbolo">${a.simbolo}</span>
          <span class="chip-meta">${metaTx}</span>
        </div>
        <div class="chip-detail">${buildDetail(a)}</div>
      </div>`;
    }).join("");

    resultadoEl.querySelectorAll(".campo-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        chip.classList.remove("chip-shaking");
        chip.classList.toggle("chip-open");
      });
    });

    // Pokéball shake en chips no diatónicos → se abre al terminar si el usuario no lo hizo
    resultadoEl.querySelectorAll(".chip-nodia").forEach((chip) => {
      chip.classList.add("chip-shaking");
      chip.addEventListener("animationend", () => {
        chip.classList.remove("chip-shaking");
        if (!chip.classList.contains("chip-open")) {
          chip.classList.add("chip-open");
        }
      }, { once: true });
    });
  }

  function scheduleAnalisis() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(analizar, DEBOUNCE_MS);
  }

  // ——— Init ———
  async function init() {
    try {
      pyInstance = await Jazz21Playground.ensurePyodide(setStatus);
      await ensureHelper();
      setStatus("Listo");
      acordesInput.disabled    = false;
      acordesInput.placeholder = "C  Am  F  G";
      acordesInput.focus();
    } catch (e) {
      setStatus("Error al cargar jazz21");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    initFamilyToggle();

    acordesInput?.addEventListener("input", scheduleAnalisis);

    tonalSelect?.addEventListener("change", () => {
      renderEscalaNotas();
      updatePlaygroundCode();
      if (acordesInput.value.trim()) scheduleAnalisis();
    });

    // sync código → UI al pulsar Ejecutar (antes de que cm.save() envíe al textarea)
    document.querySelector("[data-playground] .pg-run")
      ?.addEventListener("mousedown", syncUIFromCode, true);

    renderVacio();
    init();
  });
})();
