import tree_sitter


class API:
    """Class representing a library API function with its metadata."""

    def __init__(
        self,
        api_id: int,
        api_name: str,
        api_para_num: int,
    ) -> None:
        """Initialize an API object with basic metadata.

        Args:
            api_id: Unique identifier for the API
            api_name: Name of the API function
            api_para_num: Number of parameters the API function accepts
        """
        self.api_id = api_id
        self.api_name = api_name
        self.api_para_num = api_para_num

    def __str__(self) -> str:
        """Generate string representation of the API.

        Returns:
            String containing API metadata in a readable format
        """
        return f"API(api_id={self.api_id}, api_name='{self.api_name}', api_para_num={self.api_para_num})"

    def __eq__(self, other: object) -> bool:
        """Check equality between two API objects.

        Two APIs are considered equal if they have the same name and parameter count.

        Args:
            other: Object to compare with

        Returns:
            True if APIs are equal, False otherwise
        """
        if not isinstance(other, API):
            return NotImplemented
        return (
            self.api_name == other.api_name and self.api_para_num == other.api_para_num
        )

    def __hash__(self) -> int:
        """Generate hash value for the API.

        Returns:
            Hash based on API name and parameter count
        """
        return hash((self.api_name, self.api_para_num))

    def to_dict(self) -> dict:
        """Convert API object to dictionary representation.

        Returns:
            Dictionary containing API metadata
        """
        return {
            "api_id": self.api_id,
            "api_name": self.api_name,
            "api_para_num": self.api_para_num,
        }
