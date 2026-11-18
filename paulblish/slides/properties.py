"""Port of Advanced Slides' element properties, attribute transformers and comment parser.

Source: ``src/transformers/*.ts`` and ``src/comment.ts`` in MSzturc/obsidian-advanced-slides (MIT).
Each transformer reads a shorthand attribute (``bg``, ``pad``, ``drag``/``drop``, ...) and turns it
into classes, inline styles or reveal.js ``data-*`` attributes.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING

from paulblish.slides.jsre import JSRegExp

if TYPE_CHECKING:
    from paulblish.slides.preprocessor import Context


def _js_number(value: str) -> float:
    """JavaScript ``Number(value)``: blank is 0, anything unparsable is NaN."""
    text = value.strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return math.nan


def _js_str(value: float | None) -> str:
    """Format a number the way JavaScript's string conversion does."""
    if value is None:
        return "undefined"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value.is_integer() and abs(value) < 1e21:
            return str(int(value))
        return repr(value)
    return str(value)


class Properties:
    def __init__(self, attributes: dict[str, str], ctx: Context) -> None:
        self.ctx = ctx
        self.style: dict[str, str] = {}
        self.classes: dict[str, None] = {}
        self.attributes = attributes
        _transform(self)

    def add_class(self, name: str) -> Properties:
        self.classes[name] = None
        return self

    def delete_class(self, name: str) -> Properties:
        self.classes.pop(name, None)
        return self

    def has_class(self, name: str) -> bool:
        return name in self.classes

    def add_style(self, key: str, value: str) -> Properties:
        self.style[key] = value
        return self

    def delete_style(self, key: str) -> Properties:
        self.style.pop(key, None)
        return self

    def has_style(self, name: str) -> bool:
        return name in self.style

    def add_attribute(self, key: str, value: str, update: bool = True) -> Properties:
        self.attributes[key] = value
        if update:
            _transform(self)
        return self

    def delete_attribute(self, key: str) -> Properties:
        self.attributes.pop(key, None)
        return self

    def has_attribute(self, name: str) -> bool:
        return name in self.attributes

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def get_classes(self) -> str:
        return " ".join(self.classes)

    def get_styles(self) -> str:
        return "; ".join(f"{key}: {value}" for key, value in self.style.items())

    def get_attributes(self) -> str:
        return " ".join(f'{key}="{value}"' for key, value in self.attributes.items() if key != "onTarget")


# --- Transformers -------------------------------------------------------------------------------


def _class_transformer(el: Properties) -> None:
    clazz = el.get_attribute("class")
    if clazz is not None:
        for value in clazz.split(" "):
            el.add_class(value.strip())
        el.delete_attribute("class")


def _style_transformer(el: Properties) -> None:
    style = el.get_attribute("style")
    if style is not None:
        for item in (v.strip() for v in style.split(";")):
            if item and ":" in item:
                # JS destructuring `[key, value] = item.split(':')` keeps only the first two parts
                parts = item.split(":")
                key, value = parts[0], parts[1]
                if key and value:
                    el.add_style(key.strip(), value.strip())
        el.delete_attribute("style")


def _background_transformer(el: Properties) -> None:
    bg = el.get_attribute("bg")
    target = el.get_attribute("onTarget")
    if bg is None:
        return
    rgb = parse_color(bg)
    if rgb is not None:
        if is_light(rgb):
            el.add_class("has-light-background")
            el.delete_class("has-dark-background")
        else:
            el.add_class("has-dark-background")
            el.delete_class("has-light-background")
        el.delete_attribute("bg")
        if target == "slide":
            el.delete_attribute("data-background-image")
            el.delete_attribute("data-background-color")
            el.add_attribute("data-background-color", bg)
        else:
            el.add_style("background-color", bg)
    else:
        el.delete_attribute("bg")
        if target == "slide":
            el.delete_attribute("data-background-color")
            el.delete_attribute("data-background-image")
            el.add_attribute("data-background-image", bg)


def _padding_transformer(el: Properties) -> None:
    value = el.get_attribute("pad")
    if value is not None:
        el.add_style("padding", value)
        el.add_style("box-sizing", "border-box")
        el.delete_attribute("pad")


def _animate_transformer(el: Properties) -> None:
    value = el.get_attribute("animate")
    if value is not None:
        for item in value.split(" "):
            if item.strip():
                el.add_class(item.strip())
        el.delete_attribute("animate")


def _fragment_transformer(el: Properties) -> None:
    value = el.get_attribute("frag")
    if value is not None:
        el.add_class("fragment")
        el.delete_attribute("frag")
        el.add_attribute("data-fragment-index", value)


def _style_mapping(source: str, target: str):
    def _transform(el: Properties) -> None:
        value = el.get_attribute(source)
        if value is not None:
            el.add_style(target, value)
            el.delete_attribute(source)

    return _transform


def _border_transformer(el: Properties) -> None:
    value = el.get_attribute("border")
    if value is not None:
        el.add_style("border", value)
        el.add_style("box-sizing", "border-box")
        el.delete_attribute("border")


def _rotate_transformer(el: Properties) -> None:
    value = el.get_attribute("rotate")
    if value is not None:
        rotate = value if value.endswith("deg") else value + "deg"
        el.add_style("transform", f"rotate({rotate})")
        el.delete_attribute("rotate")


def _background_image_transformer(el: Properties) -> None:
    # Upstream this hook collects images for HTML export; here it rewrites vault paths to
    # deployed asset URLs (and records them so they get copied).
    value = el.get_attribute("data-background-image")
    if value is not None:
        resolved = el.ctx.asset_url(value)
        if resolved is not None and resolved != value:
            el.attributes["data-background-image"] = resolved


_GRID_ATTRIBUTE = re.compile(
    r"^(?:(-?\d*(?:px)?)(?:\s*|x)(-?\d*(?:px)?)|(center|top|bottom|left|right|topleft|topright|bottomleft|bottomright))$",
    re.M,
)

_ALIGNMENT: dict[str, tuple[tuple, tuple]] = {
    # name: ((col: align, alignItems, justifyContent, stretch), (row: ...))
    "topleft": (("left", "flex-start", "flex-start", None), ("left", "flex-start", "space-evenly", None)),
    "topright": (("right", "flex-end", "flex-start", None), ("right", "flex-start", "space-evenly", None)),
    "bottomright": (("right", "flex-end", "flex-end", None), ("right", "flex-end", "space-evenly", None)),
    "bottomleft": (("left", "flex-start", "flex-end", None), ("left", "flex-end", "space-evenly", None)),
    "left": (("left", "flex-start", "space-evenly", None), ("left", "center", "space-evenly", None)),
    "right": (("right", "flex-end", "space-evenly", None), ("right", "center", "space-evenly", None)),
    "top": ((None, "center", "flex-start", None), (None, "flex-start", "space-evenly", None)),
    "bottom": ((None, "center", "flex-end", None), (None, "flex-end", "space-evenly", None)),
    "stretch": ((None, "center", "space-evenly", "stretch-column"), (None, "center", "space-evenly", "stretch-row")),
    "block": (("justify", "center", "space-evenly", None), ("justify", "center", "space-evenly", None)),
    "justify": (("justify", "center", "space-evenly", None), ("justify", "center", "space-evenly", None)),
}


def _get_alignment(value: str | None, flow: str | None) -> tuple:
    direction = flow if flow is not None else "col"
    if value in _ALIGNMENT:
        col, row = _ALIGNMENT[value]
        # Upstream compares `direction == 'col'`; any other flow value takes the row branch
        if value in ("block", "justify"):
            return col
        return col if direction == "col" else row
    return (None, "center", "center", None)


def _xy_of(name: str, width: float, height: float, max_w: float, max_h: float) -> tuple[float, float]:
    return {
        "topleft": (0, 0),
        "topright": (max_w - width, 0),
        "bottomleft": (0, max_h - height),
        "bottomright": (max_w - width, max_h - height),
        "left": (0, (max_h - height) / 2),
        "right": (max_w - width, (max_h - height) / 2),
        "top": ((max_w - width) / 2, 0),
        "bottom": ((max_w - width) / 2, max_h - height),
        "center": ((max_w - width) / 2, (max_h - height) / 2),
    }.get(name, (0, 0))


def _to_relative(maximum: float, value: str) -> float:
    if value.lower().endswith("px"):
        return _js_number(value.lower().replace("px", "", 1)) / maximum * 100
    return _js_number(value)


def _to_pixel(maximum: float, value: str) -> float:
    if value.lower().endswith("px"):
        return _js_number(value.lower().replace("px", "", 1))
    return (maximum / 100) * _js_number(value)


def _read_grid(drag: str, drop: str, absolute: bool, ctx: Context) -> dict[str, float] | None:
    slide_w = _js_number(str(ctx.options.get("width", 960)))
    slide_h = _js_number(str(ctx.options.get("height", 700)))
    result: dict[str, float] = {"slideWidth": slide_w, "slideHeight": slide_h}
    if absolute:
        result["maxWidth"], result["maxHeight"] = slide_w, slide_h
        convert = _to_pixel
    else:
        result["maxWidth"], result["maxHeight"] = 100, 100
        convert = _to_relative

    drag_m = _GRID_ATTRIBUTE.search(drag)
    drop_m = _GRID_ATTRIBUTE.search(drop)
    if drag_m is None or drop_m is None:
        return None  # upstream: destructuring null throws, caught, returns undefined
    width, height = drag_m.group(1), drag_m.group(2)
    x, y, name = drop_m.group(1), drop_m.group(2), drop_m.group(3)
    if width:
        result["width"] = convert(result["slideWidth"], width)
    if height:
        result["height"] = convert(result["slideHeight"], height)
    if name:
        nx, ny = _xy_of(
            name,
            result.get("width", math.nan),
            result.get("height", math.nan),
            result["maxWidth"],
            result["maxHeight"],
        )
        result["x"], result["y"] = nx, ny
    else:
        if x:
            result["x"] = convert(result["slideWidth"], x)
        if y:
            result["y"] = convert(result["slideHeight"], y)
    return result


def _left_of(grid: dict[str, float]) -> float | None:
    x = grid.get("x")
    if x is not None and x < 0:
        return grid["maxWidth"] + x - grid.get("width", math.nan)
    return x


def _top_of(grid: dict[str, float]) -> float | None:
    y = grid.get("y")
    if y is not None and y < 0:
        return grid["maxHeight"] + y - grid.get("height", math.nan)
    return y


def _grid_transformer(el: Properties) -> None:
    absolute = el.get_attribute("absolute") == "true"
    default_drop, unit = ("480px 700px", "px") if absolute else ("50 100", "%")

    drop = el.get_attribute("drop")
    if drop is not None:
        drag = el.get_attribute("drag")
        drag = drag if drag is not None else default_drop
        grid = _read_grid(drag, drop, absolute, el.ctx)
        if grid is not None:
            left = _js_str(_left_of(grid)) + unit
            top = _js_str(_top_of(grid)) + unit
            height = _js_str(grid.get("height")) + unit
            width = _js_str(grid.get("width")) + unit
            el.add_style("position", "absolute")
            el.add_style("left", left)
            el.add_style("top", top)
            el.add_style("height", height)
            el.add_style("width", width)
            if absolute:
                el.add_style("min-height", height)
        el.delete_attribute("drag")
        el.delete_attribute("drop")

    if el.get_attribute("align") or drop:
        flow = el.get_attribute("flow")
        align, align_items, justify_content, stretch = _get_alignment(el.get_attribute("align"), flow)
        justify = el.get_attribute("justify-content")
        justify_ctx = justify if justify is not None else justify_content

        if align:
            el.add_attribute("align", align, False)
        if stretch:
            el.add_class(stretch)

        el.add_style("display", "flex")
        if flow == "row":
            el.add_style("flex-direction", "row")
            el.add_style("align-items", align_items)
            el.add_style("justify-content", justify_ctx)
            el.add_class("flex-even")
        else:
            el.add_style("flex-direction", "column")
            el.add_style("align-items", align_items)
            el.add_style("justify-content", justify_ctx)

        center = el.ctx.options.get("center")
        if center is not None and not center:
            el.add_style("align-items", "start")
        el.delete_attribute("flow")
        el.delete_attribute("justify-content")


_TRANSFORMERS = (
    _class_transformer,
    _style_transformer,
    _background_transformer,
    _padding_transformer,
    _animate_transformer,
    _fragment_transformer,
    _style_mapping("opacity", "opacity"),
    _border_transformer,
    _style_mapping("filter", "filter"),
    _rotate_transformer,
    _grid_transformer,
    _background_image_transformer,
)


def _transform(el: Properties) -> None:
    for transformer in _TRANSFORMERS:
        transformer(el)


# --- Colour parsing (port of the `color` / `color-string` npm packages, for `bg`) ----------------

_COLOR_NAMES: dict[str, list[int]] = json.loads((Path(__file__).parent / "data" / "color_names.json").read_text())

_HEX = re.compile(r"^#([a-f0-9]{6})([a-f0-9]{2})?$", re.I)
_ABBR = re.compile(r"^#([a-f0-9]{3,4})$", re.I)
_RGBA = re.compile(
    r"^rgba?\(\s*([+-]?\d+)(?=[\s,])\s*(?:,\s*)?([+-]?\d+)(?=[\s,])\s*(?:,\s*)?([+-]?\d+)\s*"
    r"(?:[,|/]\s*([+-]?[\d.]+)(%?)\s*)?\)$"
)
_PER = re.compile(
    r"^rgba?\(\s*([+-]?[\d.]+)%\s*,?\s*([+-]?[\d.]+)%\s*,?\s*([+-]?[\d.]+)%\s*(?:[,|/]\s*([+-]?[\d.]+)(%?)\s*)?\)$"
)
_KEYWORD = re.compile(r"^(\w+)$", re.A)
_NUM = r"([+-]?(?=\.\d|\d)(?:0|[1-9]\d*)?(?:\.\d*)?(?:[eE][+-]?\d+)?)"
_HSL = re.compile(
    r"^hsla?\(\s*([+-]?(?:\d{0,3}\.)?\d+)(?:deg)?\s*,?\s*([+-]?[\d.]+)%\s*,?\s*([+-]?[\d.]+)%\s*"
    r"(?:[,|/]\s*" + _NUM + r"\s*)?\)$"
)
_HWB = re.compile(
    r"^hwb\(\s*([+-]?\d{0,3}(?:\.\d+)?)(?:deg)?\s*,\s*([+-]?[\d.]+)%\s*,\s*([+-]?[\d.]+)%\s*(?:,\s*"
    + _NUM
    + r"\s*)?\)$"
)


def _parse_float(value: str) -> float:
    match = re.match(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", value)
    return float(match.group(0)) if match else math.nan


def _parse_int(value: str) -> float:
    match = re.match(r"\s*[+-]?\d+", value)
    return float(int(match.group(0))) if match else math.nan


def _hsl_to_rgb(h: float, s: float, l: float) -> list[float]:  # noqa: E741
    h, s, l = h / 360, s / 100, l / 100  # noqa: E741
    if s == 0:
        return [l * 255] * 3
    t2 = l * (1 + s) if l < 0.5 else l + s - l * s
    t1 = 2 * l - t2
    rgb = []
    for i in range(3):
        t3 = h + 1 / 3 * -(i - 1)
        if t3 < 0:
            t3 += 1
        if t3 > 1:
            t3 -= 1
        if 6 * t3 < 1:
            val = t1 + (t2 - t1) * 6 * t3
        elif 2 * t3 < 1:
            val = t2
        elif 3 * t3 < 2:
            val = t1 + (t2 - t1) * (2 / 3 - t3) * 6
        else:
            val = t1
        rgb.append(val * 255)
    return rgb


def _hwb_to_rgb(h: float, wh: float, bl: float) -> list[float]:
    h, wh, bl = h / 360, wh / 100, bl / 100
    ratio = wh + bl
    if ratio > 1:
        wh /= ratio
        bl /= ratio
    i = math.floor(6 * h)
    v = 1 - bl
    f = 6 * h - i
    if i & 1:
        f = 1 - f
    n = wh + f * (v - wh)
    r, g, b = {
        1: (n, v, wh),
        2: (wh, v, n),
        3: (wh, n, v),
        4: (n, wh, v),
        5: (v, wh, n),
    }.get(i, (v, n, wh))
    return [r * 255, g * 255, b * 255]


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(low, value), high)


def parse_color(value: str) -> list[float] | None:
    """Return ``[r, g, b]`` for a CSS colour the ``color`` package accepts, else None."""
    if not value:
        return None
    prefix = value[:3].lower()
    if prefix == "hsl":
        m = _HSL.match(value)
        if not m:
            return None
        h = ((_parse_float(m.group(1)) % 360) + 360) % 360
        return _hsl_to_rgb(h, _clamp(_parse_float(m.group(2)), 0, 100), _clamp(_parse_float(m.group(3)), 0, 100))
    if prefix == "hwb":
        m = _HWB.match(value)
        if not m:
            return None
        h = ((_parse_float(m.group(1)) % 360) + 360) % 360
        return _hwb_to_rgb(h, _clamp(_parse_float(m.group(2)), 0, 100), _clamp(_parse_float(m.group(3)), 0, 100))

    if m := _HEX.match(value):
        rgb = [float(int(m.group(1)[i : i + 2], 16)) for i in (0, 2, 4)]
    elif m := _ABBR.match(value):
        rgb = [float(int(c + c, 16)) for c in m.group(1)[:3]]
    elif m := _RGBA.match(value):
        rgb = [_parse_int(m.group(i)) for i in (1, 2, 3)]
    elif m := _PER.match(value):
        rgb = [float(round(_parse_float(m.group(i)) * 2.55)) for i in (1, 2, 3)]
    elif m := _KEYWORD.match(value):
        if m.group(1) == "transparent":
            return [0.0, 0.0, 0.0]
        if m.group(1) not in _COLOR_NAMES:
            return None
        return [float(c) for c in _COLOR_NAMES[m.group(1)]]
    else:
        return None
    return [_clamp(c, 0, 255) for c in rgb]


def is_light(rgb: list[float]) -> bool:
    yiq = (rgb[0] * 2126 + rgb[1] * 7152 + rgb[2] * 722) / 10000
    return not yiq < 128


# --- Comments -----------------------------------------------------------------------------------


class Comment(Properties):
    def __init__(self, comment_type: str, attributes: dict[str, str], ctx: Context) -> None:
        attributes["onTarget"] = comment_type
        super().__init__(attributes, ctx)
        self.type = comment_type


_READ_COMMENT = re.compile(r"<!--.*-->")
_PARSE = re.compile(r"<!--\s*(?:\.)?(element|slide):?\s*(.*)-->")
_PARSE_PROPERTIES = re.compile(r"([^=]*)\s*=\s*\"([^\"]*)\"\s*|([^=]*)\s*=\s*'([^']*)'\s*|([^ ]*)\s*")


class CommentParser:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def comment_to_string(self, comment: Comment) -> str:
        return f"<!-- .{comment.type}: {self.build_attributes(comment)} -->"

    def build_attributes(self, comment: Properties) -> str:
        styles = comment.get_styles()
        classes = comment.get_classes()
        styles_string = f'style="{styles}" ' if styles else ""
        classes_string = f'class="{classes}" ' if classes else ""
        return f"{styles_string}{classes_string}{comment.get_attributes()}".strip()

    def parse_line(self, line: str | None) -> Comment | None:
        if line is None or not self.line_has_comment(line):
            return None
        found = _READ_COMMENT.search(line)
        return self.parse_comment(found.group(0) if found else "")

    def parse_comment(self, comment: str) -> Comment | None:
        match = _PARSE.search(comment)
        if match is None:
            return None
        return Comment(match.group(1), self._parse_attributes(match.group(2)), self.ctx)

    def build_comment(
        self,
        comment_type: str,
        style: list[str] | None = None,
        clazz: list[str] | None = None,
        attributes: dict[str, str] | None = None,
    ) -> Comment:
        attributes = attributes if attributes is not None else {}
        if clazz:
            existing = attributes.get("class")
            attributes["class"] = " ".join([*existing.split(" "), *clazz]) if existing else " ".join(clazz)
        if style:
            existing = attributes.get("style")
            if existing:
                attributes["style"] = "; ".join([*(v.strip() for v in existing.split(";")), *style])
            else:
                attributes["style"] = "; ".join(style)
        return Comment(comment_type, attributes, self.ctx)

    def line_has_comment(self, line: str) -> bool:
        return _PARSE.search(line) is not None

    @staticmethod
    def _parse_attributes(properties: str) -> dict[str, str]:
        attributes: dict[str, str] = {}
        regex = JSRegExp(_PARSE_PROPERTIES.pattern, "g")
        while (m := regex.exec(properties)) is not None:
            if m.start() == regex.last_index:
                regex.last_index += 1
            key = None
            if m.group(1) is not None:
                key = m.group(1)
                attributes[key] = m.group(2)
            if m.group(3) is not None:
                key = m.group(3)
                attributes[key] = m.group(4)
            if m.group(5):
                attributes[m.group(5)] = "true"
        return attributes
