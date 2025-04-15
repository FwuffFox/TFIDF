import math
import pytest
from app.tfidf import TFIDFCalculator, WordStat

def test_tfidf_multiple():
    calculator = TFIDFCalculator()
    doc1 = "A"
    doc2 = "B"
    doc3 = "B B"
    doc4 = "A B"
    
    _ = calculator.calculate_tfidf(doc1)
    _ = calculator.calculate_tfidf(doc2)
    _ = calculator.calculate_tfidf(doc3)
    res = calculator.calculate_tfidf(doc4)

    assert len(res) == 2
    assert res[0].word == "a" and res[0].tf == 1 and res[0].idf == math.log(4/2)
    assert res[1].word == "b" and res[1].tf == 1 and res[1].idf == math.log(4/3)
    
