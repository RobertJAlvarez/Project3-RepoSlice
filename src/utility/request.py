from pathlib import Path
from utility.errors import RARequestError


class SliceRequest:
    """Represents a request for program slicing with seed information.

    This class encapsulates all necessary information to perform program slicing:
    - Project path: The project path containing the source file
    - File path: The source file containing the seed
    - Seed line number: The line number where slicing should start
    - Seed name: The variable/expression name to slice from
    - Is backward: Whether to perform backward slicing (True) or forward slicing (False)
    """

    def __init__(
        self,
        slicing_request_id: str,
        project_path: str,
        file_path: str,
        seed_line_number: int,
        seed_name: str,
        is_backward: bool = True,
    ) -> None:
        """Initialize a SliceRequest object.

        Args:
            slicing_request_id: The ID of the slicing request
            project_path: Path to the project containing the source file
            file_path: Path to the source file containing the slicing seed
            seed_line_number: Line number of the slicing seed in the file
            seed_name: Variable or expression of the slicing seed
            is_backward: Perform backward slicing if True; forward slicing if False (default: True)

        Raises:
            RARequestError: If any parameter validation fails
        """
        self._validate_parameters(project_path, file_path, seed_line_number, seed_name)

        self.slicing_request_id = slicing_request_id
        self.project_path = project_path.strip()
        self.file_path = file_path.strip()
        self.seed_line_number = seed_line_number
        self.seed_name = seed_name.strip()
        self.is_backward = is_backward

    def _validate_parameters(
        self,
        project_path: str,
        file_path: str,
        seed_line_number: int,
        seed_name: str,
    ) -> None:
        """Validate the input parameters for SliceRequest.

        Args:
            project_path: The project path to validate
            file_path: The file path to validate
            seed_line_number: The seed line number to validate
            seed_name: The seed name to validate

        Raises:
            RARequestError: If any parameter is invalid
        """
        if not isinstance(project_path, str) or not project_path.strip():
            raise RARequestError("project_path must be a non-empty string")

        if not Path(project_path).exists():
            raise RARequestError("project_path does not exist")

        if not isinstance(file_path, str) or not file_path.strip():
            raise RARequestError("file_path must be a non-empty string")

        if not Path(file_path).exists():
            raise RARequestError("file_path does not exist")

        # Check whether file_path is inside project_path as a directory
        project_full_path = Path(project_path).resolve()
        file_full_path = Path(file_path).resolve()
        try:
            file_full_path.relative_to(project_full_path)
        except ValueError:
            raise RARequestError("file_path must be inside project_path")

        if not isinstance(seed_line_number, int) or seed_line_number < 1:
            raise RARequestError("seed_line_number must be a positive integer")

        if not isinstance(seed_name, str) or not seed_name.strip():
            raise RARequestError("seed_name must be a non-empty string")

    def __str__(self) -> str:
        """Generate string representation of the slice request.

        Returns:
            String containing all request attributes in readable format
        """
        return (
            f"SliceRequest(slicing_request_id='{self.slicing_request_id}', "
            f"project_path='{self.project_path}', "
            f"file_path='{self.file_path}', "
            f"seed_line_number={self.seed_line_number}, "
            f"seed_name='{self.seed_name}', "
            f"is_backward={self.is_backward})"
        )

    def __eq__(self, other: object) -> bool:
        """Compare equality with another SliceRequest object.

        Args:
            other: Object to compare with

        Returns:
            True if requests are equal, False otherwise
        """
        if not isinstance(other, SliceRequest):
            return NotImplemented
        return (
            self.slicing_request_id == other.slicing_request_id
            and self.seed_line_number == other.seed_line_number
            and self.seed_name == other.seed_name
            and self.file_path == other.file_path
            and self.is_backward == other.is_backward
        )

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Returns:
            String representation of the slice request
        """
        return self.__str__()

    def __hash__(self) -> int:
        """Generate hash value for use in sets/dicts.

        Returns:
            Hash of the request attributes
        """
        return hash(
            (
                self.slicing_request_id,
                self.seed_line_number,
                self.seed_name,
                self.file_path,
                self.is_backward,
            )
        )

    def to_dict(self) -> dict:
        """Convert SliceRequest object to dictionary representation.

        Returns:
            Dictionary containing slice request metadata
        """
        return {
            "slicing_request_id": self.slicing_request_id,
            "seed_line_number": self.seed_line_number,
            "seed_name": self.seed_name,
            "file_path": self.file_path,
            "is_backward": self.is_backward,
        }

    def description(self) -> str:
        """Generate human-readable description of the slice request.

        Returns:
            Descriptive string about the slice request
        """
        slice_type = "backward" if self.is_backward else "forward"
        desc = (
            f"{slice_type.capitalize()} slice request for variable '{self.seed_name}' "
            f"at line {self.seed_line_number} in file '{self.file_path}' "
        )

        return desc

    @classmethod
    def from_dict(cls, data: dict) -> "SliceRequest":
        """Create SliceRequest from dictionary representation.

        Args:
            data: Dictionary containing slice request data

        Returns:
            SliceRequest object created from dictionary

        Raises:
            RARequestError: If required keys are missing or invalid
        """
        required_keys = {
            "slicing_request_id",
            "seed_line_number",
            "seed_name",
            "file_path",
        }
        missing_keys = required_keys - set(data.keys())

        if missing_keys:
            raise RARequestError(f"Missing required keys: {missing_keys}")

        BASE_PATH = Path(__file__).resolve().parents[2]

        return cls(
            slicing_request_id=data["slicing_request_id"],
            project_path=str(Path(BASE_PATH) / Path(data["project_path"])),
            file_path=str(Path(BASE_PATH) / Path(data["file_path"])),
            seed_line_number=data["seed_line_number"],
            seed_name=data["seed_name"],
            is_backward=data.get("is_backward", True),
        )
