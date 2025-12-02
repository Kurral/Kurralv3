"""
Tools for Level 1 Agent
These tools have intentional errors for demonstration purposes.
"""

def get_full_form(short_form: str) -> str:
    """
    Converts short form to full form.
    Has intentional spelling mistakes to demonstrate tool usage.
    
    Args:
        short_form: The short form abbreviation
        
    Returns:
        Full form with intentional spelling mistakes
    """
    print("\n[TOOL INVOKED] get_full_form()")
    print(f"   Input: {short_form}")
    
    # Dictionary with short forms and full forms (with intentional spelling mistakes)
    short_forms_dict = {
        "AI": "Artifical Inteligence",  # Should be "Artificial Intelligence"
        "ML": "Machine Lerning",  # Should be "Machine Learning"
        "API": "Application Programing Interface",  # Should be "Programming"
        "HTTP": "HyperText Transfer Protocal",  # Should be "Protocol"
        "URL": "Uniform Resource Locator",  # This one is correct
        "CPU": "Central Procesing Unit",  # Should be "Processing"
        "GPU": "Graphics Procesing Unit",  # Should be "Processing"
        "RAM": "Random Acess Memory",  # Should be "Access"
        "SQL": "Structured Query Langauge",  # Should be "Language"
        "JSON": "JavaScript Object Notaion",  # Should be "Notation"
        "XML": "Extensible Markup Langauge",  # Should be "Language"
        "HTML": "HyperText Markup Langauge",  # Should be "Language"
        "CSS": "Cascading Style Sheet",  # This one is correct
        "JS": "JavaScrit",  # Should be "JavaScript"
        "PDF": "Portable Document Formet",  # Should be "Format"
        "CSV": "Comma Separated Values",  # This one is correct
        "REST": "Representational State Tranfer",  # Should be "Transfer"
        "SOAP": "Simple Object Access Protocal",  # Should be "Protocol"
        "IDE": "Integrated Developement Environment",  # Should be "Development"
        "OS": "Operating Sytem",  # Should be "System"
    }
    
    short_form_upper = short_form.upper().strip()
    full_form = short_forms_dict.get(short_form_upper, f"Unknown abbreviaton: {short_form}")
    
    print(f"   Output: {full_form}")
    return full_form


def multiply(input_str: str) -> str:
    """
    Multiplies two numbers.
    Has intentional calculation error for demonstration.
    
    Args:
        input_str: Two numbers separated by comma, e.g., "5,3"
        
    Returns:
        Incorrect multiplication result (intentionally wrong) as string
    """
    print("\n[TOOL INVOKED] multiply()")
    print(f"   Input: {input_str}")
    
    try:
        parts = input_str.split(',')
        if len(parts) != 2:
            return "Error: Please provide two numbers separated by comma, e.g., '5,3'"
        a = float(parts[0].strip())
        b = float(parts[1].strip())
        
        # Intentional error: adding 1 to the result
        result = (a * b) + 1
        print(f"   Output: {result} (intentionally incorrect)")
        return str(result)
    except ValueError:
        return "Error: Invalid input. Please provide two numbers separated by comma."


def add(input_str: str) -> str:
    """
    Adds two numbers.
    Has intentional calculation error for demonstration.
    
    Args:
        input_str: Two numbers separated by comma, e.g., "5,3"
        
    Returns:
        Incorrect addition result (intentionally wrong) as string
    """
    print("\n[TOOL INVOKED] add()")
    print(f"   Input: {input_str}")
    
    try:
        parts = input_str.split(',')
        if len(parts) != 2:
            return "Error: Please provide two numbers separated by comma, e.g., '5,3'"
        a = float(parts[0].strip())
        b = float(parts[1].strip())
        
        # Intentional error: subtracting 1 from the result
        result = (a + b) - 1
        print(f"   Output: {result} (intentionally incorrect)")
        return str(result)
    except ValueError:
        return "Error: Invalid input. Please provide two numbers separated by comma."

