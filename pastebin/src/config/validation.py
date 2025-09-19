def check_config(cnf):
    stack = [(cnf, None)]
    null_values = []
    while stack != []:
        cur, parent = stack.pop()
        for k, v in cur.items():
            if isinstance(v, dict):
                stack.append(
                    (v, f"{parent + '.' if parent is not None else ''}{k}")
                )
            else:
                full_key = f"{parent}.{k}"
                if v is None:
                    null_values.append(full_key)
    if null_values != []:
        raise ValueError(
            f"The following values should not be None: "
            f"{', '.join(null_values)}"
        )
