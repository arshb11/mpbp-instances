import ast

def convert_json_to_data(obj):
    """
    Recursively convert JSON-like structure back to original Python structure:
    - List values become tuples
    - String keys that represent tuples become tuple keys
    - Handles nested dictionaries and lists
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            # Try to convert string keys that look like tuples back to tuple keys
            if isinstance(key, str) and key.startswith("(") and key.endswith(")"):
                try:
                    parsed_key = ast.literal_eval(key)
                    if isinstance(parsed_key, tuple):
                        new_key = parsed_key
                    else:
                        new_key = key
                except (ValueError, SyntaxError):
                    new_key = key
            else:
                new_key = key
            result[new_key] = convert_json_to_data(value)
        return result
    elif isinstance(obj, list):
        # Convert list back to tuple (assuming all tuples were converted to lists)
        return tuple(convert_json_to_data(item) for item in obj)
    else:
        return obj
