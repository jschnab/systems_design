from typing import Optional


def check_config(cnf: dict) -> None:
    """
    Checks if the given configuration is valid by ensuring all configuration
    keys have a non-null value.

    Args:
        cnf (dict): Configuration to validate.

    Returns:
        None

    Raises:
        ValueError: If any configuration value is `None`.
    """
    stack: list[tuple[dict, Optional[str]]] = [(cnf, None)]
    null_values = []
    while stack != []:
        cur, parent = stack.pop()
        for k, v in cur.items():
            full_key = f"{parent + '.' if parent is not None else ''}{k}"
            if isinstance(v, dict):
                stack.append((v, full_key))
            else:
                if v is None:
                    null_values.append(full_key)
    if null_values != []:
        raise ValueError(
            f"The following values should not be None: "
            f"{', '.join(null_values)}"
        )
