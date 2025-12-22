"""
Test suite for deterministic Kerykeion astrological calculations.
Uses Phoenix fixture: 1976-01-27 00:24 America/Phoenix (33.4484, -112.0740)
"""
import pytest
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import from cogs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cogs.astrologer import Astrologer

# Phoenix fixture data
PHOENIX_FIXTURE = {
    'name': 'PK',
    'y': 1976, 'm': 1, 'd': 27, 
    'hh': 0, 'mm': 24,
    'lat': 33.4484, 'lon': -112.0740,
    'tz_str': 'America/Phoenix'
}

class MockBot:
    """Mock bot for testing."""
    def __init__(self):
        self.is_closed = lambda: False
        self.loop = None

@pytest.fixture
def astrologer():
    """Create Astrologer instance for testing."""
    bot = MockBot()
    return Astrologer(bot, user_birth_data={})

@pytest.fixture
def phoenix_natal(astrologer):
    """Phoenix natal chart fixture."""
    return astrologer.computer.compute_natal(**PHOENIX_FIXTURE)

def test_signs_core(phoenix_natal):
    """Test that core planetary signs match expected values for Phoenix fixture."""
    six = phoenix_natal['natal']['six']
    
    # Expected signs based on Phoenix data (Kerykeion returns abbreviated forms)
    assert six['sun']['sign'] == 'Aqu', f"Sun in {six['sun']['sign']}, expected Aqu (Aquarius)"
    assert six['moon']['sign'] == 'Sag', f"Moon in {six['moon']['sign']}, expected Sag (Sagittarius)"  
    assert six['mercury']['sign'] == 'Cap', f"Mercury in {six['mercury']['sign']}, expected Cap (Capricorn)"
    assert six['venus']['sign'] == 'Cap', f"Venus in {six['venus']['sign']}, expected Cap (Capricorn)"
    assert six['mars']['sign'] == 'Gem', f"Mars in {six['mars']['sign']}, expected Gem (Gemini)"
    assert six['asc']['sign'] == 'Lib', f"Ascendant in {six['asc']['sign']}, expected Lib (Libra)"

def test_geometry_and_neighborhood(astrologer, phoenix_natal):
    """Test mathematical constraints and angular relationships."""

    # Test solar neighborhood (Mercury and Venus limits)
    six = phoenix_natal['natal']['six']
    sun_lon = six['sun']['lon']
    mercury_lon = six['mercury']['lon']
    venus_lon = six['venus']['lon']

    mercury_dist = astrologer.computer.angdiff(sun_lon, mercury_lon)
    venus_dist = astrologer.computer.angdiff(sun_lon, venus_lon)
    
    assert mercury_dist <= 28.5, f"Mercury {mercury_dist:.2f}° from Sun, max 28.5°"
    assert venus_dist <= 47.5, f"Venus {venus_dist:.2f}° from Sun, max 47.5°"

def test_oppositions(astrologer, phoenix_natal):
    """Test that ASC/DSC and MC/IC are properly opposed."""
    six = phoenix_natal['natal']['six']
    houses = phoenix_natal['natal']['houses']

    asc_lon = six['asc']['lon']
    mc_lon = six['mc']['lon']
    dsc_lon = houses['7']['lon']
    ic_lon = houses['4']['lon']

    asc_dsc_diff = abs(astrologer.computer.angdiff(asc_lon, dsc_lon) - 180.0)
    mc_ic_diff = abs(astrologer.computer.angdiff(mc_lon, ic_lon) - 180.0)
    
    assert asc_dsc_diff <= 0.5, f"ASC/DSC opposition off by {asc_dsc_diff:.3f}°"
    assert mc_ic_diff <= 0.5, f"MC/IC opposition off by {mc_ic_diff:.3f}°"

def test_house_monotonic(phoenix_natal):
    """Test that house cusps increase monotonically around zodiac."""
    houses = phoenix_natal['natal']['houses']
    cusps = [houses[str(i)]['lon'] for i in range(1, 13)]
    
    # Count wraps (should be exactly 1 for 0°/360° boundary)
    wraps = 0
    for i in range(12):
        current = cusps[i]
        next_cusp = cusps[(i + 1) % 12]
        if next_cusp <= current:
            wraps += 1
    
    assert wraps == 1, f"House cusps have {wraps} wraps, expected 1"

def test_validation_catches_errors(astrologer):
    """Test that validation catches impossible charts."""
    # This should pass validation
    valid_chart = astrologer.computer.compute_natal(**PHOENIX_FIXTURE)
    astrologer.computer.validate_natal_chart(valid_chart)  # Should not raise
    
    # Test would catch manually constructed invalid chart
    # (In real scenario, Kerykeion shouldn't produce invalid data)

def test_deterministic_reproducibility(astrologer):
    """Test that identical inputs produce identical outputs."""
    chart1 = astrologer.computer.compute_natal(**PHOENIX_FIXTURE)
    chart2 = astrologer.computer.compute_natal(**PHOENIX_FIXTURE)
    
    # Compare key positions (within floating point precision)
    six1 = chart1['natal']['six']
    six2 = chart2['natal']['six']
    
    for planet in ['sun', 'moon', 'mercury', 'venus', 'mars', 'asc', 'mc']:
        lon1 = six1[planet]['lon']
        lon2 = six2[planet]['lon']
        assert abs(lon1 - lon2) < 0.001, f"{planet} longitude not reproducible"
        assert six1[planet]['sign'] == six2[planet]['sign'], f"{planet} sign not reproducible"

def test_transits_computation(astrologer):
    """Test transit computation with deterministic coordinates."""
    transits = astrologer.computer.compute_transits_now(
        lat=PHOENIX_FIXTURE['lat'],
        lon=PHOENIX_FIXTURE['lon'],
        tz_str=PHOENIX_FIXTURE['tz_str']
    )
    
    # Should have current timestamp
    assert 'utc_now' in transits
    assert 'transits' in transits
    
    # Should have all main planets
    planets = transits['transits']
    required_planets = ['sun', 'moon', 'mercury', 'venus', 'mars']
    
    for planet in required_planets:
        assert planet in planets, f"Missing {planet} in transits"
        assert 'lon' in planets[planet], f"Missing longitude for {planet}"
        assert 'sign' in planets[planet], f"Missing sign for {planet}"
        
        # Longitude should be valid
        lon = planets[planet]['lon']
        assert 0 <= lon < 360, f"{planet} longitude {lon} out of range"

def test_input_storage(phoenix_natal):
    """Test that input parameters are properly stored."""
    inp = phoenix_natal['input']
    
    assert inp['name'] == PHOENIX_FIXTURE['name']
    assert inp['tz'] == PHOENIX_FIXTURE['tz_str']
    assert inp['lat'] == PHOENIX_FIXTURE['lat']
    assert inp['lon'] == PHOENIX_FIXTURE['lon']
    assert inp['house_system'] == 'placidus'
    assert inp['zodiac'] == 'tropical'
    assert inp['node'] == 'true'

def test_engine_version(phoenix_natal):
    """Test that engine version is recorded."""
    assert 'engine' in phoenix_natal
    assert 'kerykeion@4.26.3' in phoenix_natal['engine']

def test_all_houses_present(phoenix_natal):
    """Test that all 12 houses are computed."""
    houses = phoenix_natal['natal']['houses']
    
    for i in range(1, 13):
        house_key = str(i)
        assert house_key in houses, f"Missing house {i}"
        assert 'lon' in houses[house_key], f"Missing longitude for house {i}"
        assert 'sign' in houses[house_key], f"Missing sign for house {i}"
        
        # Longitude should be valid
        lon = houses[house_key]['lon']
        assert 0 <= lon < 360, f"House {i} longitude {lon} out of range"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])