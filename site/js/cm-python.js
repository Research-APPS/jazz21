/**
 * Inicializa CodeMirror con modo Python y tema Dracula
 * en todos los playgrounds de la página.
 *
 * Requiere que pyodide-playground.js ya haya capturado las referencias
 * al textarea antes de que este script lo reemplace visualmente.
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-playground]").forEach((container) => {
    const textarea = container.querySelector(".pg-editor");
    const runBtn   = container.querySelector(".pg-run");
    const resetBtn = container.querySelector(".pg-reset");
    if (!textarea) return;

    const defaultCode = textarea.value;

    const cm = CodeMirror.fromTextArea(textarea, {
      mode:           "python",
      theme:          "dracula",
      lineNumbers:    true,
      indentUnit:     4,
      tabSize:        4,
      indentWithTabs: false,
      lineWrapping:   false,
      extraKeys: {
        Tab: (editor) => editor.execCommand("insertSoftTab"),
      },
    });

    // Expone la instancia para que otros scripts puedan actualizar el código
    container._cm = cm;

    // Sincroniza CM → textarea justo antes de que Pyodide lea editor.value
    runBtn?.addEventListener("mousedown", () => cm.save(), true);

    // Pyodide-playground.js restaura textarea.value en reset;
    // nosotros esperamos un tick y luego sincronizamos CM
    resetBtn?.addEventListener("click", () => {
      setTimeout(() => cm.setValue(defaultCode), 0);
    });
  });
});
