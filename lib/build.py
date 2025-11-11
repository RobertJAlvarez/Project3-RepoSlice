import os

from tree_sitter import Language, Parser
from pathlib import Path

cwd = Path(__file__).resolve().parent.absolute()

# clone tree-sitter if necessary
if not (cwd / "vendor/tree-sitter-c/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-c.git {cwd / "vendor/tree-sitter-c"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-c"} && git checkout cd44a2b1364d26d80daa208d3caf659a4c4e953d'
    )

if not (cwd / "vendor/tree-sitter-cpp/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-cpp.git {cwd / "vendor/tree-sitter-cpp"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-cpp"} && git checkout 12bd6f7e96080d2e70ec51d4068f2f66120dde35'
    )

Language.build_library(
    # Store the library in the `build` directory
    str(cwd / "build/my-languages.so"),
    
    # Include one or more languages
    [
        str(cwd / "vendor/tree-sitter-c"),
        str(cwd / "vendor/tree-sitter-cpp")
    ],
)