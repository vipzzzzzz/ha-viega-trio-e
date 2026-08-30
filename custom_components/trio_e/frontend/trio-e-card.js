/* trio-e-card.js — custom Lovelace card for the Viega Multiplex Trio E
 * Ships with the trio_e integration (github.com/vipzzzzzz/ha-viega-trio-e).
 * Zero dependencies: vanilla custom element, shadow DOM, no build step.
 *
 * Layouts: full (bathtub hero with animated, temperature-tinted water) and
 * compact (rows only). Presets use hold-to-start (~1 s) -> trio_e.fill_bath.
 */

const DEFAULT_ENTITIES = {
  water_temperature: "sensor.trio_e_water_temperature",
  fill_progress: "sensor.trio_e_fill_progress",
  running: "binary_sensor.trio_e_running",
  target_temperature: "number.trio_e_target_temperature",
  flow: "number.trio_e_flow",
  tap: "switch.trio_e_tap",
  popup: "valve.trio_e_drain_popup",
  stop: "button.trio_e_stop",
};

const DEFAULT_PRESETS = [
  { name: "Sander", temperature: 40, volume: 180 },
  { name: "Quick", temperature: 41, volume: 215 },
  { name: "Kids", temperature: 36, volume: 90 },
];

const HOLD_MS = 1000;
const SLIDER_DEBOUNCE_MS = 300;
const SLIDER_QUIET_MS = 1500; // ignore external updates this long after user input

/* Map water temperature (°C) to a tint: 20° cool blue -> 60° hot red.
 * RGB blend (not a hue sweep) so the midpoint never turns green. */
function waterColor(temp) {
  const t = Math.min(60, Math.max(20, Number(temp) || 38));
  const f = (t - 20) / 40; // 0..1
  const mix = (a, b) => Math.round(a + (b - a) * f);
  return `rgb(${mix(59, 224)}, ${mix(130, 75)}, ${mix(212, 58)})`;
}

class TrioECard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._built = false;
    this._holdTimer = null;
    this._sliderTimers = {};
    this._sliderQuietUntil = {};
  }

  static getConfigElement() {
    return document.createElement("trio-e-card-editor");
  }

  static getStubConfig() {
    return { presets: DEFAULT_PRESETS.map((p) => ({ ...p })) };
  }

  setConfig(config) {
    this._config = {
      name: config.name || "Bath",
      compact: !!config.compact,
      presets: (config.presets || DEFAULT_PRESETS).slice(0, 3),
      entities: { ...DEFAULT_ENTITIES, ...(config.entities || {}) },
    };
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    if (!this._built) this._build();
    this._update();
  }

  getCardSize() {
    return this._config && this._config.compact ? 4 : 7;
  }

  _st(key) {
    const id = this._config.entities[key];
    return this._hass && this._hass.states[id];
  }

  _num(key, fallback) {
    const s = this._st(key);
    const v = s ? parseFloat(s.state) : NaN;
    return Number.isFinite(v) ? v : fallback;
  }

  _running() {
    const s = this._st("running");
    return !!s && s.state === "on";
  }

  /* ---------- DOM construction (once) ---------- */

  _build() {
    const c = this._config;
    const tub = c.compact
      ? ""
      : `<div class="tubwrap">
          <svg class="tub" viewBox="0 0 300 110" preserveAspectRatio="none">
            <defs>
              <clipPath id="tubclip">
                <path d="M8 8 h284 a0 0 0 0 1 0 0 v58 a36 36 0 0 1 -36 36 h-212 a36 36 0 0 1 -36 -36 z"/>
              </clipPath>
            </defs>
            <g clip-path="url(#tubclip)">
              <rect class="water" x="0" y="110" width="300" height="110"/>
              <ellipse class="wave w1" cx="80" cy="0" rx="70" ry="6"/>
              <ellipse class="wave w2" cx="220" cy="0" rx="80" ry="7"/>
            </g>
            <path class="tubline" d="M8 8 h284 v58 a36 36 0 0 1 -36 36 h-212 a36 36 0 0 1 -36 -36 z"/>
          </svg>
          <div class="tublabel"></div>
        </div>`;

    this.shadowRoot.innerHTML = `
      <style>${TrioECard._css}</style>
      <ha-card>
        <div class="head">
          <div class="title"><ha-icon icon="mdi:bathtub-outline"></ha-icon><span class="name"></span></div>
          <div class="status"><span class="temp"></span><span class="dot"></span><span class="state"></span></div>
        </div>
        ${tub}
        <div class="sliders">
          <div class="srow">
            <span class="slabel">Temp</span>
            <input class="slider" id="s-temp" type="range" min="20" max="60" step="0.5">
            <span class="sval" id="v-temp"></span>
          </div>
          <div class="srow">
            <span class="slabel">Flow</span>
            <input class="slider" id="s-flow" type="range" min="0" max="100" step="5">
            <span class="sval" id="v-flow"></span>
          </div>
        </div>
        <div class="btnrow">
          <button class="btn" id="b-tap"><ha-icon icon="mdi:faucet"></ha-icon><span>Tap</span></button>
          <button class="btn" id="b-popup"><ha-icon icon="mdi:water-circle"></ha-icon><span>Plug</span></button>
          <button class="btn warn" id="b-stop"><ha-icon icon="mdi:stop-circle-outline"></ha-icon><span>Stop</span></button>
        </div>
        <div class="presets"></div>
        <div class="runbar hidden">
          <div class="runinfo"></div>
          <button class="bigstop" id="b-bigstop"><ha-icon icon="mdi:stop"></ha-icon> STOP</button>
        </div>
      </ha-card>`;

    const $ = (sel) => this.shadowRoot.querySelector(sel);
    $(".name").textContent = c.name;

    // presets
    const box = $(".presets");
    c.presets.forEach((p, i) => {
      const chip = document.createElement("button");
      chip.className = "preset";
      chip.innerHTML = `
        <svg class="ring" viewBox="0 0 36 36"><circle class="ringbg" cx="18" cy="18" r="15.5"/><circle class="ringfg" cx="18" cy="18" r="15.5"/></svg>
        <span class="pname">${p.name}</span>
        <span class="pmeta">${p.temperature}° · ${p.volume} L</span>`;
      this._bindHold(chip, p);
      box.appendChild(chip);
    });

    // buttons
    $("#b-tap").addEventListener("click", () => this._toggleTap());
    $("#b-popup").addEventListener("click", () => this._togglePopup());
    $("#b-stop").addEventListener("click", () => this._stop());
    $("#b-bigstop").addEventListener("click", () => this._stop());

    // sliders
    this._bindSlider("s-temp", "target_temperature", (v) => `${v.toFixed(1)}°`, "v-temp");
    this._bindSlider("s-flow", "flow", (v) => `${v.toFixed(0)}%`, "v-flow");

    this._built = true;
  }

  /* ---------- interactions ---------- */

  _bindHold(chip, preset) {
    const cancel = () => {
      if (this._holdTimer) clearTimeout(this._holdTimer);
      this._holdTimer = null;
      chip.classList.remove("holding");
    };
    chip.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      if (this._running()) return;
      chip.classList.add("holding");
      this._holdTimer = setTimeout(() => {
        cancel();
        this._hass.callService("trio_e", "fill_bath", {
          temperature: preset.temperature,
          volume: preset.volume,
        });
      }, HOLD_MS);
    });
    ["pointerup", "pointerleave", "pointercancel"].forEach((e) =>
      chip.addEventListener(e, cancel)
    );
    chip.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  _bindSlider(id, entityKey, fmt, valId) {
    const el = this.shadowRoot.getElementById(id);
    const val = this.shadowRoot.getElementById(valId);
    el.addEventListener("input", () => {
      this._sliderQuietUntil[entityKey] = Date.now() + SLIDER_QUIET_MS;
      val.textContent = fmt(parseFloat(el.value));
      if (this._sliderTimers[entityKey]) clearTimeout(this._sliderTimers[entityKey]);
      this._sliderTimers[entityKey] = setTimeout(() => {
        this._hass.callService("number", "set_value", {
          entity_id: this._config.entities[entityKey],
          value: parseFloat(el.value),
        });
      }, SLIDER_DEBOUNCE_MS);
    });
  }

  _toggleTap() {
    const on = this._st("tap") && this._st("tap").state === "on";
    this._hass.callService("switch", on ? "turn_off" : "turn_on", {
      entity_id: this._config.entities.tap,
    });
  }

  _togglePopup() {
    const s = this._st("popup");
    const open = s && s.state === "open";
    this._hass.callService("valve", open ? "close_valve" : "open_valve", {
      entity_id: this._config.entities.popup,
    });
  }

  _stop() {
    this._hass.callService("button", "press", {
      entity_id: this._config.entities.stop,
    });
  }

  /* ---------- state -> DOM updates ---------- */

  _update() {
    const $ = (sel) => this.shadowRoot.querySelector(sel);
    const running = this._running();
    const temp = this._num("water_temperature", NaN);
    const progress = this._num("fill_progress", 0);
    const color = waterColor(temp);

    $(".temp").textContent = Number.isFinite(temp) ? `${temp.toFixed(1)}°C` : "—";
    $(".dot").classList.toggle("on", running);
    $(".state").textContent = running
      ? progress > 0
        ? `filling ${progress.toFixed(0)}%`
        : "running"
      : "idle";

    // tub water (full layout only)
    const water = this.shadowRoot.querySelector(".water");
    if (water) {
      // level: progress when volume-filling; a low "flowing" level when tap runs
      const level = running ? Math.max(progress, 12) : 0;
      const h = (level / 100) * 94; // tub inner height
      water.setAttribute("y", String(102 - h));
      water.setAttribute("height", String(h + 8));
      water.style.fill = color;
      const waves = this.shadowRoot.querySelectorAll(".wave");
      waves.forEach((w) => {
        w.setAttribute("cy", String(102 - h));
        w.style.fill = color;
        w.style.opacity = running ? "0.45" : "0";
      });
      this.shadowRoot.querySelector(".tublabel").textContent = running
        ? progress > 0
          ? `${progress.toFixed(0)}%`
          : "filling…"
        : "";
    }

    // sliders (skip while the user is interacting)
    this._reflectSlider("s-temp", "v-temp", "target_temperature", (v) => `${v.toFixed(1)}°`);
    this._reflectSlider("s-flow", "v-flow", "flow", (v) => `${v.toFixed(0)}%`);

    // buttons
    const tapOn = this._st("tap") && this._st("tap").state === "on";
    $("#b-tap").classList.toggle("active", !!tapOn);
    const popupOpen = this._st("popup") && this._st("popup").state === "open";
    $("#b-popup").classList.toggle("active", !!popupOpen);
    $("#b-popup").title = "Note: shows last commanded position (no sensor in the drain)";

    // presets vs run bar
    $(".presets").classList.toggle("hidden", running);
    const runbar = $(".runbar");
    runbar.classList.toggle("hidden", !running);
    if (running) {
      $(".runinfo").innerHTML =
        progress > 0
          ? `<b>${progress.toFixed(0)}%</b> · target ${this._num("target_temperature", 0).toFixed(1)}°`
          : `water running · ${Number.isFinite(temp) ? temp.toFixed(1) : "—"}°`;
    }
  }

  _reflectSlider(id, valId, entityKey, fmt) {
    if (Date.now() < (this._sliderQuietUntil[entityKey] || 0)) return;
    const el = this.shadowRoot.getElementById(id);
    const v = this._num(entityKey, NaN);
    if (!Number.isFinite(v) || document.activeElement === el) return;
    el.value = String(v);
    this.shadowRoot.getElementById(valId).textContent = fmt(v);
  }
}

TrioECard._css = `
  ha-card { padding: 14px 16px 16px; }
  .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
  .title { display:flex; align-items:center; gap:8px; font-weight:600; font-size:1.05em; }
  .title ha-icon { color: var(--primary-color); }
  .status { display:flex; align-items:center; gap:8px; color: var(--secondary-text-color); font-size:0.95em; }
  .dot { width:9px; height:9px; border-radius:50%; background: var(--disabled-text-color); }
  .dot.on { background: var(--primary-color); box-shadow: 0 0 6px var(--primary-color); }

  .tubwrap { position:relative; margin:4px 0 10px; }
  .tub { width:100%; height:96px; display:block; }
  .tubline { fill:none; stroke: var(--divider-color, #444); stroke-width:3; }
  .water { transition: y .8s ease, height .8s ease, fill 1s ease; }
  .wave { transition: cy .8s ease, opacity .5s ease; }
  .w1 { animation: drift 3.2s ease-in-out infinite alternate; }
  .w2 { animation: drift 4.1s ease-in-out infinite alternate-reverse; }
  @keyframes drift { from { transform: translateX(-12px);} to { transform: translateX(12px);} }
  .tublabel { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
    font-size:1.3em; font-weight:700; color: var(--text-primary-color, #fff);
    text-shadow: 0 1px 3px rgba(0,0,0,.6); pointer-events:none; }

  .sliders { display:flex; flex-direction:column; gap:6px; margin-bottom:10px; }
  .srow { display:flex; align-items:center; gap:10px; }
  .slabel { width:42px; color: var(--secondary-text-color); font-size:.9em; }
  .sval { width:52px; text-align:right; font-variant-numeric: tabular-nums; }
  .slider { flex:1; accent-color: var(--primary-color); }

  .btnrow { display:flex; gap:8px; margin-bottom:12px; }
  .btn { flex:1; display:flex; align-items:center; justify-content:center; gap:6px;
    padding:8px 0; border-radius:12px; border:1px solid var(--divider-color,#444);
    background: var(--secondary-background-color); color: var(--primary-text-color);
    font: inherit; cursor:pointer; }
  .btn.active { border-color: var(--primary-color); color: var(--primary-color); }
  .btn.warn:hover { border-color: var(--error-color); color: var(--error-color); }

  .presets { display:flex; gap:8px; }
  .presets.hidden, .runbar.hidden { display:none; }
  .preset { position:relative; flex:1; display:flex; flex-direction:column; align-items:center; gap:2px;
    padding:12px 4px 10px; border-radius:14px; border:1px solid var(--divider-color,#444);
    background: var(--secondary-background-color); color: var(--primary-text-color);
    font: inherit; cursor:pointer; touch-action:none; user-select:none; -webkit-user-select:none; }
  .pname { font-weight:600; }
  .pmeta { font-size:.85em; color: var(--secondary-text-color); }
  .ring { position:absolute; top:4px; right:4px; width:20px; height:20px; }
  .ringbg { fill:none; stroke: var(--divider-color,#444); stroke-width:3; }
  .ringfg { fill:none; stroke: var(--primary-color); stroke-width:3;
    stroke-dasharray: 97.4; stroke-dashoffset: 97.4; transform: rotate(-90deg); transform-origin:center; }
  .preset.holding { border-color: var(--primary-color); }
  .preset.holding .ringfg { transition: stroke-dashoffset ${HOLD_MS}ms linear; stroke-dashoffset: 0; }

  .runbar { display:flex; align-items:center; gap:12px; }
  .runinfo { flex:1; font-size:1.05em; }
  .bigstop { flex:1; display:flex; align-items:center; justify-content:center; gap:6px;
    padding:14px 0; border-radius:14px; border:none; background: var(--error-color, #b3261e);
    color:#fff; font: inherit; font-weight:700; font-size:1.1em; cursor:pointer; }
`;

/* ---------- visual config editor ---------- */

class TrioECardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = {
      name: config.name || "Bath",
      compact: !!config.compact,
      presets: (config.presets || DEFAULT_PRESETS).slice(0, 3),
      entities: config.entities,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  _emit() {
    const config = { type: "custom:trio-e-card", ...this._config };
    if (!config.entities) delete config.entities;
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true })
    );
  }

  _render() {
    const c = this._config;
    while (c.presets.length < 3) c.presets.push({ name: "", temperature: 38, volume: 150 });
    this.shadowRoot.innerHTML = `
      <style>
        .grid { display:grid; grid-template-columns: 1fr 90px 90px; gap:6px; align-items:center; }
        label { display:flex; align-items:center; gap:8px; margin:10px 0; }
        input { font:inherit; padding:6px 8px; border-radius:6px; border:1px solid var(--divider-color,#666);
          background: var(--card-background-color); color: var(--primary-text-color); width:100%; box-sizing:border-box; }
        .h { font-size:.85em; color: var(--secondary-text-color); }
      </style>
      <label>Name <input id="name" value="${c.name}"></label>
      <label><input id="compact" type="checkbox" style="width:auto" ${c.compact ? "checked" : ""}> Compact layout (no bathtub graphic)</label>
      <div class="grid">
        <span class="h">Preset name</span><span class="h">Temp °C</span><span class="h">Volume L</span>
        ${c.presets
          .map(
            (p, i) => `
          <input id="pn${i}" value="${p.name}">
          <input id="pt${i}" type="number" min="20" max="60" step="0.5" value="${p.temperature}">
          <input id="pv${i}" type="number" min="1" max="500" step="5" value="${p.volume}">`
          )
          .join("")}
      </div>`;

    const upd = () => {
      const g = (id) => this.shadowRoot.getElementById(id);
      this._config.name = g("name").value || "Bath";
      this._config.compact = g("compact").checked;
      this._config.presets = [0, 1, 2].map((i) => ({
        name: g(`pn${i}`).value || `Preset ${i + 1}`,
        temperature: parseFloat(g(`pt${i}`).value) || 38,
        volume: parseFloat(g(`pv${i}`).value) || 150,
      }));
      this._emit();
    };
    this.shadowRoot.querySelectorAll("input").forEach((el) => el.addEventListener("change", upd));
  }
}

customElements.define("trio-e-card", TrioECard);
customElements.define("trio-e-card-editor", TrioECardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "trio-e-card",
  name: "Trio E Bath Card",
  description: "Bathtub control for the Viega Multiplex Trio E: manual controls + hold-to-start fill presets.",
  preview: true,
});
