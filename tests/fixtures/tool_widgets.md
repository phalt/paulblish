---
title: Tool widgets
slug: tool-widgets
publish: true
date: 2026-10-26
description: Every form control and widget the tools CSS supports, with the HTML to write for each.
tags:
  - paulblish
---
Everything below lives inside a ` ```html embed ` block. Plain form elements need no classes at all. Each widget needs one class at most. Pages with an embed also get a small helper script that keeps sliders, dials and live readouts in sync, so you don't have to.

All of these styles are zero-specificity, so any class or id in a tool's own `<style>` wins.

## Plain inputs

No classes: `label`, `input`, `select`, `textarea`, `button` and `output`. A `<small>` after an input is a hint.

```html embed title="Plain inputs"
<form id="w-plain" onsubmit="event.preventDefault()">
  <label for="w-name">Name</label>
  <input id="w-name" type="text" placeholder="Johnny Silverhand">
  <small>Hints go in a small tag.</small>

  <label for="w-district">District</label>
  <select id="w-district">
    <option>Watson</option>
    <option>Westbrook</option>
    <option>Pacifica</option>
  </select>

  <label for="w-notes">Notes</label>
  <textarea id="w-notes" rows="3"></textarea>

  <button type="submit">Submit</button>
  <button type="reset">Reset</button>

  <p>Result: <output>42</output></p>
</form>
```

```html
<label for="w-name">Name</label>
<input id="w-name" type="text" placeholder="Johnny Silverhand">
<small>Hints go in a small tag.</small>

<label for="w-district">District</label>
<select id="w-district">
  <option>Watson</option>
</select>

<button type="submit">Submit</button>

<p>Result: <output>42</output></p>
```

## Rows

`.row` puts its children side by side, e.g. a number with its unit.

```html embed title="Rows"
<label for="w-temp">Temperature</label>
<div class="row">
  <input id="w-temp" type="number" value="200">
  <select aria-label="Unit">
    <option>°C</option>
    <option>°F</option>
  </select>
</div>

<label for="w-time">Time</label>
<div class="row">
  <input id="w-time" type="number" value="30">
  <span>min</span>
</div>
```

```html
<label for="w-temp">Temperature</label>
<div class="row">
  <input id="w-temp" type="number" value="200">
  <select aria-label="Unit">
    <option>°C</option>
    <option>°F</option>
  </select>
</div>
```

## Field grid

`.fields` lines labels and controls up in two columns. On a phone it becomes one column.

```html embed title="Field grid"
<div class="fields">
  <label for="w-w">Width (mm)</label>
  <input id="w-w" type="number" value="210">
  <label for="w-h">Height (mm)</label>
  <input id="w-h" type="number" value="297">
  <label for="w-paper">Paper</label>
  <select id="w-paper"><option>Matte</option><option>Gloss</option></select>
</div>
```

```html
<div class="fields">
  <label for="w-w">Width (mm)</label>
  <input id="w-w" type="number" value="210">
  <label for="w-h">Height (mm)</label>
  <input id="w-h" type="number" value="297">
</div>
```

## Sliders

A bare range input. The helper fills the track up to the thumb. An `<output class="live" for="...">` shows the value as you drag.

```html embed title="Slider"
<label for="w-servings">Servings</label>
<input id="w-servings" type="range" min="1" max="12" value="4">
<p><output class="live" for="w-servings">4</output> servings</p>
```

```html
<label for="w-servings">Servings</label>
<input id="w-servings" type="range" min="1" max="12" value="4">
<p><output class="live" for="w-servings">4</output> servings</p>
```

## Toggles, checkboxes and radios

Put the input inside its label to get a single clickable row. `class="switch"` draws a checkbox as a toggle.

```html embed title="Toggles"
<label><input type="checkbox" class="switch" checked> Night mode</label>
<label><input type="checkbox"> Remember me</label>
<label><input type="radio" name="w-size" checked> Small</label>
<label><input type="radio" name="w-size"> Large</label>
```

```html
<label><input type="checkbox" class="switch" checked> Night mode</label>
<label><input type="checkbox"> Remember me</label>
<label><input type="radio" name="w-size" checked> Small</label>
```

## Segmented control

`class="segmented"` on a fieldset of radio labels draws a button bar. Read the value like any radio group.

```html embed title="Segmented control"
<fieldset class="segmented">
  <legend>Roast</legend>
  <label><input type="radio" name="w-roast" value="light"> Light</label>
  <label><input type="radio" name="w-roast" value="medium" checked> Medium</label>
  <label><input type="radio" name="w-roast" value="dark"> Dark</label>
</fieldset>
```

```html
<fieldset class="segmented">
  <legend>Roast</legend>
  <label><input type="radio" name="w-roast" value="light"> Light</label>
  <label><input type="radio" name="w-roast" value="medium" checked> Medium</label>
  <label><input type="radio" name="w-roast" value="dark"> Dark</label>
</fieldset>
```

## Knob

`class="knob"` on a range input draws a dial. Drag it round, or focus it and use the arrow keys. It's still a range input, so read `.value` and listen for `input` as usual.

```html embed title="Knob"
<label for="w-volume">Volume</label>
<input id="w-volume" type="range" class="knob" min="0" max="11" value="7">
<p>Turned up to <output class="live" for="w-volume">7</output></p>
```

```html
<label for="w-volume">Volume</label>
<input id="w-volume" type="range" class="knob" min="0" max="11" value="7">
<p>Turned up to <output class="live" for="w-volume">7</output></p>
```

## Meters and progress bars

No classes. On a `<meter>`, `low`, `high` and `optimum` pick the colour: teal for good, amber for borderline, red for bad. Always write the number next to it as well.

```html embed title="Meters"
<label for="w-good">Battery: 85%</label>
<meter id="w-good" min="0" max="100" low="20" high="50" optimum="100" value="85">85%</meter>
<label for="w-ok">Battery: 35%</label>
<meter id="w-ok" min="0" max="100" low="20" high="50" optimum="100" value="35">35%</meter>
<label for="w-bad">Battery: 10%</label>
<meter id="w-bad" min="0" max="100" low="20" high="50" optimum="100" value="10">10%</meter>
<label for="w-progress">Download: 60%</label>
<progress id="w-progress" max="100" value="60">60%</progress>
```

```html
<label for="w-good">Battery: 85%</label>
<meter id="w-good" min="0" max="100" low="20" high="50" optimum="100" value="85">85%</meter>

<label for="w-progress">Download: 60%</label>
<progress id="w-progress" max="100" value="60">60%</progress>
```

## Gauge

`class="gauge"` draws a read-only dial. `--value` (0 to 100) sets how full it is, and the text inside is what gets printed. Your script sets both. Here a slider drives it:

```html embed title="Gauge"
<label for="w-gauge-in">Signal</label>
<input id="w-gauge-in" type="range" min="0" max="100" value="72">
<div class="gauge" id="w-gauge" style="--value: 72">72%</div>

<script>
document.getElementById("w-gauge-in").addEventListener("input", (event) => {
  const gauge = document.getElementById("w-gauge");
  gauge.style.setProperty("--value", event.target.value);
  gauge.textContent = `${event.target.value}%`;
});
</script>
```

```html
<div class="gauge" id="w-gauge" style="--value: 72">72%</div>

<script>
const gauge = document.getElementById("w-gauge");
gauge.style.setProperty("--value", 40);
gauge.textContent = "40%";
</script>
```

## Bar chart

`class="bars"` on a `<dl>`. Each `<dt>` is a label. Each `<dd>` gets `--value` (0 to 100) for the bar length, and its text is printed at the end of the bar.

```html embed title="Bar chart"
<dl class="bars">
  <dt>Mon</dt><dd style="--value: 40">4 km</dd>
  <dt>Tue</dt><dd style="--value: 100">10 km</dd>
  <dt>Wed</dt><dd style="--value: 0">rest</dd>
  <dt>Thu</dt><dd style="--value: 65">6.5 km</dd>
</dl>
```

```html
<dl class="bars">
  <dt>Mon</dt><dd style="--value: 40">4 km</dd>
  <dt>Tue</dt><dd style="--value: 100">10 km</dd>
</dl>
```

## Stats

`class="stats"` lays out a row of figures. Each child holds a `<strong>` (or `<output>`) value and a caption.

```html embed title="Stats"
<div class="stats">
  <div><strong>1,284</strong> words</div>
  <div><strong>6 min</strong> reading time</div>
  <div><strong>99.9%</strong> uptime</div>
</div>
```

```html
<div class="stats">
  <div><strong>1,284</strong> words</div>
  <div><strong>6 min</strong> reading time</div>
</div>
```

## Panel

`class="panel"` boxes a result off from the inputs.

```html embed title="Panel"
<div class="panel">
  <p>Cook at <output>175 °C</output> for <output>24 min</output>.</p>
  <small>Check it a few minutes early.</small>
</div>
```

```html
<div class="panel">
  <p>Cook at <output>175 °C</output> for <output>24 min</output>.</p>
  <small>Check it a few minutes early.</small>
</div>
```

## Errors and disabled controls

Inputs go red once someone types an invalid value (`required`, `min`, `max`, `pattern`), and so does a `<small>` hint straight after them. Use `class="error"` for messages your script writes. Disabled controls fade out.

```html embed title="Errors"
<label for="w-age">Age</label>
<input id="w-age" type="number" min="0" max="120" value="150" required>
<small>Between 0 and 120.</small>
<p class="error">Something went wrong.</p>
<button type="button" disabled>Disabled</button>
<label><input type="checkbox" class="switch" disabled> Disabled switch</label>
```

```html
<input id="w-age" type="number" min="0" max="120" required>
<small>Between 0 and 120.</small>

<p class="error">Something went wrong.</p>

<button type="button" disabled>Disabled</button>
```

## All together

A coffee brew ratio tool that uses a slider, a segmented control, stats and a gauge.

```html embed title="Brew ratio"
<form id="w-brew">
  <label for="w-beans">Coffee (g)</label>
  <input id="w-beans" type="range" min="10" max="40" value="18">
  <p><output class="live" for="w-beans">18</output> g</p>

  <fieldset class="segmented">
    <legend>Ratio</legend>
    <label><input type="radio" name="ratio" value="15"> 1:15</label>
    <label><input type="radio" name="ratio" value="16" checked> 1:16</label>
    <label><input type="radio" name="ratio" value="17"> 1:17</label>
  </fieldset>

  <div class="stats">
    <div><output id="w-water">288 g</output> water</div>
    <div><output id="w-cups">1.2</output> cups</div>
  </div>

  <div class="gauge" id="w-strength" style="--value: 50">Medium</div>
</form>

<script>
(() => {
  const form = document.getElementById("w-brew");
  function update() {
    const beans = Number(form.elements["w-beans"].value);
    const ratio = Number(form.elements.ratio.value);
    const water = beans * ratio;
    document.getElementById("w-water").value = `${water} g`;
    document.getElementById("w-cups").value = (water / 240).toFixed(1);
    const strength = document.getElementById("w-strength");
    strength.style.setProperty("--value", (17 - ratio) * 50);
    strength.textContent = { 15: "Strong", 16: "Medium", 17: "Light" }[ratio];
  }
  form.addEventListener("input", update);
  update();
})();
</script>
```
