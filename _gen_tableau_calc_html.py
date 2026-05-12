"""One-off: emit HTML for Tableau calc blocks with blog005-tb-* spans."""
import html
import re

PARAMS = {
    "[All New Colours]",
    "[Colour Palette Select]",
    "[Selected Colour]",
    "[Start Colour]",
}


def span_bracket(m: re.Match) -> str:
    inner = m.group(0)
    cls = "blog005-tb-param" if inner in PARAMS else "blog005-tb-field"
    return f'<span class="{cls}">{html.escape(inner)}</span>'


def highlight_tableau(s: str) -> str:
    ph: dict[str, str] = {}
    n = 0

    def stash_comment(m: re.Match) -> str:
        nonlocal n
        key = f"__B005C{n}__"
        ph[key] = f'<span class="blog005-tb-comment">{html.escape(m.group(0))}</span>'
        n += 1
        return key

    def stash_string(m: re.Match) -> str:
        nonlocal n
        key = f"__B005S{n}__"
        ph[key] = f'<span class="blog005-tb-str">{html.escape(m.group(0))}</span>'
        n += 1
        return key

    s = re.sub(r"//[^\n]*", stash_comment, s)
    s = re.sub(r'"[^"]*"', stash_string, s)

    for w in ("IF", "THEN", "ELSE", "END"):
        s = re.sub(rf"\b{w}\b", f'<span class="blog005-tb-kw">{w}</span>', s)
    funcs = (
        r"\b(STR|MAX|MAKEPOINT|CONTAINS|LEFT|FIND|MID|LEN|"
        r"SUM|AVG|MIN|COUNT|ATTR|LOOKUP|ZN|IIF)\b"
    )
    s = re.sub(funcs, r'<span class="blog005-tb-fn">\1</span>', s)
    s = re.sub(
        r"[\{\}]",
        lambda m: f'<span class="blog005-tb-lod">{m.group(0)}</span>',
        s,
    )
    s = re.sub(r"\[[^\]]+\]", span_bracket, s)

    for k, v in ph.items():
        s = s.replace(k, v)

    # Escape only text outside our spans (no span contains raw < except our tags)
    out = []
    i = 0
    for m in re.finditer(r"<span class=\"blog005-tb-[^\"]+\">.*?</span>", s, re.DOTALL):
        out.append(html.escape(s[i : m.start()]))
        out.append(m.group(0))
        i = m.end()
    out.append(html.escape(s[i:]))
    return "".join(out)


CALCS = [
    ("blog005-tb-xnorm", "X (Normalised)", "[X]/ {MAX([X])}"),  # space before { matches Tableau
    (
        "blog005-tb-mp-lines",
        "MP- Lines (Others)",
        """IF [global_path_id] > 1 THEN
MAKEPOINT([X (Normalised)],[Y (Normalised)])
END""",
    ),
    (
        "blog005-tb-selected-section",
        "Selected Section Update",
        """IF CONTAINS([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") THEN
    // Remove the old segment and add new entry
    LEFT([All New Colours], FIND([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") - 1)
    +
    MID(
        [All New Colours],
        FIND([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") // segment start
        +
        FIND(
            MID([All New Colours], FIND([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") + 1, LEN([All New Colours])),
            // Start after segmentStart
            "|"
        ),
        LEN([All New Colours])
    )
    +
    //"|" + 
    STR([global_path_id (Clickable)]) + ":" + [Selected Colour] + "|"
ELSE

    IF LEN([All New Colours]) = 0
    THEN
    [All New Colours] + "|" + STR([global_path_id (Clickable)]) + ":" + [Selected Colour] + "|"
    ELSE
    [All New Colours] + STR([global_path_id (Clickable)]) + ":" + [Selected Colour] + "|"
    END
END""",
    ),
    (
        "blog005-tb-changed-colour",
        "Changed Colour",
        """IF CONTAINS([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") THEN

    MID(
        [All New Colours],
        FIND([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") + LEN("|" + STR([global_path_id (Clickable)]) + ":"),
        FIND(
            MID(
                [All New Colours],
                FIND([All New Colours], "|" + STR([global_path_id (Clickable)]) + ":") + LEN("|" + STR([global_path_id (Clickable)]) + ":"),
                LEN([All New Colours])
            ),
            "|"
        ) - 1
    )

ELSE
    [Start Colour]
END""",
    ),
    (
        "blog005-tb-palette-concat",
        "Colour Palette Concat",
        'STR([Colour Palette Select])+"-"+STR([Colour Palette ID])',
    ),
]

for aid, title, code in CALCS:
    inner = highlight_tableau(code)
    print(f'            <section class="blog005-code-step" aria-labelledby="{aid}">')
    print(f'              <h4 id="{aid}" class="blog005-code-step__label">{html.escape(title)}</h4>')
    if aid == "blog005-tb-selected-section":
        print(
            '              <div class="code-block-wrap blog005-code-expand blog005-code-expand--tb-long">'
        )
        print('                <button class="code-copy" type="button" data-code-copy>Copy</button>')
        print(
            '                <div class="blog005-code-expand__viewport" id="blog005-tb-selected-section-region" role="region" aria-label="Tableau: Selected Section Update">'
        )
        print(f"                <pre><code>{inner}</code></pre>")
        print("                </div>")
        print(
            """                <button
                  class="blog005-code-expand__toggle"
                  type="button"
                  aria-expanded="false"
                  aria-controls="blog005-tb-selected-section-region"
                >
                  Show full code
                </button>"""
        )
    else:
        print('              <div class="code-block-wrap">')
        print('                <button class="code-copy" type="button" data-code-copy>Copy</button>')
        print(f"                <pre><code>{inner}</code></pre>")
    print("              </div>")
    print("            </section>")
