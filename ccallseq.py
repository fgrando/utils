#!/usr/bin/env python3
"""Lightweight C call-sequence extractor for console use.

This tool does not depend on external parsers or compilers. It performs a
best-effort scan of C source and header files to infer function definitions and
call sites, and then prints call trees starting from a selected function.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

# A node identifies one function definition: (name, defining file). Callees
# that were never seen as a definition (stdlib calls, macros, etc.) are kept
# as leaves: their "file" is the standard header that declares them (best
# effort, see STDLIB_HEADERS below), or empty if unrecognized.
NodeKey = Tuple[str, str]

# Best-effort C/POSIX standard library function -> declaring header, used to
# label call leaves that were never defined in the scanned source.
_STDLIB_FUNCTIONS_BY_HEADER: Dict[str, Tuple[str, ...]] = {
    "assert.h": ("assert",),
    "ctype.h": (
        "isalnum", "isalpha", "isblank", "iscntrl", "isdigit", "isgraph",
        "islower", "isprint", "ispunct", "isspace", "isupper", "isxdigit",
        "tolower", "toupper",
    ),
    "locale.h": ("setlocale", "localeconv"),
    "math.h": (
        "ceil", "fabs", "floor", "fmod", "pow", "sqrt", "sin", "cos", "tan",
        "asin", "acos", "atan", "atan2", "exp", "log", "log10", "round", "trunc",
    ),
    "setjmp.h": ("setjmp", "longjmp"),
    "signal.h": ("signal", "raise", "sigaction", "sigemptyset", "sigaddset", "kill"),
    "stdarg.h": ("va_start", "va_end", "va_arg", "va_copy"),
    "stdio.h": (
        "printf", "fprintf", "sprintf", "snprintf", "vprintf", "vfprintf",
        "vsprintf", "vsnprintf", "scanf", "fscanf", "sscanf", "fopen",
        "freopen", "fclose", "fflush", "fread", "fwrite", "fseek", "ftell",
        "rewind", "fgetpos", "fsetpos", "remove", "rename", "tmpfile",
        "tmpnam", "fgets", "fputs", "fgetc", "fputc", "getc", "putc",
        "getchar", "putchar", "gets", "puts", "perror", "feof", "ferror",
        "clearerr",
    ),
    "stdlib.h": (
        "malloc", "calloc", "realloc", "free", "exit", "abort", "atexit",
        "atoi", "atol", "atoll", "atof", "strtol", "strtoul", "strtoll",
        "strtoull", "strtod", "rand", "srand", "qsort", "bsearch", "abs",
        "labs", "llabs", "div", "ldiv", "getenv", "setenv", "unsetenv",
        "system", "mblen", "mbtowc", "wctomb", "mbstowcs", "wcstombs",
    ),
    "string.h": (
        "memcpy", "memmove", "memset", "memcmp", "memchr", "strcpy",
        "strncpy", "strcat", "strncat", "strcmp", "strncmp", "strcoll",
        "strchr", "strrchr", "strspn", "strcspn", "strpbrk", "strstr",
        "strtok", "strxfrm", "strlen", "strerror", "strdup",
    ),
    "time.h": (
        "time", "clock", "difftime", "mktime", "asctime", "ctime", "gmtime",
        "localtime", "strftime",
    ),
    "wchar.h": (
        "wcslen", "wcscpy", "wcsncpy", "wcscat", "wcsncat", "wcscmp",
        "wcsncmp", "wcschr", "wcsrchr", "wcsstr", "wcstok", "wprintf",
        "fwprintf", "swprintf", "wcstol", "wcstoul", "wcstod",
    ),
    # POSIX
    "unistd.h": (
        "read", "write", "close", "lseek", "unlink", "rmdir", "access",
        "chdir", "getcwd", "fork", "execve", "execv", "execvp", "execl",
        "execlp", "pipe", "dup", "dup2", "sleep", "usleep", "alarm",
        "getpid", "getppid", "getuid", "geteuid", "getgid", "getegid",
        "isatty", "gethostname",
    ),
    "fcntl.h": ("open", "fcntl", "creat"),
    "sys/stat.h": ("stat", "fstat", "lstat", "mkdir", "chmod", "umask"),
    "sys/socket.h": (
        "socket", "bind", "listen", "accept", "connect", "send", "recv",
        "sendto", "recvfrom", "shutdown", "setsockopt", "getsockopt",
        "getsockname", "getpeername",
    ),
    "arpa/inet.h": (
        "inet_addr", "inet_ntoa", "inet_pton", "inet_ntop",
        "htons", "htonl", "ntohs", "ntohl",
    ),
    "pthread.h": (
        "pthread_create", "pthread_join", "pthread_exit", "pthread_detach",
        "pthread_mutex_init", "pthread_mutex_destroy", "pthread_mutex_lock",
        "pthread_mutex_unlock", "pthread_cond_init", "pthread_cond_wait",
        "pthread_cond_signal", "pthread_cond_broadcast",
    ),
    "dirent.h": ("opendir", "readdir", "closedir", "rewinddir"),
    "poll.h": ("poll",),
    "sys/select.h": ("select",),
    "sys/wait.h": ("wait", "waitpid"),
    "sys/mman.h": ("mmap", "munmap", "mprotect"),
}

STDLIB_HEADERS: Dict[str, str] = {
    name: header
    for header, names in _STDLIB_FUNCTIONS_BY_HEADER.items()
    for name in names
}


def _iter_c_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    if root.is_file() and root.suffix.lower() in {".c", ".h", ".cpp", ".hpp"}:
        return [root]
    files: List[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".c", ".h", ".cpp", ".hpp"}:
            files.append(path)
    return files


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


class CFunctionParser:
    def __init__(self) -> None:
        # Every node defined anywhere, indexed by plain name so a call site
        # (which only has a name) can be resolved to every matching definition.
        self.nodes_by_name: Dict[str, Set[NodeKey]] = {}
        self.calls: Dict[NodeKey, Set[str]] = {}

    def parse_file(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = _strip_comments(text)
        file_key = str(path)

        defs = self._extract_function_definitions(text)
        for name in defs:
            node = (name, file_key)
            self.nodes_by_name.setdefault(name, set()).add(node)
            self.calls.setdefault(node, set())

        for name in defs:
            node = (name, file_key)
            body = self._extract_function_body(text, name)
            if body is None:
                continue
            self.calls[node].update(self._extract_call_sites(body))

    def _extract_function_definitions(self, text: str) -> List[str]:
        defs: List[str] = []
        # The separator before the name is whitespace-or-* (not just
        # whitespace) so pointer-returning functions written as
        # "Type *name(...)" -- with no space between '*' and the name --
        # are still recognized, not just "Type* name(...)"/"Type * name(...)".
        for match in re.finditer(
            r"(?:^|\n)\s*[A-Za-z_][\w\s\*]*?[\s\*]([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{", text
        ):
            name = match.group(1)
            if name not in {"if", "for", "while", "switch", "return"}:
                defs.append(name)
        return defs

    def _extract_function_body(self, text: str, name: str) -> str | None:
        pattern = re.compile(rf"\b{name}\s*\([^;]*\)\s*\{{(.*?)\}}", re.S)
        match = pattern.search(text)
        if not match:
            return None
        return match.group(1)

    def _extract_call_sites(self, body: str) -> Set[str]:
        calls: Set[str] = set()
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
            name = match.group(1)
            if name in {"if", "for", "while", "switch", "return", "sizeof"}:
                continue
            calls.add(name)
        return calls


@dataclass
class CallGraph:
    calls: Dict[NodeKey, Set[NodeKey]]
    # Nodes that came from an actual function definition in the scanned
    # source, as opposed to leaves synthesized for unresolved call sites
    # (stdlib functions labelled with their header, or truly unknown names).
    defined: Set[NodeKey] = field(default_factory=set)


def build_call_graph(paths: List[Path | str]) -> CallGraph:
    parser = CFunctionParser()
    files = []
    for raw in paths:
        files.extend(_iter_c_files(Path(raw)))

    for path in files:
        parser.parse_file(path)

    defined = set(parser.calls.keys())

    # Resolve each call site (a bare name) to every known definition with
    # that name -- this is what keeps same-named functions in different
    # files as distinct branches instead of merging their callees together.
    # A name with no known definition becomes a leaf node, labelled with its
    # standard header if it's a recognized stdlib/POSIX function, else empty.
    resolved: Dict[NodeKey, Set[NodeKey]] = {}
    for node, callee_names in parser.calls.items():
        targets: Set[NodeKey] = set()
        for name in callee_names:
            matches = parser.nodes_by_name.get(name)
            targets.update(matches if matches else {(name, STDLIB_HEADERS.get(name, ""))})
        resolved[node] = targets

    changed = True
    while changed:
        changed = False
        for callees in list(resolved.values()):
            for callee in callees:
                if callee not in resolved:
                    resolved[callee] = set()
                    changed = True

    return CallGraph(calls=resolved, defined=defined)


def _format_node(node: NodeKey, show_files: bool) -> str:
    name, file = node
    if show_files and file:
        return f"{name}({file})"
    return name


def print_tree(graph: CallGraph, start: NodeKey, max_depth: int = 5, show_files: bool = False) -> None:
    def walk(node: NodeKey, depth: int, ancestors: Set[NodeKey]) -> None:
        print(f"{'\t' * depth}{_format_node(node, show_files)}")
        if depth >= max_depth:
            return
        for callee in sorted(graph.calls.get(node, set())):
            if callee in ancestors:
                continue
            walk(callee, depth + 1, ancestors | {callee})

    walk(start, 0, {start})


def _dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _dot_node_id(node: NodeKey) -> str:
    name, file = node
    return f'"{_dot_escape(name + "|" + file)}"'


def collect_dot_graph(
    graph: CallGraph, starts: List[NodeKey], max_depth: int = 5
) -> Tuple[Set[NodeKey], Set[Tuple[NodeKey, NodeKey]]]:
    nodes: Set[NodeKey] = set()
    edges: Set[Tuple[NodeKey, NodeKey]] = set()

    def walk(node: NodeKey, depth: int, ancestors: Set[NodeKey]) -> None:
        nodes.add(node)
        if depth >= max_depth:
            return
        for callee in graph.calls.get(node, set()):
            edges.add((node, callee))
            if callee in ancestors:
                continue
            walk(callee, depth + 1, ancestors | {callee})

    for start in starts:
        walk(start, 0, {start})
    return nodes, edges


def format_dot(
    nodes: Set[NodeKey], edges: Set[Tuple[NodeKey, NodeKey]], show_files: bool = False
) -> str:
    lines = ["digraph callgraph {"]
    for node in sorted(nodes):
        label = _dot_escape(_format_node(node, show_files).replace("(", "\\n(", 1))
        lines.append(f'    {_dot_node_id(node)} [label="{label}"];')
    for caller, callee in sorted(edges):
        lines.append(f"    {_dot_node_id(caller)} -> {_dot_node_id(callee)};")
    lines.append("}")
    return "\n".join(lines)


def _drawio_layout(
    nodes: Set[NodeKey], edges: Set[Tuple[NodeKey, NodeKey]], show_files: bool
) -> Dict[NodeKey, Tuple[float, float, float, float]]:
    """Compute (x, y, w, h) box positions with grandalf's pure-Python Sugiyama layout."""
    try:
        from grandalf.graphs import Edge as GEdge
        from grandalf.graphs import Graph as GGraph
        from grandalf.graphs import Vertex
        from grandalf.layouts import SugiyamaLayout
    except ImportError as exc:
        raise SystemExit(
            "--drawio requires the 'grandalf' package for graph layout: pip install grandalf"
        ) from exc

    class _View:
        def __init__(self, w: float, h: float) -> None:
            self.w = w
            self.h = h

    vertices: Dict[NodeKey, Vertex] = {}
    for node in nodes:
        name, file = node
        label_lines = [name] + ([file] if show_files and file else [])
        width = max(80.0, max(len(line) for line in label_lines) * 7.0 + 20.0)
        height = 30.0 if len(label_lines) == 1 else 46.0
        vertex = Vertex(node)
        vertex.view = _View(width, height)
        vertices[node] = vertex

    gedges = [GEdge(vertices[a], vertices[b]) for a, b in edges if a in vertices and b in vertices]
    root = GGraph(list(vertices.values()), gedges)

    positions: Dict[NodeKey, Tuple[float, float, float, float]] = {}
    y_offset = 0.0
    for component in root.C:
        sug = SugiyamaLayout(component)
        sug.init_all()
        sug.draw()
        max_bottom = y_offset
        for vertex in component.sV:
            x, y = vertex.view.xy
            top = y + y_offset
            positions[vertex.data] = (x, top, vertex.view.w, vertex.view.h)
            max_bottom = max(max_bottom, top + vertex.view.h)
        y_offset = max_bottom + 60.0

    return positions


def format_drawio(
    nodes: Set[NodeKey], edges: Set[Tuple[NodeKey, NodeKey]], show_files: bool = False
) -> str:
    from xml.sax.saxutils import escape

    positions = _drawio_layout(nodes, edges, show_files)
    min_x = min((x - w / 2 for x, _y, w, _h in positions.values()), default=0.0)
    min_y = min((y for _x, y, _w, _h in positions.values()), default=0.0)
    node_ids = {node: f"n{i}" for i, node in enumerate(sorted(positions))}

    lines = [
        '<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="850" pageHeight="1100" math="0" shadow="0">',
        "  <root>",
        '    <mxCell id="0" />',
        '    <mxCell id="1" parent="0" />',
    ]

    for node, (x, y, w, h) in positions.items():
        name, file = node
        if show_files and file:
            value = f"{escape(name)}&lt;br&gt;{escape(file)}"
        else:
            value = escape(name)
        cell_id = node_ids[node]
        lines.append(
            f'    <mxCell id="{cell_id}" value="{value}" '
            'style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">'
        )
        lines.append(
            f'      <mxGeometry x="{x - w / 2 - min_x + 40:.1f}" y="{y - min_y + 40:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" as="geometry" />'
        )
        lines.append("    </mxCell>")

    for i, (a, b) in enumerate(sorted(edges)):
        if a not in node_ids or b not in node_ids:
            continue
        lines.append(
            f'    <mxCell id="e{i}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" '
            f'edge="1" parent="1" source="{node_ids[a]}" target="{node_ids[b]}">'
        )
        lines.append('      <mxGeometry relative="1" as="geometry" />')
        lines.append("    </mxCell>")

    lines.append("  </root>")
    lines.append("</mxGraphModel>")
    return "\n".join(lines)


def _parse_start(value: str) -> Tuple[str, str | None]:
    match = re.match(r"^(.*)\((.*)\)$", value)
    if match:
        return match.group(1), match.group(2)
    return value, None


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract simple call trees from C source files")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument(
        "--start",
        help="Function name to start from. If omitted, all files are scanned "
        "and a call tree is printed for every function found. If the name "
        "was defined in more than one file, a separate tree is printed per "
        "definition unless narrowed down with 'name(path)', e.g. "
        "'main(unix/plink.c)' -- the path is matched as a substring, so a "
        "partial path is enough as long as it is unambiguous",
    )
    parser.add_argument("--max-depth", type=int, default=5, help="Maximum depth of call chains")
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Show the defining file after each function name, e.g. main(/path/main.c)",
    )
    parser.add_argument(
        "--dot",
        metavar="PATH",
        help="Write a Graphviz DOT file of the call graph to PATH instead of "
        "printing a tree. Render it with e.g. 'dot -Tsvg PATH -o graph.svg', "
        "or import it directly into draw.io (Extras > Edit Diagram)",
    )
    parser.add_argument(
        "--drawio",
        metavar="PATH",
        help="Write a draw.io (mxGraph XML) file of the call graph to PATH "
        "instead of printing a tree. Uses a pure-Python layered layout "
        "(via the 'grandalf' package: pip install grandalf), no Graphviz "
        "install required. Open the file directly in draw.io. The layout "
        "gets slow beyond roughly a thousand nodes, so narrow the graph "
        "with --start/--max-depth for large codebases",
    )
    args = parser.parse_args(argv)

    root_paths = [Path(p) for p in args.paths]
    graph = build_call_graph(root_paths)

    if args.start:
        name, file_pattern = _parse_start(args.start)
        if file_pattern is not None:
            file_pattern = file_pattern.replace("\\", "/")
        starts = sorted(
            node
            for node in graph.calls
            if node[0] == name
            and (file_pattern is None or file_pattern in node[1].replace("\\", "/"))
        )
        if not starts:
            print(f"Unknown function: {args.start}")
            return 0
    else:
        starts = sorted(graph.defined)
        if not starts:
            print("No functions found")
            return 0

    if args.dot:
        nodes, edges = collect_dot_graph(graph, starts, max_depth=args.max_depth)
        Path(args.dot).write_text(format_dot(nodes, edges, show_files=args.show_files), encoding="utf-8")
        print(f"Wrote {len(nodes)} nodes and {len(edges)} edges to {args.dot}")
        return 0

    if args.drawio:
        nodes, edges = collect_dot_graph(graph, starts, max_depth=args.max_depth)
        Path(args.drawio).write_text(
            format_drawio(nodes, edges, show_files=args.show_files), encoding="utf-8"
        )
        print(f"Wrote {len(nodes)} nodes and {len(edges)} edges to {args.drawio}")
        return 0

    for i, start in enumerate(starts):
        if i:
            print()
        print_tree(graph, start, max_depth=args.max_depth, show_files=args.show_files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
