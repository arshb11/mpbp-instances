import ast

def convert_json_to_data(obj) -> dict:
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
    
def data_preprocessing(d: dict) -> dict:
    """
    Preprocesses data to add additional sets and parameters
    
    Arguments
    ---------
        d : dict
            Data Dictionary
    Returns
    -------
        d: dict
            Data Dictionary after preprocessing

    """

    d['N'] = d['S'] + d['B'] + d['D']  

    # Nodes coming in and out
    Nin = dict()
    Nout = dict()
    for n in d['N']:
        an_in = list()
        an_out = list()
        for a in d['A']:
            if n == a[0]:
                an_out.append(a[1])
            elif n == a[1]:
                an_in.append(a[0])
        Nin[n] = an_in
        Nout[n] = an_out

    d['Nin'] = Nin
    d['Nout'] = Nout

    # Set preprocessing
    NB, BN, SD, BD = [], [], [], []
    for (nin, nout) in d['A']:
        if nout in d['B']:
            NB.append((nin,nout))
        if nin in d['B']:
            BN.append((nin,nout))
            if nout in d['D']:
                BD.append((nin,nout))
        if nin in d['S'] and nout in d['D']:
            SD.append((nin, nout))

    d['NB'] = NB
    d['BN'] = BN
    d['SD'] = SD
    d['BD'] = BD

    # Redundant Constraint set and parameter generation
    B_hat = []
    R = d['S']

    for b in d['B']:
        if d['I0'][b] != 0:
            B_hat.append(b)

    C0_hat = d['CIN'].copy()     
    for q in d['Q']:
        for b in B_hat:
            C0_hat[q,b] = d['C0'][q,b]

    R = R + B_hat

    d['R'] = R
    d['B_hat'] = B_hat
    d['C0_hat'] = C0_hat

    return d
