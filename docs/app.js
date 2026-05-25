"use strict";

const RATINGS = [
  { key: "safeD", label: "Safe Dem", color: "#2166ac" },
  { key: "leanD", label: "Lean Dem", color: "#7fabd6" },
  { key: "toss", label: "Toss-up", color: "#ece7a8" },
  { key: "leanR", label: "Lean Rep", color: "#e8907c" },
  { key: "safeR", label: "Safe Rep", color: "#b2182b" },
];
const COLOR = Object.fromEntries(RATINGS.map((r) => [r.key, r.color]));
const LABEL = Object.fromEntries(RATINGS.map((r) => [r.key, r.label]));

const state = {
  manifest: null,
  states: null,
  scenarios: [],
  scenarioCache: new Map(),
  current: null,
  model: "blend",
  index: 0,
  lineMode: "real",
  currentIsReal: false,
};

const fmt = (n) => n.toLocaleString("en-US");
const pct = (x) => (x * 100).toFixed(1) + "%";

// --- partisan model math -------------------------------------------------
function cyclesFor(model) {
  return model === "blend" ? ["PRES16", "PRES20", "PRES24"] : [model];
}
function districtDR(props, model) {
  let d = 0, r = 0;
  for (const c of cyclesFor(model)) {
    d += props[c + "_D"] || 0;
    r += props[c + "_R"] || 0;
  }
  return [d, r];
}
function demShare(props, model) {
  const [d, r] = districtDR(props, model);
  return d + r > 0 ? d / (d + r) : 0.5;
}
function ratingOf(s) {
  if (s >= 0.575) return "safeD";
  if (s >= 0.525) return "leanD";
  if (s > 0.475) return "toss";
  if (s > 0.425) return "leanR";
  return "safeR";
}

// --- map rendering -------------------------------------------------------
const svg = d3.select("#map");
const projection = d3.geoAlbersUsa();
const path = d3.geoPath(projection);
const MIN_ZOOM = 1, MAX_ZOOM = 40;
let gZoom, gStates, gDistricts, zoom;

function sizeMap() {
  const wrap = document.querySelector(".map-wrap");
  const w = wrap.clientWidth, h = wrap.clientHeight;
  svg.attr("viewBox", `0 0 ${w} ${h}`).attr("width", w).attr("height", h);
  if (state.states) projection.fitExtent([[8, 8], [w - 8, h - 8]], state.states);
  if (zoom) zoom.extent([[0, 0], [w, h]]).translateExtent([[0, 0], [w, h]]);
}

function setupLayers() {
  gZoom = svg.append("g").attr("class", "zoom-layer");
  gStates = gZoom.append("g");
  gDistricts = gZoom.append("g");
  zoom = d3.zoom()
    .scaleExtent([MIN_ZOOM, MAX_ZOOM])
    .on("zoom", (event) => {
      gZoom.attr("transform", event.transform);
      document.querySelector(".map-wrap").classList.toggle("zoomed", event.transform.k > 1.01);
    });
  svg.call(zoom);
}

function resetZoom() {
  svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
}

function renderStates() {
  gStates.selectAll("path")
    .data(state.states.features)
    .join("path")
    .attr("class", "state-outline")
    .attr("d", path);
}

function renderDistricts() {
  if (!state.current) return;
  gDistricts.selectAll("path")
    .data(state.current.features, (d) => d.properties.id)
    .join("path")
    .attr("class", "district")
    .attr("d", path)
    .attr("fill", (d) => COLOR[ratingOf(demShare(d.properties, state.model))])
    .on("mousemove", showTooltip)
    .on("mouseleave", hideTooltip);
}

// --- tooltip -------------------------------------------------------------
const tooltip = document.getElementById("tooltip");
function showTooltip(event, d) {
  const s = demShare(d.properties, state.model);
  const r = ratingOf(s);
  const dem = s >= 0.5;
  tooltip.hidden = false;
  tooltip.innerHTML =
    `<b>${d.properties.id}</b><br>` +
    `<span class="swatch" style="background:${COLOR[r]}"></span>${LABEL[r]}<br>` +
    `Two-party Dem: ${pct(s)} (${dem ? "D" : "R"}+${(Math.abs(s - 0.5) * 200).toFixed(1)})<br>` +
    `Population: ${fmt(d.properties.pop)}`;
  const wrap = document.querySelector(".map-wrap").getBoundingClientRect();
  let x = event.clientX - wrap.left + 14, y = event.clientY - wrap.top + 14;
  if (x + 240 > wrap.width) x -= 254;
  tooltip.style.left = x + "px";
  tooltip.style.top = y + "px";
}
function hideTooltip() { tooltip.hidden = true; }

// --- summary + metrics ---------------------------------------------------
function computeMetrics(feats, model) {
  const counts = { safeD: 0, leanD: 0, toss: 0, leanR: 0, safeR: 0 };
  let demSeats = 0, repSeats = 0;
  let totD = 0, totR = 0;
  let wastedD = 0, wastedR = 0, totalVotes = 0;

  for (const f of feats) {
    const [d, r] = districtDR(f.properties, model);
    const s = d + r > 0 ? d / (d + r) : 0.5;
    counts[ratingOf(s)]++;
    if (s >= 0.5) demSeats++; else repSeats++;
    totD += d; totR += r;
    const tot = d + r; totalVotes += tot;
    if (d >= r) { wastedD += d - tot / 2; wastedR += r; }
    else { wastedR += r - tot / 2; wastedD += d; }
  }
  const total = feats.length;
  const V = totD + totR > 0 ? totD / (totD + totR) : 0.5;
  const propDem = V * total;
  const gapSeats = demSeats - propDem;
  const eg = totalVotes > 0 ? (wastedD - wastedR) / totalVotes : 0; // >0 favors R
  return { total, counts, demSeats, repSeats, V, seatShare: demSeats / total,
           propDem, gapSeats, eg, toss: counts.toss };
}

function updateSummary() {
  const m = computeMetrics(state.current.features, state.model);
  const { total, counts, demSeats, repSeats, V, seatShare, propDem, gapSeats, eg } = m;

  // seat bar + ratings table
  const bar = document.getElementById("seatbar");
  bar.innerHTML = RATINGS.map((rt) =>
    `<div style="background:${rt.color};width:${(counts[rt.key] / total) * 100}%"></div>`).join("");
  document.getElementById("ratingsTable").innerHTML = RATINGS.map((rt) =>
    `<tr><td><span class="sw" style="background:${rt.color}"></span>${rt.label}</td>` +
    `<td class="num">${counts[rt.key]}</td></tr>`).join("");

  document.getElementById("demSeats").textContent = demSeats;
  document.getElementById("repSeats").textContent = repSeats;
  document.getElementById("tossSeats").textContent = counts.toss;
  document.getElementById("natVote").textContent = pct(V);
  document.getElementById("seatShare").textContent = pct(seatShare);

  const gapParty = gapSeats >= 0 ? "D" : "R";
  document.getElementById("propGap").textContent =
    `${gapSeats >= 0 ? "+" : ""}${gapSeats.toFixed(0)} ${gapParty} (${Math.abs(gapSeats).toFixed(0)} seats)`;
  document.getElementById("propGapShare").textContent =
    `${pct(Math.abs(gapSeats) / total)} of the House`;
  document.getElementById("effGap").textContent =
    `${pct(Math.abs(eg))} (favors ${eg > 0 ? "R" : "D"})`;
  document.getElementById("distortionNote").textContent =
    `If seats matched the statewide-summed two-party vote exactly, Democrats would hold ~${propDem.toFixed(0)} of ${total}. ` +
    `The map gives them ${demSeats}. ` +
    (state.currentIsReal
      ? "These are the actual current districts, so this gap reflects today's real map (areal vote approximations aside)."
      : "Smaller districts tend to shrink this gap.");
}

// --- scenario loading ----------------------------------------------------
function realMapFor(size) {
  const rm = state.manifest.realMap;
  return rm && rm.size === size ? rm : null;
}

function updateLineModeControl(rm, useReal) {
  const ctrl = document.getElementById("lineModeControl");
  if (!ctrl) return;
  ctrl.hidden = !rm;
  if (!rm) return;
  document.getElementById("lineMode").value = state.lineMode;
  document.getElementById("lineModeHint").textContent = useReal
    ? rm.note
    : "Partisan-blind splitline redraw at the same seat count, for an apples-to-apples comparison.";
}

async function loadScenario(idx) {
  state.index = idx;
  const sc = state.scenarios[idx];
  document.getElementById("houseSize").textContent = fmt(sc.size);
  document.getElementById("perRep").textContent = fmt(sc.peoplePerRep);

  const rm = realMapFor(sc.size);
  const useReal = !!rm && state.lineMode === "real";
  state.currentIsReal = useReal;
  updateLineModeControl(rm, useReal);

  const file = useReal ? rm.file : sc.file;
  if (!state.scenarioCache.has(file)) {
    gDistricts.selectAll("path").remove();
    const fc = await fetch("data/" + file).then((r) => r.json());
    state.scenarioCache.set(file, fc);
  }
  state.current = state.scenarioCache.get(file);
  renderDistricts();
  updateSummary();
}

// --- lessons / seat-dilution ---------------------------------------------
async function ensureAllScenarios() {
  const files = state.scenarios.map((s) => s.file);
  const rm = state.manifest.realMap;
  if (rm) files.push(rm.file);
  await Promise.all(files.map(async (f) => {
    if (state.scenarioCache.has(f)) return;
    try {
      const fc = await fetch("data/" + f).then((r) => r.json());
      state.scenarioCache.set(f, fc);
    } catch (e) { /* real map is absent until the build Action runs */ }
  }));
}

function scenarioSeries(model) {
  return state.scenarios.map((sc) => {
    const fc = state.scenarioCache.get(sc.file);
    return { size: sc.size, ...computeMetrics(fc.features, model) };
  });
}

function realBaseline(model) {
  const rm = state.manifest.realMap;
  const fc = rm && state.scenarioCache.get(rm.file);
  return fc ? { rm, m: computeMetrics(fc.features, model) } : null;
}

function drawLineChart(mountId, opts) {
  const mount = document.getElementById(mountId);
  if (!mount) return;
  mount.innerHTML = "";
  const W = 720, H = 280, pad = { t: 18, r: 18, b: 38, l: 56 };
  const svg = d3.select(mount).append("svg")
    .attr("viewBox", `0 0 ${W} ${H}`).attr("class", "chart");
  const x = d3.scaleLinear().domain(opts.xDomain).range([pad.l, W - pad.r]);
  const y = d3.scaleLinear().domain(opts.yDomain).nice().range([H - pad.b, pad.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - pad.b})`)
    .call(d3.axisBottom(x).tickValues(opts.xTicks).tickFormat(d3.format("d")));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${pad.l},0)`)
    .call(d3.axisLeft(y).ticks(5).tickFormat(opts.yFmt || ((d) => d)));
  svg.append("text").attr("class", "axis-label").attr("x", pad.l - 8).attr("y", pad.t - 6)
    .text(opts.yLabel);
  const line = d3.line().x((d) => x(d.x)).y((d) => y(d.y));
  for (const s of opts.series) {
    svg.append("path").datum(s.points).attr("fill", "none")
      .attr("stroke", s.color).attr("stroke-width", 2.2).attr("d", line);
    svg.append("g").selectAll("circle").data(s.points).join("circle")
      .attr("cx", (d) => x(d.x)).attr("cy", (d) => y(d.y)).attr("r", 3.2).attr("fill", s.color);
  }
}

function renderLessons() {
  const host = document.getElementById("lessons");
  ensureAllScenarios().then(() => {
    const model = state.model;
    const modelLabel =
      document.querySelector(`#modelSelect option[value="${model}"]`)?.textContent.trim() || model;
    const series = scenarioSeries(model);
    const sizes = series.map((s) => s.size);
    const minN = sizes[0], maxN = sizes[sizes.length - 1];
    const pct1 = (x) => x.toFixed(1) + "%";
    const pct2 = (x) => x.toFixed(2) + "%";
    const pct3 = (x) => x.toFixed(3) + "%";

    const real = realBaseline(model);
    const edge = Math.max(1, Math.round(real ? Math.abs(real.m.gapSeats) : Math.abs(series[0].gapSeats)));
    const edgeDesc = real ? `the edge in today's real map (${edge} seats)` : `a ${edge}-seat edge`;
    const shareAt = (n) => (edge / n) * 100;
    const needToHold = Math.round(edge * (maxN / minN));

    const distShare = series.map((s) => Math.abs(s.gapSeats) / s.total * 100);
    const egMag = series.map((s) => Math.abs(s.eg) * 100);
    const distMin = Math.min(...distShare), distMax = Math.max(...distShare);

    const realLineHint = real
      ? `On the <b>Map</b> tab, switch &ldquo;District lines&rdquo; to <b>Real current districts</b> at 435 to see today's actual gerrymander (Democrats hold ${real.m.demSeats} seats vs. a proportional ${real.m.propDem.toFixed(0)}), then flip to the neutral redraw at the same 435 seats to isolate it.`
      : `The real-current-districts baseline (119th Congress) lights up on the <b>Map</b> tab once the data build Action has run; it lets you compare today's actual map against a neutral redraw at the same 435 seats.`;

    host.innerHTML = `
      <h1>What expansion does to gerrymandering</h1>
      <p><b>The unit of manipulation is the district.</b> A gerrymander works by
      <i>packing</i> the other side's voters into a few throwaway districts and <i>cracking</i>
      the rest thinly across districts your side narrowly wins. The bigger each district is, the
      more voters a mapmaker can move per seat &mdash; so in a 435-seat House (about 760,000 people
      a district) one well-placed boundary swings a large share of the whole chamber. Shrink the
      districts and two things change at once.</p>

      <h2>1. Every seat is worth less</h2>
      <p>A seat's a-priori voting power is simply its share of the floor: one vote out of
      <code>N</code>. For equal-weight seats the Banzhaf and Shapley&ndash;Shubik power indices
      both reduce to exactly <code>1/N</code>. Expansion therefore <b>mechanically dilutes</b>
      every seat, gerrymandered or not:</p>
      <div id="chartPower"></div>
      <p class="chart-cap">Per-seat power falls from <b>${pct3(100 / 435)}</b> at 435 seats to
      <b>${pct3(100 / 870)}</b> at 870 and <b>${pct3(100 / 1500)}</b> at 1,500. Double the House,
      halve each member's power.</p>

      <h2>2. The same gerrymander buys a smaller slice</h2>
      <p>A gerrymander is counted in <i>seats</i>, but power is a <i>share of the chamber</i>.
      Holding the seat edge fixed, that share shrinks as the House grows. Take ${edgeDesc}: it is
      <b>${pct1(shareAt(minN))}</b> of a ${fmt(minN)}-seat House, but only
      <b>${pct1(shareAt(870))}</b> at 870 and <b>${pct1(shareAt(maxN))}</b> at ${fmt(maxN)}.</p>
      <div class="callout">
        <div class="dilbar"><span class="lbl">${fmt(minN)} seats</span>
          <span class="track"><span class="fill" style="width:${Math.min(100, shareAt(minN) / shareAt(minN) * 100)}%"></span></span>
          <b>${pct1(shareAt(minN))}</b></div>
        <div class="dilbar"><span class="lbl">870 seats</span>
          <span class="track"><span class="fill" style="width:${shareAt(870) / shareAt(minN) * 100}%"></span></span>
          <b>${pct1(shareAt(870))}</b></div>
        <div class="dilbar"><span class="lbl">${fmt(maxN)} seats</span>
          <span class="track"><span class="fill" style="width:${shareAt(maxN) / shareAt(minN) * 100}%"></span></span>
          <b>${pct1(shareAt(maxN))}</b></div>
        <p class="hint">Same ${edge}-seat edge, shrinking grip on power. To hold the
        ${fmt(minN)}-seat level of control in a ${fmt(maxN)}-seat House, a gerrymander would have to
        flip about <b>${fmt(needToHold)}</b> seats &mdash; far more manipulation for the same payoff,
        and far harder when each district is small.</p>
      </div>

      <h2>What this particular simulation shows</h2>
      <p>The maps in this tool are drawn <b>partisan-blind</b> &mdash; the algorithm never looks at
      votes. So the distortion below isn't intentional gerrymandering; it's the residue of political
      <i>geography</i> (Democratic voters packed into cities by where they live). Under the
      <b>${modelLabel}</b> model it stays modest &mdash; between <b>${pct1(distMin)}</b> and
      <b>${pct1(distMax)}</b> of the chamber across every House size &mdash; and it does
      <b>not</b> grow as the House expands. That's the quiet finding: when a map isn't
      gerrymandered, chamber size barely changes how fair the result is.</p>
      <div class="chart-legend">
        <span><span class="k" style="background:#b2182b"></span>Seats vs. proportional (% of chamber)</span>
        <span><span class="k" style="background:#2166ac"></span>Efficiency gap (%)</span>
      </div>
      <div id="chartDistort"></div>
      <p class="chart-cap">${realLineHint}</p>

      <h2>The takeaway</h2>
      <p>Expanding the House doesn't make a neutral map dramatically fairer &mdash; a neutral map is
      already roughly proportional at any size. What expansion does is strip <i>leverage</i> from a
      <i>deliberate</i> gerrymander: smaller districts are harder to pack and crack safely, and even
      a successful gerrymander controls a smaller share of a larger chamber. The bigger the House,
      the less a rigged map is worth.</p>
      <p class="hint">Caveats: votes are apportioned at county resolution, so single-district figures
      are approximate; the per-seat-power argument is exact, while the &ldquo;same edge, smaller
      slice&rdquo; figure holds the seat edge fixed for illustration. Numbers above follow the
      partisan model selected on the Map tab.</p>`;

    drawLineChart("chartPower", {
      xDomain: [minN, maxN], xTicks: sizes,
      yDomain: [0, 100 / minN * 1.05],
      yLabel: "% of chamber per seat", yFmt: (d) => d.toFixed(2) + "%",
      series: [{ color: "#1a1d23", points: sizes.map((n) => ({ x: n, y: 100 / n })) }],
    });
    drawLineChart("chartDistort", {
      xDomain: [minN, maxN], xTicks: sizes,
      yDomain: [0, Math.max(distMax, ...egMag) * 1.15 || 1],
      yLabel: "% (distortion)", yFmt: (d) => d.toFixed(1) + "%",
      series: [
        { color: "#b2182b", points: series.map((s, i) => ({ x: s.size, y: distShare[i] })) },
        { color: "#2166ac", points: series.map((s, i) => ({ x: s.size, y: egMag[i] })) },
      ],
    });
  });
}

// --- methodology ---------------------------------------------------------
function renderMethodology() {
  const m = state.manifest;
  const cites = m.citations.map((c) =>
    `<li><a href="${c.url}" target="_blank" rel="noopener">${c.name}</a> &mdash; ${c.source}</li>`).join("");
  document.getElementById("methodology").innerHTML = `
    <h1>How this works</h1>
    <p>This tool answers a hypothetical: if the US House of Representatives were larger,
    what would the districts look like, and how would the partisan balance change? The premise
    is that smaller districts are harder to gerrymander safely, so distortions between votes and
    seats should shrink as the House grows.</p>

    <h2>1. Apportionment</h2>
    <p>For a chosen House size <code>N</code>, seats are divided among the 50 states with the
    <b>Huntington&ndash;Hill method</b> &mdash; the exact method Congress uses. Every state gets at
    least one seat; the rest are handed out by priority value
    <code>pop / &radic;(n(n+1))</code>. At <code>N = 435</code> this reproduces the real
    2020 apportionment exactly (verified in the test suite).</p>

    <h2>2. Drawing districts</h2>
    <p>Within each state we draw equal-population, compact districts with a
    <b>shortest-splitline variant</b>: the set of population units is recursively bisected along its
    principal axis at the point that balances population, so each cut is short and districts stay
    compact. The algorithm never looks at vote data, so the maps are partisan-blind by construction.</p>
    <p><b>Resolution &amp; honesty:</b> in this build the population units are <b>counties</b>
    (geometry, population, votes joined on FIPS). Counties larger than a district are split into
    equal-area pieces assuming uniform density inside the county. This is an approximation: districts
    land within a few percent of equal population, and boundaries follow county-piece edges rather than
    real precinct lines. The pipeline is built to swap in Census tracts / VEST precincts for full
    fidelity (run via GitHub Action where those hosts are reachable).</p>
    <p><b>Real current districts:</b> at the 435-seat stop you can switch the map from the neutral
    redraw to the <b>actual 119th-Congress districts</b> (Census TIGER) &mdash; the real,
    gerrymandered map. County votes are apportioned onto each district by area, so its per-district
    lean is an estimate. Comparing it against the neutral 435-seat redraw isolates how much of
    today's distortion is the map rather than the geography; the <b>Lessons</b> tab works through
    what that implies as the House grows.</p>

    <h2>3. Partisan lean</h2>
    <p>Each redrawn district sums the presidential votes of the units inside it. The
    <b>multi-cycle blend</b> pools two-party votes from 2016&nbsp;+&nbsp;2020&nbsp;+&nbsp;2024; the other
    options use a single cycle. Two-party Democratic share <code>S</code> maps to a rating:</p>
    <table>
      <tr><th>Rating</th><th>Two-party Dem share</th></tr>
      <tr><td>Safe Dem</td><td>S &ge; 57.5%</td></tr>
      <tr><td>Lean Dem</td><td>52.5% &ndash; 57.5%</td></tr>
      <tr><td>Toss-up</td><td>47.5% &ndash; 52.5%</td></tr>
      <tr><td>Lean Rep</td><td>42.5% &ndash; 47.5%</td></tr>
      <tr><td>Safe Rep</td><td>S &le; 42.5%</td></tr>
    </table>

    <h2>4. Distortion metrics</h2>
    <p><b>Seats vs. proportional</b>: compares predicted Democratic seats to the national two-party
    Democratic vote share times the number of seats &mdash; the perfectly-proportional benchmark.
    <b>Efficiency gap</b>: the difference in "wasted" votes (votes for a loser, plus a winner's votes
    beyond 50%) between the parties, divided by all votes. A larger gap means more distortion.</p>

    <h2>Sources</h2>
    <ul>${cites}</ul>
    <p class="hint">All per-district numbers behind these charts are in the downloadable scenario files
    under <code>docs/data/</code>, so every figure can be re-derived independently.</p>`;
}

// --- UI wiring -----------------------------------------------------------
function setupTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
      if (btn.dataset.tab === "map") { sizeMap(); renderStates(); renderDistricts(); }
      if (btn.dataset.tab === "lessons") renderLessons();
    });
  });
}

function setupControls() {
  const slider = document.getElementById("sizeSlider");
  slider.max = state.scenarios.length - 1;
  slider.value = state.scenarios.findIndex((s) => s.size === state.manifest.currentHouseSize);
  if (slider.value < 0) slider.value = 0;
  slider.addEventListener("input", (e) => loadScenario(+e.target.value));
  document.getElementById("sliderTicks").innerHTML =
    state.scenarios.map((s) => `<span>${s.size}</span>`).join("");

  document.getElementById("modelSelect").addEventListener("change", (e) => {
    state.model = e.target.value;
    renderDistricts();
    updateSummary();
  });

  const lineMode = document.getElementById("lineMode");
  if (lineMode) {
    lineMode.addEventListener("change", (e) => {
      state.lineMode = e.target.value;
      loadScenario(state.index);
    });
  }

  document.getElementById("legend").innerHTML =
    RATINGS.map((r) => `<div class="row"><span class="sw" style="background:${r.color}"></span>${r.label}</div>`).join("");

  const zoomBy = (k) => svg.transition().duration(250).call(zoom.scaleBy, k);
  document.getElementById("zoomIn").addEventListener("click", () => zoomBy(1.6));
  document.getElementById("zoomOut").addEventListener("click", () => zoomBy(1 / 1.6));
  document.getElementById("zoomReset").addEventListener("click", resetZoom);
}

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    sizeMap(); renderStates(); renderDistricts();
    svg.call(zoom.transform, d3.zoomIdentity);
  }, 150);
});

// --- boot ----------------------------------------------------------------
async function main() {
  state.manifest = await fetch("data/manifest.json").then((r) => r.json());
  state.scenarios = state.manifest.scenarios.slice().sort((a, b) => a.size - b.size);
  state.states = await fetch("data/states.geojson").then((r) => r.json());

  document.getElementById("footerMeta").textContent =
    `${fmt(state.manifest.totalApportionmentPop)} people (2020 apportionment) · county-resolution build · partisan-blind districting`;

  setupLayers();
  sizeMap();
  renderStates();
  setupTabs();
  setupControls();
  renderMethodology();
  await loadScenario(+document.getElementById("sizeSlider").value);
}

main();
