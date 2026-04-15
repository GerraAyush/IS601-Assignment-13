from datetime import datetime
from typing import List, Optional

from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class CalculationType(str, Enum):
    """Valid calculation types"""
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"

class CalculationBase(BaseModel):
    type: CalculationType = Field(
        ...,
        description="Type of calculation (addition, subtraction, multiplication, division)",
        example="addition"
    )
    inputs: List[float] = Field(
        ...,
        description="List of numeric inputs for the calculation",
        example=[10.5, 3, 2],
    )

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        allowed = {e.value for e in CalculationType}
        # Ensure v is a string and check (in lowercase) if it's allowed.
        if not isinstance(v, str) or v.lower() not in allowed:
            raise ValueError(f"Type must be one of: {', '.join(sorted(allowed))}")
        return v.lower()

    @field_validator("inputs", mode="before")
    @classmethod
    def check_inputs_is_list(cls, v):
        if not isinstance(v, list):
            raise ValueError("Input should be a valid list")
        return v

    @model_validator(mode='after')
    def validate_inputs(self) -> "CalculationBase":
        """Validate inputs based on calculation type"""
        if len(self.inputs) < 2:
            raise ValueError("At least two numbers are required for calculation")
        if self.type == CalculationType.DIVISION:
            # Prevent division by zero (skip the first value as numerator)
            if any(x == 0 for x in self.inputs[1:]):
                raise ValueError("Cannot divide by zero")
        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {"type": "addition", "inputs": [10.5, 3, 2]},
                {"type": "division", "inputs": [100, 2]}
            ]
        }
    )

class CalculationCreate(CalculationBase):
    """Schema for creating a new Calculation"""
    user_id: UUID = Field(
        ...,
        description="UUID of the user who owns this calculation",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "addition",
                "inputs": [10.5, 3, 2],
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )

class CalculationUpdate(BaseModel):
    """Schema for updating an existing Calculation"""
    
    type: Optional[CalculationType] = Field(
        None,
        description="Updated calculation type",
        example="addition"
    )

    inputs: Optional[List[float]] = Field(
        None,
        description="Updated list of numeric inputs for the calculation",
        example=[42, 7]
    )

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v is None:
            return v
        allowed = {e.value for e in CalculationType}
        if not isinstance(v, str) or v.lower() not in allowed:
            raise ValueError(f"Type must be one of: {', '.join(sorted(allowed))}")
        return v.lower()

    @model_validator(mode="after")
    def validate_inputs(self):
        """
        Validate inputs and type combination.
        Important: Only validate what's provided.
        """
        if self.inputs is not None:
            if len(self.inputs) < 2:
                raise ValueError("At least two numbers are required for calculation")

            # If type is provided OR defaults to division from DB later,
            # we only enforce division rule if type is explicitly given here
            if self.type == CalculationType.DIVISION:
                if any(x == 0 for x in self.inputs[1:]):
                    raise ValueError("Cannot divide by zero")

        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "type": "multiplication",
                "inputs": [6, 7]
            }
        }
    )

class CalculationResponse(CalculationBase):
    """Schema for reading a Calculation from the database"""
    id: UUID = Field(
        ...,
        description="Unique UUID of the calculation",
        example="123e4567-e89b-12d3-a456-426614174999"
    )
    user_id: UUID = Field(
        ...,
        description="UUID of the user who owns this calculation",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    created_at: datetime = Field(..., description="Time when the calculation was created")
    updated_at: datetime = Field(..., description="Time when the calculation was last updated")
    result: float = Field(
        ...,
        description="Result of the calculation",
        example=15.5
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174999",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "addition",
                "inputs": [10.5, 3, 2],
                "result": 15.5,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        }
    )
