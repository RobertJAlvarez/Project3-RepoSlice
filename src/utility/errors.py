class RepoSliceError(Exception):
    """Base class for all errors related to RepoSlice."""

    pass


class RARequestError(RepoSliceError):
    """Exception raised for request errors in RepoSlice."""

    pass


class RAValueError(RepoSliceError, ValueError):
    """Exception raised for value errors in RepoSlice."""

    pass


class RATypeError(RepoSliceError, TypeError):
    """Exception raised for type errors in RepoSlice."""

    pass


class RAAnalysisError(RepoSliceError):
    """Exception raised for analysis errors in RepoSlice."""

    pass


class RALLMAPIError(RepoSliceError):
    """Exception raised for API-related errors in RepoSlice."""

    pass
