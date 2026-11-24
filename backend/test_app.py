import pytest
from app import location
def test_valid():
    assert location('https://www.google.com/maps/@41.9380092,21.5279322,240a') == {'latitude':41.9380092,'longitude':21.5279322}
@pytest.mark.parametrize('url',['https://evil.com/maps/@1,2','https://www.google.com/maps/@999,2','https://www.google.com/maps/place/test'])
def test_invalid(url):
    with pytest.raises(ValueError): location(url)
