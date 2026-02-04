"""
Unit tests for request models.

Tests the Pydantic request models for validation and serialization.

Validates: Requirements 12.6
"""

import pytest
from pydantic import ValidationError
from app.models.requests import OCRRequest, HealthCheckRequest


class TestOCRRequest:
    """Test suite for OCRRequest model"""
    
    def test_ocr_request_with_all_fields(self):
        """Test OCRRequest with all fields provided"""
        request = OCRRequest(
            language="Turkish",
            enhance_image=True
        )
        
        assert request.language == "Turkish"
        assert request.enhance_image is True
    
    def test_ocr_request_with_no_fields(self):
        """Test OCRRequest with no fields (all optional)"""
        request = OCRRequest()
        
        assert request.language is None
        assert request.enhance_image is False
    
    def test_ocr_request_with_only_language(self):
        """Test OCRRequest with only language field"""
        request = OCRRequest(language="English")
        
        assert request.language == "English"
        assert request.enhance_image is False
    
    def test_ocr_request_with_only_enhance_image(self):
        """Test OCRRequest with only enhance_image field"""
        request = OCRRequest(enhance_image=True)
        
        assert request.language is None
        assert request.enhance_image is True
    
    def test_ocr_request_serialization(self):
        """Test OCRRequest JSON serialization"""
        request = OCRRequest(language="Spanish", enhance_image=True)
        data = request.model_dump()
        
        assert data == {
            "language": "Spanish",
            "enhance_image": True
        }
    
    def test_ocr_request_from_dict(self):
        """Test OCRRequest creation from dictionary"""
        data = {
            "language": "French",
            "enhance_image": False
        }
        request = OCRRequest(**data)
        
        assert request.language == "French"
        assert request.enhance_image is False
    
    def test_ocr_request_json_schema(self):
        """Test OCRRequest has proper JSON schema"""
        schema = OCRRequest.model_json_schema()
        
        assert "properties" in schema
        assert "language" in schema["properties"]
        assert "enhance_image" in schema["properties"]
        # Check that fields have proper structure (Pydantic v2 uses anyOf for optional fields)
        assert "anyOf" in schema["properties"]["language"] or "type" in schema["properties"]["language"]
        assert "type" in schema["properties"]["enhance_image"] or "anyOf" in schema["properties"]["enhance_image"]


class TestHealthCheckRequest:
    """Test suite for HealthCheckRequest model"""
    
    def test_health_check_request_with_detailed(self):
        """Test HealthCheckRequest with detailed field"""
        request = HealthCheckRequest(detailed=True)
        
        assert request.detailed is True
    
    def test_health_check_request_without_detailed(self):
        """Test HealthCheckRequest without detailed field"""
        request = HealthCheckRequest()
        
        assert request.detailed is False
    
    def test_health_check_request_serialization(self):
        """Test HealthCheckRequest JSON serialization"""
        request = HealthCheckRequest(detailed=True)
        data = request.model_dump()
        
        assert data == {"detailed": True}
    
    def test_health_check_request_from_dict(self):
        """Test HealthCheckRequest creation from dictionary"""
        data = {"detailed": False}
        request = HealthCheckRequest(**data)
        
        assert request.detailed is False
    
    def test_health_check_request_json_schema(self):
        """Test HealthCheckRequest has proper JSON schema"""
        schema = HealthCheckRequest.model_json_schema()
        
        assert "properties" in schema
        assert "detailed" in schema["properties"]
        # Check that field has proper structure (Pydantic v2 uses anyOf for optional fields)
        assert "type" in schema["properties"]["detailed"] or "anyOf" in schema["properties"]["detailed"]


class TestRequestModelsIntegration:
    """Integration tests for request models"""
    
    def test_ocr_request_example_matches_schema(self):
        """Test that OCRRequest example is valid"""
        schema = OCRRequest.model_json_schema()
        example = schema.get("examples", [{}])[0] if "examples" in schema else {}
        
        # If example exists, it should be valid
        if example:
            request = OCRRequest(**example)
            assert request is not None
    
    def test_health_check_request_example_matches_schema(self):
        """Test that HealthCheckRequest example is valid"""
        schema = HealthCheckRequest.model_json_schema()
        example = schema.get("examples", [{}])[0] if "examples" in schema else {}
        
        # If example exists, it should be valid
        if example:
            request = HealthCheckRequest(**example)
            assert request is not None
    
    def test_all_request_models_have_descriptions(self):
        """Test that all request models have field descriptions"""
        ocr_schema = OCRRequest.model_json_schema()
        health_schema = HealthCheckRequest.model_json_schema()
        
        # Check OCRRequest fields have descriptions
        for field_name in ["language", "enhance_image"]:
            assert "description" in ocr_schema["properties"][field_name]
        
        # Check HealthCheckRequest fields have descriptions
        assert "description" in health_schema["properties"]["detailed"]
