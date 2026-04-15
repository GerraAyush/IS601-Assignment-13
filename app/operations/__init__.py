from typing import Union


# Define a type alias for numbers that can be either int or float
Number = Union[int, float]

def add(a: Number, b: Number) -> Number:
    # Perform addition of a and b
    result = a + b
    return result

def subtract(a: Number, b: Number) -> Number:
    # Perform subtraction of b from a
    result = a - b
    return result

def multiply(a: Number, b: Number) -> Number:
    # Perform multiplication of a and b
    result = a * b
    return result

def divide(a: Number, b: Number) -> float:
    # Check if the divisor is zero to prevent division by zero
    if b == 0:
        # Raise a ValueError with a descriptive message
        raise ValueError("Cannot divide by zero!")
    
    # Perform division of a by b and return the result as a float
    result = a / b
    return result
