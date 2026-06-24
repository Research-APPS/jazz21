/**
 * Playground Pyodide reutilizable para la biblioteca jazz21.
 * Carga music21 + wheel local de jazz21 y ejecuta código del editor.
 */
(function (global) {
  const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
  const WHEEL_NAME = "jazz21-0.1.0-py3-none-any.whl";
  const GALLERY_MARKER = "__JAZZ21_GALLERY__";

  let pyodidePromise = null;

  const playgroundScriptSrc =
    (document.currentScript && document.currentScript.src) || "";

  function wheelUrlFromPage() {
    if (playgroundScriptSrc) {
      return new URL("../wheels/" + WHEEL_NAME, playgroundScriptSrc).href;
    }
    return new URL("wheels/" + WHEEL_NAME, global.location.href).href;
  }

  function appendStreamChunk(target, chunk) {
    if (!chunk) return;
    target += chunk;
    if (!target.endsWith("\n") && !chunk.endsWith("\n")) {
      target += "\n";
    }
    return target;
  }

  function splitGalleryPayload(stdout) {
    const idx = stdout.indexOf(GALLERY_MARKER);
    if (idx === -1) {
      return { text: stdout, items: null };
    }
    const text = stdout.slice(0, idx).trimEnd();
    const after = stdout.slice(idx + GALLERY_MARKER.length);
    const jsonLine = after.split("\n")[0].trim();
    try {
      const items = JSON.parse(jsonLine);
      if (Array.isArray(items)) {
        return { text, items };
      }
    } catch (_e) {
      /* fall through */
    }
    return { text: stdout, items: null };
  }

  function extractSvgsAndCaptions(stdout) {
    const captions = [
      ...stdout.matchAll(/===\s*([^=]+?)\s*===/g),
    ].map((m) => m[1].trim());
    const svgs = [...stdout.matchAll(/<svg[\s\S]*?<\/svg>/gi)].map((m) => m[0]);
    return { captions, svgs };
  }

  function renderGalleryCards(galleryEl, items) {
    galleryEl.innerHTML = "";
    items.forEach((item) => {
      const card = document.createElement("figure");
      card.className = "pg-svg-card";
      const cap = document.createElement("figcaption");
      cap.textContent = item.caption || "Diagrama";
      card.appendChild(cap);
      const wrap = document.createElement("div");
      wrap.innerHTML = item.svg || "";
      card.appendChild(wrap);
      galleryEl.appendChild(card);
    });
  }

  async function ensurePyodide(onStatus) {
    if (!pyodidePromise) {
      pyodidePromise = (async () => {
        onStatus?.("Cargando Pyodide…");
        const py = await loadPyodide({ indexURL: PYODIDE_URL });
        onStatus?.("Instalando music21…");
        await py.loadPackage("micropip");
        await py.runPythonAsync(`
import micropip
await micropip.install("music21", keep_going=True)
        `);
        onStatus?.("Instalando jazz21…");
        const wheel = wheelUrlFromPage();
        await py.runPythonAsync(`
import micropip
await micropip.install(${JSON.stringify(wheel)})
        `);
        onStatus?.("Listo");
        return py;
      })();
    }
    return pyodidePromise;
  }

  function init(container) {
    const editor = container.querySelector(".pg-editor");
    const runBtn = container.querySelector(".pg-run");
    const resetBtn = container.querySelector(".pg-reset");
    const statusEl = container.querySelector(".pg-status");
    const outEl = container.querySelector(".pg-output");
    const svgEl = container.querySelector(".pg-svg");
    const galleryEl = container.querySelector(".pg-svg-gallery");
    const galleryMode = container.hasAttribute("data-svg-gallery");
    const defaultCode = editor?.value || container.dataset.code || "";

    if (!editor || !runBtn || !outEl) return;

    const setStatus = (msg) => {
      if (statusEl) statusEl.textContent = msg;
    };

    const clearOutputs = () => {
      outEl.textContent = "";
      if (svgEl) svgEl.innerHTML = "";
      if (galleryEl) galleryEl.innerHTML = "";
    };

    resetBtn?.addEventListener("click", () => {
      editor.value = defaultCode;
      clearOutputs();
      setStatus("");
    });

    function renderSvgOutput(stdout) {
      const { text, items } = splitGalleryPayload(stdout);

      if (galleryEl && galleryMode) {
        if (svgEl) svgEl.innerHTML = "";
        if (items && items.length) {
          renderGalleryCards(galleryEl, items);
          return;
        }
        galleryEl.innerHTML = "";
        const { captions, svgs } = extractSvgsAndCaptions(stdout);
        if (svgs.length) {
          const fallbackItems = svgs.map((svg, i) => ({
            caption: captions[i] || `Opción ${i}`,
            svg,
          }));
          renderGalleryCards(galleryEl, fallbackItems);
        }
        return;
      }

      const svgMatch = stdout.match(/<svg[\s\S]*?<\/svg>/i);
      if (svgEl && svgMatch) {
        svgEl.innerHTML = svgMatch[0];
      }
    }

    function cleanTextForDisplay(stdout) {
      let text = stdout;
      if (text.includes(GALLERY_MARKER)) {
        const idx = text.indexOf(GALLERY_MARKER);
        const after = text.slice(idx + GALLERY_MARKER.length);
        const rest = after.split("\n").slice(1).join("\n");
        text = text.slice(0, idx).trimEnd() + (rest ? "\n" + rest.trim() : "");
      }
      if (galleryMode) {
        text = text.replace(/<svg[\s\S]*?<\/svg>/gi, "").trim();
      }
      text = text.replace(/^.*RequestsDependencyWarning.*$/gm, "").trim();
      text = text.replace(/^.*warnings\.warn.*$/gm, "").trim();
      return text;
    }

    runBtn.addEventListener("click", async () => {
      runBtn.disabled = true;
      clearOutputs();
      try {
        const py = await ensurePyodide(setStatus);
        let stdout = "";
        let stderr = "";
        py.setStdout({
          batched: (s) => {
            stdout = appendStreamChunk(stdout, s) ?? stdout;
          },
        });
        py.setStderr({
          batched: (s) => {
            stderr = appendStreamChunk(stderr, s) ?? stderr;
          },
        });
        setStatus("Ejecutando…");
        await py.runPythonAsync(editor.value);
        const displayOut = cleanTextForDisplay(stdout);
        outEl.textContent = displayOut || "(sin salida)";
        renderSvgOutput(stdout);
        if (stderr.trim() && /Warning/i.test(stderr)) {
          setStatus("Hecho (avisos de dependencias ignorados en la salida)");
        }
      } catch (e) {
        outEl.textContent = (e && e.message) ? e.message : String(e);
        setStatus("Error");
      } finally {
        runBtn.disabled = false;
        if (statusEl && statusEl.textContent === "Ejecutando…") {
          setStatus("Hecho");
        }
      }
    });
  }

  function initAll() {
    document.querySelectorAll("[data-playground]").forEach(init);
  }

  global.Jazz21Playground = {
    init,
    initAll,
    ensurePyodide,
    GALLERY_MARKER,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})(window);
