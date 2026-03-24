def deep_merge(dict1, dict2):
    """
    Deep merges two dictionaries.
    If a key exists in both dictionaries, the value from dict2 will be applied.
    If both values are lists, they will be concatenated.
    If a key exists in both and the values are dictionaries, a recursive merge will occur.
    """
    for key, value in dict2.items():
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(value, dict):
                dict1[key] = deep_merge(dict1[key], value)
            elif isinstance(dict1[key], list) and isinstance(value, list):
                dict1[key].extend(value)
            else:
                dict1[key] = value
        else:
            dict1[key] = value
    return dict1


def load_yaml_file(file_path):
    """
    Loads a YAML file and returns its content.
    Uses safe_load to prevent the execution of arbitrary code.
    """
    import yaml
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def update_context(overlay_paths=None):
    if overlay_paths is not None:
        for path in overlay_paths:
            # Load and merge logic here...
            pass
    # Existing behavior here...