---
title: Oven → Air Fryer Converter
slug: air-fryer-converter
publish: true
date: 2026-05-11
description: Convert any oven recipe to air fryer time and temperature instantly.
tags:
  - tools
  - cooking
---

# Oven → Air Fryer Converter

Air fryers circulate hot air more efficiently than a conventional oven, so you can generally:

- **Reduce the temperature** by 25 °F (about 15 °C)
- **Reduce the cook time** by around 20 %

Use the tool below to convert any oven recipe.

```html embed
<div class="air-fryer-tool">
  <form id="af-form" onsubmit="return false;">
    <div class="af-row">
      <label for="af-temp">Oven temperature</label>
      <div class="af-input-group">
        <input type="number" id="af-temp" value="375" min="100" max="550" step="5">
        <select id="af-unit">
          <option value="F">°F</option>
          <option value="C">°C</option>
        </select>
      </div>
    </div>
    <div class="af-row">
      <label for="af-time">Oven cook time</label>
      <div class="af-input-group">
        <input type="number" id="af-time" value="30" min="1" max="360" step="1">
        <span class="af-unit-label">min</span>
      </div>
    </div>
    <button type="button" id="af-btn" onclick="afConvert()">Convert</button>
    <div id="af-result" hidden>
      <p><strong>Air fryer temperature:</strong> <span id="af-out-temp"></span></p>
      <p><strong>Air fryer cook time:</strong> <span id="af-out-time"></span></p>
      <p class="af-note">Check for doneness a few minutes early — air fryer models vary.</p>
    </div>
  </form>
</div>

<style>
.air-fryer-tool { margin: 1.5rem 0; padding: 1.25rem 1.5rem; border: 1px solid var(--border, #444); }
.af-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.75rem; }
.af-row label { flex: 0 0 auto; }
.af-input-group { display: flex; align-items: center; gap: 0.4rem; }
.af-input-group input { width: 5rem; padding: 0.3rem 0.5rem; font-family: inherit; font-size: 1rem; border: 1px solid var(--border, #444); background: var(--bg, #1a1a1a); color: inherit; }
.af-input-group select { padding: 0.3rem; border: 1px solid var(--border, #444); background: var(--bg, #1a1a1a); color: inherit; font-family: inherit; font-size: 1rem; }
.af-unit-label { font-size: 0.9rem; color: var(--muted, #888); }
#af-btn { margin-top: 0.5rem; padding: 0.45rem 1.25rem; background: var(--accent, #5e9e91); color: #0d0d0d; border: none; font-family: inherit; font-size: 1rem; font-weight: 700; cursor: pointer; letter-spacing: 0.05em; }
#af-btn:hover { filter: brightness(1.15); }
#af-result { margin-top: 1rem; padding: 0.85rem 1rem; border-left: 3px solid var(--accent, #5e9e91); }
#af-result p { margin: 0.25rem 0; }
.af-note { font-size: 0.85rem; color: var(--muted, #888); margin-top: 0.5rem !important; }
</style>

<script>
function afConvert() {
  var tempIn = parseFloat(document.getElementById('af-temp').value);
  var minutes = parseFloat(document.getElementById('af-time').value);
  var unit = document.getElementById('af-unit').value;

  if (isNaN(tempIn) || isNaN(minutes) || minutes <= 0) return;

  var afTempF, displayTemp;
  if (unit === 'F') {
    afTempF = tempIn - 25;
    // Round to nearest 5
    afTempF = Math.round(afTempF / 5) * 5;
    displayTemp = afTempF + ' °F';
  } else {
    var afTempC = tempIn - 15;
    afTempC = Math.round(afTempC / 5) * 5;
    displayTemp = afTempC + ' °C';
  }

  var afMinutes = Math.round(minutes * 0.8);

  document.getElementById('af-out-temp').textContent = displayTemp;
  document.getElementById('af-out-time').textContent = afMinutes + ' min';
  document.getElementById('af-result').removeAttribute('hidden');
}
</script>
```

## How it works

The conversion follows the standard rules of thumb:

| | Oven | Air fryer |
|---|---|---|
| Temperature | 375 °F | 350 °F |
| Time | 30 min | 24 min |

Always keep an eye on things the first time you try a recipe — air fryers vary, and thinner cuts cook faster than expected.
