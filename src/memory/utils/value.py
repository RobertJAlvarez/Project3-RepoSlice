from enum import Enum
import re
from typing import Optional, Set, TYPE_CHECKING

from utility.errors import RAValueError

if TYPE_CHECKING:
    from memory.utils.function import Function


class ValueLabel(Enum):
    """Enumeration of possible value labels in the program.

    These labels indicate the role and usage context of values in the code.
    Labels are grouped by category for better organization.
    """

    # Group 1: Value types used in the dfbscan agent
    SRC = 1  # Source value that provides data
    SINK = 2  # Sink value that consumes data

    # Group 2: General value types used for inter-procedural analysis
    ## Parameter types
    PARA = 3  # Regular function parameter
    VARI_PARA = 4  # Variadic parameter (*args)
    OBJ_PARA = 5  # Object/self parameter

    ## Argument types
    ARG = 6  # Regular function argument
    OBJ_ARG = 7  # Object/receiver argument

    ## Return/output types
    RET = 8  # Function return value
    OUT = 9  # Function output value (call expression)

    # Group 3: Expression types
    BUF_ACCESS_EXPR = 10  # Buffer access expression
    NON_BUF_ACCESS_EXPR = 11  # Non-buffer access expression
    CONSTANT = 12  # Literal/constant value
    DECLARATION = 13  # Variable/function declaration

    ## Group 4: Scope types
    LOCAL = 14  # Local variable scope
    GLOBAL = 15  # Global variable scope

    def __str__(self) -> str:
        """Convert label to string representation.

        Returns:
            String representation of the label enum value
        """
        mapping = {
            ValueLabel.SRC: "ValueLabel.SRC",
            ValueLabel.SINK: "ValueLabel.SINK",
            ValueLabel.PARA: "ValueLabel.PARA",
            ValueLabel.VARI_PARA: "ValueLabel.VARI_PARA",
            ValueLabel.OBJ_PARA: "ValueLabel.OBJ_PARA",
            ValueLabel.ARG: "ValueLabel.ARG",
            ValueLabel.OBJ_ARG: "ValueLabel.OBJ_ARG",
            ValueLabel.RET: "ValueLabel.RET",
            ValueLabel.OUT: "ValueLabel.OUT",
            ValueLabel.BUF_ACCESS_EXPR: "ValueLabel.BUF_ACCESS_EXPR",
            ValueLabel.NON_BUF_ACCESS_EXPR: "ValueLabel.NON_BUF_ACCESS_EXPR",
            ValueLabel.CONSTANT: "ValueLabel.CONSTANT",
            ValueLabel.DECLARATION: "ValueLabel.DECLARATION",
            ValueLabel.LOCAL: "ValueLabel.LOCAL",
            ValueLabel.GLOBAL: "ValueLabel.GLOBAL",
        }
        return mapping[self]

    def is_para(self) -> bool:
        """Check if label represents a parameter type.

        Returns:
            True if label is a parameter type, False otherwise
        """
        return self in {ValueLabel.PARA, ValueLabel.VARI_PARA, ValueLabel.OBJ_PARA}

    def is_arg(self) -> bool:
        """Check if label represents an argument type.

        Returns:
            True if label is an argument type, False otherwise
        """
        return self in {ValueLabel.ARG, ValueLabel.OBJ_ARG}

    @staticmethod
    def from_str(label_str: str) -> "ValueLabel":
        """Convert string to ValueLabel enum.

        Args:
            label_str: String representation of label

        Returns:
            Corresponding ValueLabel enum value

        Raises:
            RAValueError: If string does not match a valid label
        """
        mapping = {
            "ValueLabel.SRC": ValueLabel.SRC,
            "ValueLabel.SINK": ValueLabel.SINK,
            "ValueLabel.PARA": ValueLabel.PARA,
            "ValueLabel.VARI_PARA": ValueLabel.VARI_PARA,
            "ValueLabel.OBJ_PARA": ValueLabel.OBJ_PARA,
            "ValueLabel.ARG": ValueLabel.ARG,
            "ValueLabel.OBJ_ARG": ValueLabel.OBJ_ARG,
            "ValueLabel.RET": ValueLabel.RET,
            "ValueLabel.OUT": ValueLabel.OUT,
            "ValueLabel.BUF_ACCESS_EXPR": ValueLabel.BUF_ACCESS_EXPR,
            "ValueLabel.NON_BUF_ACCESS_EXPR": ValueLabel.NON_BUF_ACCESS_EXPR,
            "ValueLabel.CONSTANT": ValueLabel.CONSTANT,
            "ValueLabel.DECLARATION": ValueLabel.DECLARATION,
            "ValueLabel.LOCAL": ValueLabel.LOCAL,
            "ValueLabel.GLOBAL": ValueLabel.GLOBAL,
        }
        try:
            return mapping[label_str]
        except KeyError:
            raise RAValueError(f"Invalid label: {label_str}")


class Value:
    """Represents a value in the program with its metadata and context.

    A Value object tracks information about variables, parameters, expressions and other
    program elements including their type, location, and usage context.
    """

    def __init__(
        self,
        name: str,
        label: ValueLabel,
        file_path: str,
        line_number_in_file: int,
        function_id: int = -1,
        function_name: Optional[str] = None,
        line_number_in_function: int = -1,
        index: int = -1,
        comment: Optional[str] = None,
    ) -> None:
        """Initialize a Value object.

        Args:
            name: Variable/parameter name or expression string
            label: Type/role of the value
            file_path: Source file path
            line_number_in_file: Line number in source file
            function_id: Function ID (-1 for globals)
            function_name: Function name (None for globals)
            line_number_in_function: Line number in function (-1 for globals)
            index: Parameter/argument index (-1 if not applicable)
            comment: Optional descriptive comment
        """
        self.name = name
        self.label = label
        self.file_path = file_path
        self.line_number_in_file = line_number_in_file
        self.function_id = function_id
        self.function_name = function_name
        self.line_number_in_function = line_number_in_function
        self.index = index
        self.comment = comment

    def __str__(self) -> str:
        """Generate string representation of the value.

        Returns:
            String containing all value attributes in readable format
        """
        return (
            f"({self.name}, {self.label}, {self.file_path}, "
            f"{self.line_number_in_file}, {self.function_id}, "
            f"{self.function_name}, {self.line_number_in_function}, "
            f"{self.index}, {self.comment})"
        )

    def __eq__(self, other: object) -> bool:
        """Compare equality with another Value object.

        Args:
            other: Object to compare with

        Returns:
            True if values are equal, False otherwise
        """
        if not isinstance(other, Value):
            return NotImplemented
        return str(self) == str(other)

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Returns:
            String representation of the value
        """
        return self.__str__()

    def __hash__(self) -> int:
        """Generate hash value for use in sets/dicts.

        Returns:
            Hash of the string representation
        """
        return hash(str(self))

    def description(self) -> str:
        """Generate human-readable description of the value.

        Returns:
            Descriptive string including value type, name, location and context

        Raises:
            RAValueError: If value has invalid label
        """
        type_mapping = {
            ValueLabel.SRC: "source",
            ValueLabel.SINK: "sink",
            ValueLabel.PARA: "parameter",
            ValueLabel.VARI_PARA: "element of the variadic parameter",
            ValueLabel.OBJ_PARA: "object parameter",
            ValueLabel.ARG: "argument",
            ValueLabel.OBJ_ARG: "receiver object argument",
            ValueLabel.RET: "return value",
            ValueLabel.OUT: "output value of the call expression",
            ValueLabel.BUF_ACCESS_EXPR: "buffer access expression",
            ValueLabel.NON_BUF_ACCESS_EXPR: "non-buffer access expression",
            ValueLabel.CONSTANT: "constant value",
            ValueLabel.DECLARATION: "declared variable",
            ValueLabel.LOCAL: "local variable",
            ValueLabel.GLOBAL: "global variable",
        }

        type_desc = type_mapping.get(self.label)
        if type_desc is None:
            raise RAValueError(f"Invalid label: {self.label}")

        if self.index != -1:
            ordinal = (
                lambda n: f"{n+1}{'st' if n%10==0 else 'nd' if n%10==1 else 'rd' if n%10==2 else 'th'}"
            )
            index_desc = ordinal(self.index)
            desc = f"{index_desc} {type_desc} `{self.name}` (at index {self.index})"
        else:
            desc = f"the {type_desc} `{self.name}`"

        if self.function_name and self.line_number_in_function != -1:
            desc += f" at line {self.line_number_in_function} of this function `{self.function_name}`"

        if self.comment:
            desc += f" (comment: {self.comment})"

        return desc

    def to_dict(self) -> dict:
        """Convert Value object to dictionary representation.

        Returns:
            Dictionary containing value metadata
        """
        return {
            "name": self.name,
            "label": str(self.label),
            "file_path": self.file_path,
            "line_number_in_file": self.line_number_in_file,
            "function_id": self.function_id,
            "function_name": self.function_name,
            "line_number_in_function": self.line_number_in_function,
            "index": self.index,
            "comment": self.comment,
        }
