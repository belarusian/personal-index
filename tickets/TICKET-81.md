# TICKET-81: Type error — `APIResponse.to_dict()` assigns generic `T` to `bool`-typed dict keys

## Title
`APIResponse.to_dict()` has incompatible type assignments — mypy infers `result` keys as `bool` from `{"success": self.success}`

## Evidence
mypy flags 5 errors in `personal_index/api/models.py`:

1. Line 26: `result["data"] = self.data` — expression has type `T`, target has type `bool`
2. Line 28: `result["data"] = self.data` — expression has type `T`, target has type `bool`
3. Line 30: `result["error"] = self.error` — expression has type `str`, target has type `bool`
4. Line 32: `result["message"] = self.message` — expression has type `str`, target has type `bool`
5. Line 34: `result["meta"] = self.meta` — expression has type `dict[str, Any]`, target has type `bool`
