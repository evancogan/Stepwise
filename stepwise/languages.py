"""What each language counts as built in, how its code imports things, and how its dependency
file lists what has to be installed. The prerequisites check reads all three to compare a
project's dependency file with what its code actually imports."""

import ast
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .store import Project, slugify

SAVED = json.loads(Path(__file__).with_name("builtins.json").read_text(encoding="utf-8"))


def norm(name: str) -> str:
    """Package names compared the way pip compares them: case and -, _, . don't matter."""
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass
class Import:
    name: str  # as written, e.g. "PySide6.QtCore", "node:fs", "github.com/x/y"
    file: str
    part_of: str = ""  # Python only: the package a name was pulled from, e.g. QtCore from PySide6


@dataclass
class Builtins:
    names: set[str]
    live: bool  # True when the installed tool was asked, False for Stepwise's saved list
    extra: dict = field(default_factory=dict)  # anything else the tool reported (Python: installed packages)


class Language:
    key = ""
    name = ""
    tool = ""  # what's installed to run it, e.g. Node for JavaScript
    extensions: tuple[str, ...] = ()
    dep_files: tuple[str, ...] = ()  # the first is the one Stepwise creates
    version_command = ""
    comes_with = ""  # e.g. "comes with Python"
    install_hint = ""  # a sentence on installing what the dependency file lists; {file} is its name
    dep_example = ""  # one sentence on how to add a library, shown on the stage 4 page
    reliable_match = True  # False where an import can't be matched to a dependency for certain

    # --- dependency file ---------------------------------------------------

    def dep_path(self, project: Project) -> Path | None:
        for name in self.dep_files:
            matches = sorted(project.root.glob(name))
            if matches:
                return matches[0]
        return None

    def new_dep_path(self, project: Project) -> Path:
        return project.root / self.dep_files[0]

    def starter(self, project: Project) -> str:
        return ""

    def read_deps(self, path: Path) -> list[str]:
        raise NotImplementedError

    # --- imports -----------------------------------------------------------

    def scan(self, text: str, file: str) -> list[Import]:
        raise NotImplementedError

    def top(self, name: str) -> str:
        """The part of an import that names the package it comes from."""
        return name

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        return False

    async def builtins(self, run) -> Builtins:
        return Builtins(set(), live=False)

    def is_builtin(self, name: str, builtins: Builtins) -> bool:
        return self.top(name) in builtins.names

    def matches(self, imp: Import, dep: str, builtins: Builtins) -> bool:
        return self.top(imp.name) == dep

    def installed(self, dep: str, project: Project, builtins: Builtins) -> bool | None:
        """True or False when Stepwise can tell, None when the build tool handles it."""
        return None


class Python(Language):
    key, name, tool = "python", "Python", "Python"
    extensions = (".py",)
    dep_files = ("requirements.txt", "pyproject.toml")
    version_command = "python --version"
    comes_with = "comes with Python"
    install_hint = "Run pip install -r {file} to install them."
    dep_example = "Add one line for each library you install, the name you'd pip install, like PySide6."

    # One call gets the standard library, which installed packages provide which import names
    # (bs4 comes from beautifulsoup4), and what's installed, from the user's own Python.
    LIVE = ('python -c "import sys, json, importlib.metadata as m; '
            "print(json.dumps({'stdlib': sorted(getattr(sys, 'stdlib_module_names', [])), "
            "'provides': m.packages_distributions(), "
            "'installed': sorted({d.metadata['Name'] for d in m.distributions() if d.metadata['Name']})}))\"")

    def starter(self, project: Project) -> str:
        return "# One library per line, the name you'd pip install, like:\n# PySide6\n"

    def read_deps(self, path: Path) -> list[str]:
        if path.name == "pyproject.toml":
            lines = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {}).get("dependencies", [])
        else:
            lines = path.read_text(encoding="utf-8").splitlines()
        names = []
        for line in lines:
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-") and (m := re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)):
                names.append(m.group(0))
        return names

    def scan(self, text: str, file: str) -> list[Import]:
        found = []
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                found += [Import(alias.name, file) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.append(Import(node.module, file))
                found += [Import(alias.name, file, part_of=node.module.split(".")[0]) for alias in node.names]
        return found

    def top(self, name: str) -> str:
        return name.split(".")[0]

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        top = self.top(imp.name)
        return (project.root / f"{top}.py").exists() or (project.root / top / "__init__.py").exists()

    async def builtins(self, run) -> Builtins:
        code, out = await run(self.LIVE)
        if code == 0:
            try:
                data = json.loads(out.splitlines()[-1])
                if data["stdlib"]:
                    return Builtins(set(data["stdlib"]), live=True,
                                    extra={"provides": data["provides"], "installed": {norm(n) for n in data["installed"]}})
            except (ValueError, KeyError, IndexError):
                pass
        return Builtins(set(SAVED["python"]["modules"]), live=False)

    def matches(self, imp: Import, dep: str, builtins: Builtins) -> bool:
        top = self.top(imp.name)
        providers = builtins.extra.get("provides", {}).get(top, [])
        return norm(dep) == norm(top) or norm(dep) in {norm(p) for p in providers}

    def installed(self, dep: str, project: Project, builtins: Builtins) -> bool | None:
        installed = builtins.extra.get("installed")
        return None if installed is None else norm(dep) in installed


class JavaScript(Language):
    key, name, tool = "javascript", "JavaScript", "Node"
    extensions = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx")
    dep_files = ("package.json",)
    version_command = "node --version"
    comes_with = "comes with Node"
    install_hint = "Run npm install to install them."
    dep_example = ('Add each library under "dependencies", like "lodash": "^4.17.21". Running '
                   "npm install lodash adds it for you.")
    PATTERN = re.compile(r"""(?:\bimport\s+(?:[\w*{}\s,$]+?\s+from\s+)?|\bexport\s+[\w*{}\s,$]+?\s+from\s+|"""
                         r"""\brequire\s*\(\s*|\bimport\s*\(\s*)['"]([^'"]+)['"]""")

    def starter(self, project: Project) -> str:
        return json.dumps({"name": slugify(project.name), "version": "1.0.0", "dependencies": {}}, indent=2) + "\n"

    def read_deps(self, path: Path) -> list[str]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [*data.get("dependencies", {}), *data.get("devDependencies", {})]

    def scan(self, text: str, file: str) -> list[Import]:
        return [Import(m.group(1), file) for m in self.PATTERN.finditer(text)]

    def top(self, name: str) -> str:
        parts = name.removeprefix("node:").split("/")
        return "/".join(parts[:2]) if name.startswith("@") else parts[0]

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        return imp.name.startswith((".", "/"))

    async def builtins(self, run) -> Builtins:
        code, out = await run("node -p \"require('module').builtinModules.join(' ')\"")
        if code == 0 and out.split():
            return Builtins(set(out.split()), live=True)
        return Builtins({m.removeprefix("node:") for m in SAVED["node"]["modules"]}, live=False)

    def is_builtin(self, name: str, builtins: Builtins) -> bool:
        if name.startswith("node:"):
            return True
        return name in builtins.names or self.top(name) in builtins.names

    def installed(self, dep: str, project: Project, builtins: Builtins) -> bool | None:
        return (project.root / "node_modules" / dep / "package.json").is_file()


class Go(Language):
    key, name, tool = "go", "Go", "Go"
    extensions = (".go",)
    dep_files = ("go.mod",)
    version_command = "go version"
    comes_with = "is part of Go's standard library"
    install_hint = "Running go mod tidy downloads everything in {file}."
    dep_example = "Add each library as a require line. Running go get with the library's path adds it for you."
    BLOCK = re.compile(r"\bimport\s*\((.*?)\)", re.S)
    SINGLE = re.compile(r'\bimport\s+(?:[\w.]+\s+)?"([^"]+)"')

    def starter(self, project: Project) -> str:
        return f"module {slugify(project.name)}\n"

    def read_deps(self, path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8")
        deps = re.findall(r"^\s*require\s+([^\s(]+)\s", text, re.M)
        for block in re.findall(r"^\s*require\s*\((.*?)\)", text, re.S | re.M):
            deps += [line.split()[0] for line in block.splitlines() if line.split() and not line.strip().startswith("//")]
        return deps

    def module(self, deps_path: Path | None) -> str:
        if deps_path and deps_path.is_file():
            if m := re.search(r"^\s*module\s+(\S+)", deps_path.read_text(encoding="utf-8"), re.M):
                return m.group(1)
        return ""

    def scan(self, text: str, file: str) -> list[Import]:
        names = self.SINGLE.findall(text)
        for block in self.BLOCK.findall(text):
            names += re.findall(r'"([^"]+)"', block)
        return [Import(n, file) for n in names]

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        module = self.module(deps_path)
        return bool(module) and (imp.name == module or imp.name.startswith(module + "/"))

    async def builtins(self, run) -> Builtins:
        code, out = await run("go list std")
        if code == 0 and out.split():
            return Builtins(set(out.split()), live=True)
        return Builtins(set(SAVED["go"]["packages"]), live=False)

    def is_builtin(self, name: str, builtins: Builtins) -> bool:
        # Go's own rule: standard packages never have a dot in their first path element.
        return name in builtins.names or "." not in name.split("/")[0]

    def matches(self, imp: Import, dep: str, builtins: Builtins) -> bool:
        return imp.name == dep or imp.name.startswith(dep + "/")


class Rust(Language):
    key, name, tool = "rust", "Rust", "Rust"
    extensions = (".rs",)
    dep_files = ("Cargo.toml",)
    version_command = "rustc --version"
    comes_with = "comes with Rust"
    install_hint = "cargo build downloads everything in {file}."
    dep_example = 'Add each library under [dependencies], like serde = "1". Running cargo add serde does it for you.'
    USE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?use\s+(?:::)?([A-Za-z_]\w*)", re.M)
    EXTERN = re.compile(r"\bextern\s+crate\s+([A-Za-z_]\w*)")
    MOD = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_]\w*)\s*[;{]", re.M)

    def starter(self, project: Project) -> str:
        return (f'[package]\nname = "{slugify(project.name)}"\nversion = "0.1.0"\nedition = "2021"\n\n'
                "[dependencies]\n")

    def read_deps(self, path: Path) -> list[str]:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return [*data.get("dependencies", {}), *data.get("dev-dependencies", {}), *data.get("build-dependencies", {})]

    def scan(self, text: str, file: str) -> list[Import]:
        names = self.USE.findall(text) + self.EXTERN.findall(text)
        return [Import(n, file) for n in names]

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        if imp.name in ("crate", "self", "super", "Self"):
            return True
        modules = set()
        for path in project.source_files(".rs"):
            modules |= set(self.MOD.findall(path.read_text(encoding="utf-8", errors="replace")))
            modules.add(path.stem)
        return imp.name in modules

    async def builtins(self, run) -> Builtins:
        return Builtins(set(SAVED["rust"]["crates"]), live=False)

    def matches(self, imp: Import, dep: str, builtins: Builtins) -> bool:
        return imp.name == dep.replace("-", "_")


class Java(Language):
    key, name, tool = "java", "Java", "Java"
    extensions = (".java",)
    dep_files = ("pom.xml", "build.gradle", "build.gradle.kts")
    version_command = "java -version"
    comes_with = "comes with the JDK"
    install_hint = "Maven or Gradle downloads everything in {file} when you build."
    dep_example = "Add each library as a <dependency> with its groupId, artifactId and version."
    reliable_match = False
    IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+?)(?:\.\*)?\s*;", re.M)
    PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)

    def starter(self, project: Project) -> str:
        slug = slugify(project.name)
        return ('<project xmlns="http://maven.apache.org/POM/4.0.0">\n  <modelVersion>4.0.0</modelVersion>\n'
                f"  <groupId>com.example</groupId>\n  <artifactId>{slug}</artifactId>\n  <version>1.0</version>\n"
                "  <dependencies>\n  </dependencies>\n</project>\n")

    def read_deps(self, path: Path) -> list[str]:
        if path.name == "pom.xml":
            deps = []
            for element in ET.parse(path).iter():
                if element.tag.split("}")[-1] == "dependency":
                    parts = {child.tag.split("}")[-1]: (child.text or "").strip() for child in element}
                    deps.append(f"{parts.get('groupId', '')}:{parts.get('artifactId', '')}")
            return deps
        text = path.read_text(encoding="utf-8")
        return [f"{g}:{a}" for g, a in re.findall(r"""['"]([\w.\-]+):([\w.\-]+)(?::[^'"]*)?['"]""", text)]

    def scan(self, text: str, file: str) -> list[Import]:
        return [Import(n, file) for n in self.IMPORT.findall(text)]

    def top(self, name: str) -> str:
        """The package: the segments before the first one that starts with a capital (a class)."""
        package = []
        for segment in name.split("."):
            if segment[:1].isupper():
                break
            package.append(segment)
        return ".".join(package) or name

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        packages = set()
        for path in project.source_files(".java"):
            packages |= set(self.PACKAGE.findall(path.read_text(encoding="utf-8", errors="replace")))
        package = self.top(imp.name)
        return any(package == p or package.startswith(p + ".") for p in packages)

    async def builtins(self, run) -> Builtins:
        return Builtins(set(SAVED["java"]["packages"]), live=False)

    def is_builtin(self, name: str, builtins: Builtins) -> bool:
        package = self.top(name)
        return package in builtins.names

    def matches(self, imp: Import, dep: str, builtins: Builtins) -> bool:
        # Best effort: a library's group id usually shares its first two segments with its packages
        # (com.google.code.gson -> com.google.gson), but nothing guarantees it.
        group = dep.split(":")[0].split(".")[:2]
        return self.top(imp.name).split(".")[:2] == group


class CSharp(Language):
    key, name, tool = "csharp", "C#", ".NET"
    extensions = (".cs",)
    dep_files = ("*.csproj",)
    version_command = "dotnet --version"
    comes_with = "comes with .NET"
    install_hint = "dotnet build downloads everything in {file}."
    dep_example = ('Add each library as <PackageReference Include="Name" Version="1.0" />. Running '
                   "dotnet add package Name does it for you.")
    reliable_match = False
    USING = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([A-Za-z_][\w.]*)\s*;", re.M)
    NAMESPACE = re.compile(r"^\s*namespace\s+([\w.]+)", re.M)

    def new_dep_path(self, project: Project) -> Path:
        return project.root / f"{slugify(project.name)}.csproj"

    def starter(self, project: Project) -> str:
        return ('<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n'
                "    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n  <ItemGroup>\n"
                "  </ItemGroup>\n</Project>\n")

    def read_deps(self, path: Path) -> list[str]:
        return [e.get("Include") for e in ET.parse(path).iter()
                if e.tag.split("}")[-1] == "PackageReference" and e.get("Include")]

    def scan(self, text: str, file: str) -> list[Import]:
        return [Import(n, file) for n in self.USING.findall(text)]

    def is_local(self, imp: Import, project: Project, deps_path: Path | None) -> bool:
        spaces = set()
        for path in project.source_files(".cs"):
            spaces |= set(self.NAMESPACE.findall(path.read_text(encoding="utf-8", errors="replace")))
        return any(imp.name == s or imp.name.startswith(s + ".") for s in spaces)

    async def builtins(self, run) -> Builtins:
        return Builtins(set(SAVED["csharp"]["roots"]), live=False)

    def is_builtin(self, name: str, builtins: Builtins) -> bool:
        return any(name == root or name.startswith(root + ".") for root in builtins.names)

    def matches(self, imp: Import, dep: str, builtins: Builtins) -> bool:
        return imp.name == dep or imp.name.startswith(dep + ".")


LANGUAGES: list[Language] = [Python(), JavaScript(), Go(), Rust(), Java(), CSharp()]


def language_of(file_name: str) -> Language | None:
    return next((lang for lang in LANGUAGES if file_name.lower().endswith(lang.extensions)), None)


def detect(project: Project) -> list[Language]:
    """The languages of the files listed in stage 4, in the order they first appear."""
    found: list[Language] = []
    for name, _ in project.files():
        if (lang := language_of(name)) and lang not in found:
            found.append(lang)
    return found


def code_files(project: Project, lang: Language) -> list[str]:
    names = [name for name, _ in project.files()] + [project.answer("tests.file").strip()]
    return [n for n in dict.fromkeys(names) if n and language_of(n) is lang]


def saved_date() -> str:
    return SAVED["fetched"]
