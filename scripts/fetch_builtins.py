"""Refetches each language's list of built-in modules and writes stepwise/builtins.json.

Stepwise asks the installed tool first (python, node, go); these saved lists are the fallback
when it isn't installed, and the only source for Java, Rust and C#. Run from the repo root:

    python scripts/fetch_builtins.py
"""

import json
import re
import urllib.request
from datetime import date
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "stepwise" / "builtins.json"

PYTHON_URL = "https://docs.python.org/3/py-modindex.html"
NODE_URL = "https://raw.githubusercontent.com/sindresorhus/builtin-modules/main/builtin-modules.json"
GO_URL = "https://api.github.com/repos/golang/go/contents/src"
JAVA_URL = "https://docs.oracle.com/en/java/javase/21/docs/api/allpackages-index.html"
RUST_URL = "https://doc.rust-lang.org/std/"
CSHARP_URL = "https://learn.microsoft.com/en-us/dotnet/standard/class-library-overview"


def get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "stepwise-fetch-builtins"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def python() -> list[str]:
    names = re.findall(r'<code class="xref">([A-Za-z_][\w.]*)</code>', get(PYTHON_URL))
    return sorted({n for n in names if "." not in n})


def node() -> list[str]:
    return sorted(set(json.loads(get(NODE_URL))))


def go() -> list[str]:
    # Every top-level folder in Go's src/ is a standard package, apart from the toolchain's own.
    entries = json.loads(get(GO_URL))
    skip = {"cmd", "vendor", "testdata", "internal"}
    return sorted(e["name"] for e in entries if e["type"] == "dir" and e["name"] not in skip)


def java() -> list[str]:
    return sorted(set(re.findall(r'href="[^"]*?/package-summary\.html">([a-z][\w.]*)</a>', get(JAVA_URL))))


def main() -> None:
    data = {
        "fetched": date.today().isoformat(),
        "python": {"source": PYTHON_URL, "modules": python()},
        "node": {"source": NODE_URL, "modules": node()},
        "go": {"source": GO_URL, "packages": go(),
               "rule": "A path whose first element has no dot (fmt, net/http) is standard library."},
        "java": {"source": JAVA_URL, "packages": java()},
        # These two have no fetchable list: Rust's are fixed crates, and C#'s are Microsoft's documented roots.
        "rust": {"source": RUST_URL, "crates": ["alloc", "core", "proc_macro", "std", "test"]},
        "csharp": {"source": CSHARP_URL,
                   "roots": ["System", "Microsoft.CSharp", "Microsoft.VisualBasic", "Microsoft.Win32"]},
    }
    for language in ("python", "node", "go", "java"):
        key = "modules" if "modules" in data[language] else "packages"
        if len(data[language][key]) < 20:
            raise SystemExit(f"Only {len(data[language][key])} {language} built-ins found; the page may have changed.")
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
    for language in ("python", "node", "go", "java", "rust", "csharp"):
        values = next(v for k, v in data[language].items() if isinstance(v, list))
        print(f"{language}: {len(values)}")


if __name__ == "__main__":
    main()
