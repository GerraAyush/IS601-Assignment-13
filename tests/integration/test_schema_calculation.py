import pytest
from pydantic import ValidationError

from uuid import uuid4

from app.schemas.calculation import (
    CalculationType,
    CalculationBase,
    CalculationCreate,
    CalculationUpdate,
    CalculationResponse
)


def test_calculation_type_enum_values():

    assert CalculationType.ADDITION.value == "addition"
    assert CalculationType.SUBTRACTION.value == "subtraction"
    assert CalculationType.MULTIPLICATION.value == "multiplication"
    assert CalculationType.DIVISION.value == "division"


def test_calculation_base_valid_addition():

    data = {
        "type": "addition",
        "inputs": [10.5, 3, 2]
    }
    calc = CalculationBase(**data)
    assert calc.type == CalculationType.ADDITION
    assert calc.inputs == [10.5, 3, 2]


def test_calculation_base_valid_subtraction():

    data = {
        "type": "subtraction",
        "inputs": [20, 5.5]
    }
    calc = CalculationBase(**data)
    assert calc.type == CalculationType.SUBTRACTION
    assert calc.inputs == [20, 5.5]


def test_calculation_base_case_insensitive_type():

    for type_variant in ["Addition", "ADDITION", "AdDiTiOn"]:
        data = {"type": type_variant, "inputs": [1, 2]}
        calc = CalculationBase(**data)
        assert calc.type == CalculationType.ADDITION


def test_calculation_base_invalid_type():

    data = {
        "type": "modulus",  # Invalid type
        "inputs": [10, 3]
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    
    errors = exc_info.value.errors()
    assert any("Type must be one of" in str(err) for err in errors)


def test_calculation_base_inputs_not_list():

    data = {
        "type": "addition",
        "inputs": "not a list"
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    
    errors = exc_info.value.errors()
    assert any("Input should be a valid list" in str(err) for err in errors)


def test_calculation_base_insufficient_inputs():

    data = {
        "type": "addition",
        "inputs": [5]  # Only one input
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    
    # Validation error can be from min_length constraint or model validator
    assert len(exc_info.value.errors()) > 0


def test_calculation_base_empty_inputs():

    data = {
        "type": "multiplication",
        "inputs": []
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    
    errors = exc_info.value.errors()
    # Should fail on min_length=2
    assert len(errors) > 0


def test_calculation_base_division_by_zero():

    data = {
        "type": "division",
        "inputs": [100, 0]  # Division by zero
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    
    errors = exc_info.value.errors()
    assert any("Cannot divide by zero" in str(err) for err in errors)


def test_calculation_base_division_by_zero_in_middle():

    data = {
        "type": "division",
        "inputs": [100, 5, 0, 2]  # Zero in middle
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    
    errors = exc_info.value.errors()
    assert any("Cannot divide by zero" in str(err) for err in errors)


def test_calculation_base_division_zero_numerator_ok():

    data = {
        "type": "division",
        "inputs": [0, 5, 2]  # Zero numerator is valid
    }
    calc = CalculationBase(**data)
    assert calc.inputs[0] == 0


def test_calculation_create_valid():

    user_id = uuid4()
    data = {
        "type": "multiplication",
        "inputs": [2, 3, 4],
        "user_id": str(user_id)
    }
    calc = CalculationCreate(**data)
    assert calc.type == CalculationType.MULTIPLICATION
    assert calc.inputs == [2, 3, 4]
    assert calc.user_id == user_id


def test_calculation_create_missing_user_id():

    data = {
        "type": "addition",
        "inputs": [1, 2]
        # Missing user_id
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationCreate(**data)
    
    errors = exc_info.value.errors()
    assert any("user_id" in str(err) for err in errors)


def test_calculation_create_invalid_user_id():

    data = {
        "type": "subtraction",
        "inputs": [10, 5],
        "user_id": "not-a-valid-uuid"
    }
    with pytest.raises(ValidationError):
        CalculationCreate(**data)


def test_calculation_update_valid():

    data = {
        "inputs": [42, 7]
    }
    calc = CalculationUpdate(**data)
    assert calc.inputs == [42, 7]


def test_calculation_update_all_fields_optional():

    data = {}
    calc = CalculationUpdate(**data)
    assert calc.inputs is None


def test_calculation_update_insufficient_inputs():

    data = {
        "inputs": [5]  # Only one input
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationUpdate(**data)
    
    # Validation error can be from min_length constraint or model validator
    assert len(exc_info.value.errors()) > 0


def test_calculation_response_valid():

    from datetime import datetime
    
    data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "type": "addition",
        "inputs": [10, 5],
        "result": 15.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    calc = CalculationResponse(**data)
    assert calc.result == 15.0
    assert calc.type == CalculationType.ADDITION


def test_calculation_response_missing_result():

    from datetime import datetime
    
    data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "type": "multiplication",
        "inputs": [2, 3],
        # Missing result
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    with pytest.raises(ValidationError) as exc_info:
        CalculationResponse(**data)
    
    errors = exc_info.value.errors()
    assert any("result" in str(err) for err in errors)


def test_multiple_calculations_with_different_types():

    user_id = uuid4()
    
    calcs_data = [
        {"type": "addition", "inputs": [1, 2, 3], "user_id": str(user_id)},
        {"type": "subtraction", "inputs": [10, 3], "user_id": str(user_id)},
        {"type": "multiplication", "inputs": [2, 3, 4],
         "user_id": str(user_id)},
        {"type": "division", "inputs": [100, 5], "user_id": str(user_id)},
    ]
    
    calcs = [CalculationCreate(**data) for data in calcs_data]
    
    assert len(calcs) == 4
    assert calcs[0].type == CalculationType.ADDITION
    assert calcs[1].type == CalculationType.SUBTRACTION
    assert calcs[2].type == CalculationType.MULTIPLICATION
    assert calcs[3].type == CalculationType.DIVISION


def test_schema_with_large_numbers():

    data = {
        "type": "multiplication",
        "inputs": [1e10, 1e10, 1e10]
    }
    calc = CalculationBase(**data)
    assert all(isinstance(x, float) for x in calc.inputs)


def test_schema_with_negative_numbers():

    data = {
        "type": "addition",
        "inputs": [-5, -10, 3.5]
    }
    calc = CalculationBase(**data)
    assert calc.inputs == [-5, -10, 3.5]


def test_schema_with_mixed_int_and_float():

    data = {
        "type": "subtraction",
        "inputs": [100, 23.5, 10, 6.7]
    }
    calc = CalculationBase(**data)
    assert len(calc.inputs) == 4


def test_calculation_base_too_few_inputs():
    """Fewer than 2 inputs → ValidationError (line 49)."""
    with pytest.raises(Exception) as exc:
        CalculationBase(type="addition", inputs=[1])
    assert "At least two numbers" in str(exc.value)


def test_calculation_base_division_by_zero_in_schema():
    """Division with a zero divisor → ValidationError caught by schema (line 51-52)."""
    with pytest.raises(Exception, match="zero"):
        CalculationBase(type="division", inputs=[10, 0])


def test_calculation_update_too_few_inputs():
    """CalculationUpdate with inputs list < 2 → ValidationError (line 97)."""
    with pytest.raises(Exception) as exc:
        CalculationUpdate(inputs=[5])
    assert "At least two numbers" in str(exc.value)


def test_calculation_update_none_inputs_is_valid():
    """CalculationUpdate with inputs=None is explicitly allowed."""
    update = CalculationUpdate(inputs=None)
    assert update.inputs is None

import pytest
from app.schemas.calculation import CalculationUpdate


def test_update_invalid_type():
    """Should raise error for invalid calculation type."""
    with pytest.raises(ValueError):
        CalculationUpdate(type="invalid_type", inputs=[1, 2])


def test_update_inputs_too_short():
    """Should raise error when fewer than 2 inputs are provided."""
    with pytest.raises(ValueError):
        CalculationUpdate(inputs=[1])


def test_update_division_by_zero():
    """Should raise error when division inputs contain zero (except first)."""
    with pytest.raises(ValueError):
        CalculationUpdate(type="division", inputs=[10, 0])


def test_update_only_inputs_valid():
    """Valid update when only inputs are provided."""
    obj = CalculationUpdate(inputs=[10, 2])
    assert obj.inputs == [10, 2]
    assert obj.type is None


def test_update_type_case_insensitive():
    """Type should be normalized to lowercase."""
    obj = CalculationUpdate(type="ADDITION", inputs=[1, 2])
    assert obj.type == "addition"
    assert obj.inputs == [1, 2]
    