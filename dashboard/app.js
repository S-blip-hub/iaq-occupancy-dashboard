/* IAQ dashboard: renders summary cards, an hourly profile and a daily chart
 * from window.IAQ_DATA (written by `python -m iaq.build`). No external
 * libraries, so the page works offline and on GitHub Pages. */

(function () {
  "use strict";

  const data = window.IAQ_DATA;
  if (!data) {
    document.body.insertAdjacentHTML("afterbegin",
      "<p>No data found. Run <code>python -m iaq.build &lt;export.xlsx&gt;</code> first.</p>");
    return;
  }

  const COLORS = { navy: "#1f4e79", grey: "#9aa5b1", amber: "#f0b429", red: "#c0392b", line: "#d9e0e8", ink: "#1a2433" };
  const pct = (x) => `${(100 * x).toFixed(1)}%`;
  const fmt = (x, d = 0) => Number(x).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });

  /* ---------- summary cards ---------- */
  function renderCards() {
    const s = data.summary;
    const cards = [
      ["Monitoring", `${s.days} days`, `${fmt(s.readings)} readings`],
      ["Mean indoor CO₂", `${fmt(s.indoor_co2_mean_ppm)} ppm`, `95th percentile ${fmt(s.indoor_co2_p95_ppm)} ppm`],
      ["Peak indoor CO₂", `${fmt(s.indoor_co2_max_ppm)} ppm`, `${pct(s.share_co2_poor)} of readings above 1200 ppm`],
      ["CO₂ when occupied", `${fmt(s.co2_when_occupied_mean_ppm)} ppm`, `vs ${fmt(s.co2_when_unoccupied_mean_ppm)} ppm unoccupied`],
      ["Likely occupied", pct(s.share_likely_occupied), "of all readings (CO₂ proxy)"],
      ["In comfort band", pct(s.share_in_comfort_band), "20–30 °C and 30–70% RH"],
    ];
    document.getElementById("cards").innerHTML = cards.map(([label, value, hint]) =>
      `<div class="card"><div class="label">${label}</div><div class="value">${value}</div><div class="hint">${hint}</div></div>`
    ).join("");
  }

  /* ---------- canvas helpers ---------- */
  function setupCanvas(canvas) {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = Number(canvas.getAttribute("height"));
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.font = "12px system-ui, sans-serif";
    return { ctx, width, height };
  }

  function niceRange(values, pad = 0.08) {
    const finite = values.filter(Number.isFinite);
    let lo = Math.min(...finite), hi = Math.max(...finite);
    const span = hi - lo || 1;
    return [lo - span * pad, hi + span * pad];
  }

  function axes(ctx, box, yRange, yLabel, xTicks) {
    const { x0, y0, x1, y1 } = box;
    ctx.strokeStyle = COLORS.line;
    ctx.fillStyle = "#5b6878";
    ctx.lineWidth = 1;
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const v = yRange[0] + (yRange[1] - yRange[0]) * (i / steps);
      const y = y1 - (y1 - y0) * (i / steps);
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.textBaseline = "middle";
      ctx.fillText(fmt(v, yRange[1] - yRange[0] < 20 ? 1 : 0), x0 - 6, y);
    }
    ctx.save();
    ctx.translate(12, (y0 + y1) / 2); ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center"; ctx.fillText(yLabel, 0, 0);
    ctx.restore();
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    xTicks.forEach(([x, label]) => ctx.fillText(label, x, y1 + 6));
  }

  function line(ctx, pts, color, width = 2) {
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
    pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.stroke();
  }

  function legend(ctx, items, x, y) {
    items.forEach(([label, color], i) => {
      const lx = x + i * 150;
      ctx.fillStyle = color; ctx.fillRect(lx, y - 5, 14, 10);
      ctx.fillStyle = COLORS.ink; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText(label, lx + 20, y);
    });
  }

  /* ---------- hourly profile ---------- */
  const METRICS = {
    co2: { label: "CO₂ (ppm)", name: "CO₂", unit: " ppm", inKey: "in_co2_ppm", outKey: "out_co2_ppm", digits: 0 },
    temp: { label: "Temperature (°C)", name: "temperature", unit: " °C", inKey: "in_temp_c", outKey: "out_temp_c", digits: 1 },
    rh: { label: "Indoor RH (%)", name: "relative humidity", unit: "%", inKey: "in_rh_pct", outKey: null, digits: 1 },
  };
  let currentMetric = "co2";

  function renderHourly() {
    const canvas = document.getElementById("hourly");
    const { ctx, width, height } = setupCanvas(canvas);
    const m = METRICS[currentMetric];
    const rows = data.hourly;
    const box = { x0: 56, y0: 28, x1: width - 16, y1: height - 28 };
    const values = rows.map((r) => r[m.inKey]).concat(m.outKey ? rows.map((r) => r[m.outKey]) : []);
    const yr = niceRange(values);
    const X = (h) => box.x0 + (box.x1 - box.x0) * (h / 23);
    const Y = (v) => box.y1 - (box.y1 - box.y0) * ((v - yr[0]) / (yr[1] - yr[0]));

    // occupancy share as background bars
    const bw = (box.x1 - box.x0) / 24 * 0.8;
    rows.forEach((r) => {
      const h = (box.y1 - box.y0) * r.occupied_share;
      ctx.fillStyle = "rgba(240,180,41,0.28)";
      ctx.fillRect(X(r.hour) - bw / 2, box.y1 - h, bw, h);
    });
    axes(ctx, box, yr, m.label, rows.filter((r) => r.hour % 3 === 0).map((r) => [X(r.hour), `${r.hour}:00`]));
    if (m.outKey) line(ctx, rows.map((r) => [X(r.hour), Y(r[m.outKey])]), COLORS.grey, 1.6);
    line(ctx, rows.map((r) => [X(r.hour), Y(r[m.inKey])]), currentMetric === "temp" ? COLORS.red : COLORS.navy, 2.4);
    const items = [["Indoor", currentMetric === "temp" ? COLORS.red : COLORS.navy]];
    if (m.outKey) items.push(["Outdoor", COLORS.grey]);
    items.push(["Likely occupied (share)", "rgba(240,180,41,0.5)"]);
    legend(ctx, items, box.x0, 12);

    const peak = rows.reduce((a, b) => (b[m.inKey] > a[m.inKey] ? b : a));
    document.getElementById("hourly-note").textContent =
      `Indoor ${m.name} peaks around ${peak.hour}:00 at ${fmt(peak[m.inKey], m.digits)}${m.unit} on an average day.`;
  }

  /* ---------- daily chart ---------- */
  function renderDaily() {
    const canvas = document.getElementById("daily");
    const { ctx, width, height } = setupCanvas(canvas);
    const rows = data.daily;
    const box = { x0: 56, y0: 28, x1: width - 16, y1: height - 28 };
    const co2r = [0, Math.max(...rows.map((r) => r.in_co2_max)) * 1.08];
    const tr = niceRange(rows.map((r) => r.in_temp_mean), 0.15);
    const n = rows.length;
    const step = (box.x1 - box.x0) / n;
    const X = (i) => box.x0 + step * (i + 0.5);
    const Yc = (v) => box.y1 - (box.y1 - box.y0) * (v / co2r[1]);
    const Yt = (v) => box.y1 - (box.y1 - box.y0) * ((v - tr[0]) / (tr[1] - tr[0]));

    const ticks = rows.map((r, i) => [X(i), r.date.slice(5)]).filter((_, i) => i % Math.ceil(n / 10) === 0);
    axes(ctx, box, co2r, "Peak indoor CO₂ (ppm)", ticks);
    rows.forEach((r, i) => {
      ctx.fillStyle = r.in_co2_max >= 1200 ? COLORS.red : r.in_co2_max >= 800 ? COLORS.amber : COLORS.navy;
      ctx.globalAlpha = 0.75;
      ctx.fillRect(X(i) - step * 0.35, Yc(r.in_co2_max), step * 0.7, box.y1 - Yc(r.in_co2_max));
      ctx.globalAlpha = 1;
    });
    line(ctx, rows.map((r, i) => [X(i), Yt(r.in_temp_mean)]), COLORS.ink, 1.4);
    legend(ctx, [["< 800 ppm", COLORS.navy], ["800–1200 ppm", COLORS.amber], ["> 1200 ppm", COLORS.red],
                 [`Mean temp (${fmt(tr[0], 0)}–${fmt(tr[1], 0)} °C)`, COLORS.ink]], box.x0, 12);

    const tip = document.getElementById("tooltip");
    canvas.onmousemove = (e) => {
      const rect = canvas.getBoundingClientRect();
      const i = Math.floor((e.clientX - rect.left - box.x0) / step);
      if (i < 0 || i >= n) { tip.hidden = true; return; }
      const r = rows[i];
      tip.textContent = `${r.date}\nPeak CO₂ ${fmt(r.in_co2_max)} ppm\nMean CO₂ ${fmt(r.in_co2_mean)} ppm\nMean temp ${fmt(r.in_temp_mean, 1)} °C\nLikely occupied ${fmt(r.occupied_hours, 1)} h`;
      tip.style.left = `${e.clientX + 12}px`; tip.style.top = `${e.clientY + 12}px`; tip.hidden = false;
    };
    canvas.onmouseleave = () => { tip.hidden = true; };
  }

  /* ---------- worst days table ---------- */
  function renderTable() {
    const top = [...data.daily].sort((a, b) => b.in_co2_max - a.in_co2_max).slice(0, 8);
    document.querySelector("#worst tbody").innerHTML = top.map((r) =>
      `<tr><td>${r.date}</td><td>${fmt(r.in_co2_max)}</td><td>${fmt(r.in_co2_mean)}</td><td>${fmt(r.in_temp_max, 1)}</td><td>${fmt(r.occupied_hours, 1)}</td></tr>`
    ).join("");
  }

  document.querySelectorAll(".toggle button").forEach((b) => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".toggle button").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      currentMetric = b.dataset.metric;
      renderHourly();
    });
  });

  function renderAll() { renderCards(); renderHourly(); renderDaily(); renderTable(); }
  window.addEventListener("resize", () => { renderHourly(); renderDaily(); });
  renderAll();
})();
