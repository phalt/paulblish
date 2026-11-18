"""Port of Advanced Slides' test/comment.unit.test.ts: parsing <!-- element/slide --> annotations.

Upstream compares the parsed comment with one built by ``Comment.of(type, style, class, attrs)``;
here both go through the same Python code and are compared field by field.
"""

import pytest

from paulblish.slides.preprocessor import DEFAULTS, Context
from paulblish.slides.properties import CommentParser, is_light, parse_color


@pytest.fixture
def parser():
    return CommentParser(Context(options=dict(DEFAULTS)))


def _state(comment):
    return comment.type, comment.style, set(comment.classes), comment.attributes


CASES = [
    ('text with border <!-- element class="with-border" -->', ("element", [], ["with-border"], {})),
    ('text with background <!-- element style="background:blue" -->', ("element", ["background:blue"], [], {})),
    ("<!-- slide -->", ("slide", [], [], {})),
    ('text with attribute <!-- element data-toggle="modal" -->', ("element", [], [], {"data-toggle": "modal"})),
    ('<!-- .slide: style="background-color: coral;" -->', ("slide", ["background-color: coral"], [], {})),
    ('<!-- slide bg="coral" -->', ("slide", [], ["has-light-background"], {"data-background-color": "coral"})),
    ('<!-- slide bg="black" -->', ("slide", [], ["has-dark-background"], {"data-background-color": "black"})),
    ('<!-- slide bg="[[Image.png]]" -->', ("slide", [], [], {"data-background-image": "[[Image.png]]"})),
    ("<!-- slide data-auto-animate -->", ("slide", [], [], {"data-auto-animate": "true"})),
    (
        '<!-- slide bg="coral" class="reveal section small" style="width: 200px; height: 400px; margin: 0" '
        'data-toggle="modal" -->',
        (
            "slide",
            ["width: 200px"],
            ["has-light-background", "small"],
            {
                "data-toggle": "modal",
                "data-background-color": "coral",
                "class": "reveal section",
                "style": "height: 400px; margin: 0",
            },
        ),
    ),
    ('<!-- slide pad="10px 15px" -->', ("slide", ["padding: 10px 15px", "box-sizing: border-box"], [], {})),
    ('<!-- slide animate="fadeIn slower" -->', ("slide", [], ["fadeIn", "slower"], {})),
    ('<!-- element frag="1" -->', ("element", [], ["fragment"], {"data-fragment-index": "1"})),
    ('<!-- element opacity="0.5" -->', ("element", ["opacity: 0.5"], [], {})),
    (
        '<!-- slide border="thick dotted blue" -->',
        ("slide", ["border: thick dotted blue", "box-sizing: border-box"], [], {}),
    ),
    ('<!-- slide rotate="-10" -->', ("slide", ["transform: rotate(-10deg)"], [], {})),
    ('<!-- slide rotate="-10deg" -->', ("slide", ["transform: rotate(-10deg)"], [], {})),
]


@pytest.mark.parametrize(("line", "expected"), CASES, ids=[c[0] for c in CASES])
def test_parse_comment_matches_built_comment(parser, line, expected):
    kind, style, clazz, attributes = expected
    parsed = parser.parse_line(line)
    built = parser.build_comment(kind, style, clazz, dict(attributes))
    assert _state(parsed) == _state(built)


def test_invalid_input_is_none(parser):
    assert parser.parse_line('<-- .slde: stle="background-color: coral;" -') is None


def test_comment_to_string(parser):
    comment = parser.parse_line('<!-- element class="a b" style="color: red" data-x="1" -->')
    assert parser.comment_to_string(comment) == '<!-- .element: style="color: red" class="a b" data-x="1" -->'


@pytest.mark.parametrize(
    ("value", "light"),
    [
        ("white", True),
        ("black", False),
        ("coral", True),
        ("#fff", True),
        ("#2d3e50", False),
        ("rgb(70, 70, 255)", False),
        ("hsla(315, 100%, 50%, 1)", False),
        ("aquamarine", True),
        ("transparent", False),
    ],
)
def test_colour_lightness_matches_color_package(value, light):
    rgb = parse_color(value)
    assert rgb is not None
    assert is_light(rgb) is light


@pytest.mark.parametrize("value", ["[[Image.png]]", "Image.png", "https://example.com/a.png", "Red", ""])
def test_non_colours_are_images(value):
    assert parse_color(value) is None
