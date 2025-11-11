from abc import ABC, abstractmethod
from threading import Lock
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Generic,
    get_args,
    get_origin,
)

from llmtool.LLM_utils import LLM
from utility.logger import Logger


class LLMToolInput(ABC):
    """Abstract base class for LLM tool inputs."""

    def __init__(self):
        """Initialize LLM tool input."""
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Generate hash for input."""
        pass

    def __eq__(self, value) -> bool:
        """Compare inputs based on hash."""
        return self.__hash__() == value.__hash__()


class LLMToolOutput(ABC):
    """Abstract base class for LLM tool outputs."""

    def __init__(self):
        """Initialize LLM tool output."""
        pass


TInput = TypeVar("TInput", bound=LLMToolInput)
TOutput = TypeVar("TOutput", bound=LLMToolOutput)

# Keep old TypeVar for backwards compatibility
T = TypeVar("T", bound=LLMToolOutput)


class LLMTool(Generic[TInput, TOutput], ABC):
    """Abstract base class for LLM-based tools."""

    def __init__(
        self,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        """Initialize LLM tool.

        Args:
            model_name: Name of LLM model to use
            temperature: Temperature parameter for LLM sampling
            language: Programming language being analyzed
            max_query_num: Maximum number of LLM queries allowed for re-tries
            logger: Logger instance for tracking
        """
        self.model_name = model_name
        self.temperature = temperature
        self.language = language
        self.max_query_num = max_query_num
        self.logger = logger

        self.model = LLM(model_name, temperature)
        self.cache: Dict[TInput, TOutput] = {}

        self.input_token_cost = 0
        self.output_token_cost = 0
        self.total_query_num = 0
        self.lock = Lock()

        # Extract input and output types from Generic parameters
        self._input_type, self._output_type = self._get_instance_generic_types()

    @classmethod
    def get_input_type(cls) -> Type[TInput]:
        """Get the input type for this LLMTool class.

        Returns:
            The input type specified in Generic[TInput, TOutput]
        """
        return cls._get_generic_types()[0]

    @classmethod
    def get_output_type(cls) -> Type[TOutput]:
        """Get the output type for this LLMTool class.

        Returns:
            The output type specified in Generic[TInput, TOutput]
        """
        return cls._get_generic_types()[1]

    @classmethod
    def _get_generic_types(cls) -> Tuple[Type[TInput], Type[TOutput]]:
        """Automatically extract Input/Output types from Generic parameters."""
        orig_bases = getattr(cls, "__orig_bases__", ())
        for base in orig_bases:
            if get_origin(base) is LLMTool:
                args = get_args(base)
                if len(args) == 2:
                    return args[0], args[1]  # type: ignore
        raise TypeError(
            f"{cls} must specify Input and Output types in Generic[TInput, TOutput]"
        )

    def _get_instance_generic_types(self) -> Tuple[Type[TInput], Type[TOutput]]:
        """Instance method wrapper for getting generic types."""
        return self.__class__._get_generic_types()

    def invoke(self, input: TInput) -> Optional[TOutput]:
        """Type-safe invoke method - no manual type specification needed.

        Args:
            input: Input for the LLM tool (type is enforced by Generic)

        Returns:
            Processed output of correct type or None if failed

        Raises:
            TypeError: If input type doesn't match expected type
        """
        # Automatic type validation
        if not isinstance(input, self._input_type):
            raise TypeError(
                f"Expected input of type {self._input_type}, but got {type(input)}"
            )

        log_strs = []
        log_strs.append("\n")
        log_strs.append("================================================")
        log_strs.append("LLM Tool Log starts...")
        log_strs.append("================================================")

        output, log_strs = self._invoke(input, log_strs)

        log_strs.append("================================================")
        log_strs.append("LLM Tool Log ends...")
        log_strs.append("================================================")
        log_strs.append("\n")

        self.logger.print_log("\n".join(log_strs))

        if output is not None and not isinstance(output, self._output_type):
            raise TypeError(
                f"Expected output of type {self._output_type}, but got {type(output)}"
            )

        return output

    def _invoke(
        self, input: TInput, log_strs: List[str]
    ) -> Tuple[Optional[TOutput], List[str]]:
        """Type-safe internal invoke implementation.

        Args:
            input: Input for the LLM tool (type-safe)
            log_strs: List of log strings to append to

        Returns:
            Tuple of (processed output, updated log strings)
        """
        class_name = type(self).__name__
        log_strs.append(f"The LLM Tool {class_name} is invoked.")
        if input in self.cache:
            log_strs.append("Cache hit.")
            return self.cache[input], log_strs

        prompt = self._get_prompt(input)
        log_strs.append("------------------------------------------------")
        log_strs.append("Prompt:")
        log_strs.append("------------------------------------------------")
        log_strs.append(prompt)
        log_strs.append("------------------------------------------------")

        single_query_num = 0
        output = None
        while True:
            if single_query_num > self.max_query_num:
                break
            single_query_num += 1
            response, input_token_cost, output_token_cost, log_strs = self.model.infer(
                prompt, True, log_strs
            )
            log_strs.append("------------------------------------------------")
            log_strs.append("Response:")
            log_strs.append("------------------------------------------------")
            log_strs.append(response)
            log_strs.append("------------------------------------------------")

            self.input_token_cost += input_token_cost
            self.output_token_cost += output_token_cost
            output = self._parse_response(response, input)

            if output is not None:
                break

        log_strs.append("------------------------------------------------")
        log_strs.append("Output:")
        log_strs.append("------------------------------------------------")
        log_strs.append(str(output))
        log_strs.append("------------------------------------------------")

        self.total_query_num += single_query_num
        if output is not None:
            self.cache[input] = output
        return output, log_strs

    @abstractmethod
    def _get_prompt(self, input: TInput) -> str:
        """Type-safe generate prompt for LLM from input.

        Args:
            input: Input to generate prompt from (type-safe)

        Returns:
            Generated prompt string
        """
        pass

    @abstractmethod
    def _parse_response(self, response: str, input: TInput) -> Optional[TOutput]:
        """Type-safe parse LLM response into output.

        Args:
            response: Raw response from LLM
            input: Original input for context (type-safe)

        Returns:
            Parsed output or None if parsing fails (type-safe)
        """
        pass
