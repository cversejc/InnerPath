"""
Unit tests for bazi_calculator module
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.bazi_calculator import (
    BaziCalculator,
    calculate_bazi_from_user_data,
    calculate_mingli_foundation,
)


class TestBaziCalculator:
    """Test BaziCalculator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.calculator = BaziCalculator()

    def test_calculate_bazi_with_hour(self):
        """Test bazi calculation with hour specified"""
        result = self.calculator.calculate_bazi(
            year=2002,
            month=2,
            day=4,
            hour=0,
            minute=0,
            is_solar=True
        )

        assert result["year"]["pillar"] == "辛巳"
        assert result["month"]["pillar"] == "壬寅"
        assert result["day"]["pillar"] == "癸卯"
        assert result["hour"]["pillar"] == "壬子"
        assert result["day_master"] == "癸"
        assert result["zodiac"] == "蛇"

    def test_calculate_bazi_without_hour(self):
        """Test bazi calculation without hour"""
        result = self.calculator.calculate_bazi(
            year=1990,
            month=5,
            day=15,
            hour=None,
            minute=None,
            is_solar=True
        )

        assert result["year"]["pillar"] == "庚午"
        assert result["month"]["pillar"] == "辛巳"
        assert result["day"]["pillar"] == "庚辰"
        assert result["hour"] is None
        assert result["day_master"] == "庚"
        assert result["zodiac"] == "马"

    def test_calculate_bazi_lunar_calendar(self):
        """Test bazi calculation with lunar calendar"""
        result = self.calculator.calculate_bazi(
            year=2001,
            month=12,
            day=23,
            hour=0,
            minute=0,
            is_solar=False
        )

        # 农历2001年12月23日 = 公历2002年2月4日
        assert result["year"]["pillar"] == "辛巳"
        assert result["day_master"] == "癸"

    def test_ten_gods_calculation(self):
        """Test ten gods (十神) calculation"""
        result = self.calculator.calculate_bazi(
            year=2002,
            month=2,
            day=4,
            hour=0,
            minute=0,
            is_solar=True
        )

        # 日主为癸
        assert result["day_master"] == "癸"
        # 年干为辛，癸见辛为偏印
        assert result["year"]["ten_god"] == "偏印"
        # 月干为壬，癸见壬为劫财
        assert result["month"]["ten_god"] == "劫财"
        # 时干为壬，癸见壬为劫财
        assert result["hour"]["ten_god"] == "劫财"

    def test_different_hours(self):
        """Test different hours produce different hour pillars"""
        result_zi = self.calculator.calculate_bazi(2002, 2, 4, 0, 0, True)
        result_wu = self.calculator.calculate_bazi(2002, 2, 4, 12, 0, True)

        assert result_zi["hour"]["pillar"] == "壬子"
        assert result_wu["hour"]["pillar"] == "戊午"
        assert result_zi["hour"]["pillar"] != result_wu["hour"]["pillar"]

    def test_invalid_date(self):
        """Test invalid date raises error"""
        with pytest.raises(ValueError):
            self.calculator.calculate_bazi(
                year=2002,
                month=13,  # Invalid month
                day=4,
                hour=0,
                minute=0,
                is_solar=True
            )


class TestCalculateBaziFromUserData:
    """Test calculate_bazi_from_user_data function"""

    def test_with_complete_data(self):
        """Test with complete user data"""
        user_data = {
            "birth_year": 2002,
            "birth_month": 2,
            "birth_day": 4,
            "birth_hour": 0,
            "birth_minute": 0,
            "gender": "male",
            "calendar_type": "solar"
        }

        result = calculate_bazi_from_user_data(user_data)

        assert "bazi" in result
        assert "ziwei" in result
        assert result["bazi"]["day_master"] == "癸"

    def test_without_hour(self):
        """Test without hour data"""
        user_data = {
            "birth_year": 1990,
            "birth_month": 5,
            "birth_day": 15,
            "birth_hour": None,
            "birth_minute": None,
            "gender": "female",
            "calendar_type": "solar"
        }

        result = calculate_bazi_from_user_data(user_data)

        assert "bazi" in result
        assert result["bazi"]["hour"] is None
        assert result["ziwei"] is None  # No ziwei without hour

    def test_lunar_calendar(self):
        """Test with lunar calendar"""
        user_data = {
            "birth_year": 2001,
            "birth_month": 12,
            "birth_day": 23,
            "birth_hour": 0,
            "birth_minute": 0,
            "gender": "male",
            "calendar_type": "lunar"
        }

        result = calculate_bazi_from_user_data(user_data)

        assert "bazi" in result
        assert result["bazi"]["day_master"] == "癸"

    def test_frontend_payload_aliases(self):
        """Test frontend-compatible field names and string values"""
        user_data = {
            "birth_year": "2001",
            "birth_month": "12",
            "birth_day": "23",
            "birth_hour": "0",
            "birth_minute": "",
            "gender": "male",
            "calendarType": "lunar",
            "birth_place": "北京",
        }

        result = calculate_bazi_from_user_data(user_data)

        assert result["bazi"]["day_master"] == "癸"
        assert result["bazi"]["hour"]["pillar"] == "壬子"


class TestMingliFoundation:
    """Test report-ready deterministic foundation data"""

    def test_foundation_with_hour_contains_bazi_and_ziwei(self):
        user_data = {
            "birth_year": 2002,
            "birth_month": 2,
            "birth_day": 4,
            "birth_hour": 0,
            "birth_minute": 0,
            "gender": "male",
            "calendar_type": "solar",
        }

        result = calculate_mingli_foundation(user_data)

        assert result["calculation_method"] == "deterministic-mingli"
        assert result["bazi"]["year"] == {
            "stem": "辛",
            "branch": "巳",
            "ten_god": "偏印",
        }
        assert result["bazi"]["hour"] == {
            "stem": "壬",
            "branch": "子",
            "ten_god": "劫财",
        }
        assert result["bazi"]["day_master"] == "癸"
        assert result["ziwei"]["life_palace"]["main_stars"]

    def test_foundation_without_hour_omits_ziwei(self):
        user_data = {
            "birth_year": 1990,
            "birth_month": 5,
            "birth_day": 15,
            "birth_hour": None,
            "birth_minute": None,
            "gender": "female",
            "calendar_type": "solar",
        }

        result = calculate_mingli_foundation(user_data)

        assert "hour" not in result["bazi"]
        assert "ziwei" not in result


class TestDeterminism:
    """Test that calculations are deterministic"""

    def test_same_input_same_output(self):
        """Test that same input always produces same output"""
        calculator = BaziCalculator()

        result1 = calculator.calculate_bazi(2002, 2, 4, 0, 0, True)
        result2 = calculator.calculate_bazi(2002, 2, 4, 0, 0, True)
        result3 = calculator.calculate_bazi(2002, 2, 4, 0, 0, True)

        assert result1 == result2 == result3

    def test_multiple_calls_consistency(self):
        """Test consistency across multiple calls"""
        user_data = {
            "birth_year": 1990,
            "birth_month": 5,
            "birth_day": 15,
            "birth_hour": 12,
            "birth_minute": 0,
            "gender": "female",
            "calendar_type": "solar"
        }

        results = [calculate_bazi_from_user_data(user_data) for _ in range(10)]

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result


if __name__ == "__main__":
    # Run tests manually
    print("Running BaziCalculator tests...")
    test_suite = TestBaziCalculator()
    test_suite.setup_method()

    try:
        test_suite.test_calculate_bazi_with_hour()
        print("✓ test_calculate_bazi_with_hour")
    except AssertionError as e:
        print(f"✗ test_calculate_bazi_with_hour: {e}")

    try:
        test_suite.test_calculate_bazi_without_hour()
        print("✓ test_calculate_bazi_without_hour")
    except AssertionError as e:
        print(f"✗ test_calculate_bazi_without_hour: {e}")

    try:
        test_suite.test_ten_gods_calculation()
        print("✓ test_ten_gods_calculation")
    except AssertionError as e:
        print(f"✗ test_ten_gods_calculation: {e}")

    try:
        test_suite.test_different_hours()
        print("✓ test_different_hours")
    except AssertionError as e:
        print(f"✗ test_different_hours: {e}")

    print("\nAll manual tests completed!")
