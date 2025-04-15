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

def test_empty_document():
    calculator = TFIDFCalculator()
    result = calculator.calculate_tfidf("")
    assert result == []

def test_special_characters_only():
    calculator = TFIDFCalculator()
    result = calculator.calculate_tfidf("!@#$%^&*()")
    assert result == []

def test_case_insensitivity():
    calculator = TFIDFCalculator()
    calculator.calculate_tfidf("Apple banana")
    result = calculator.calculate_tfidf("apple BANANA")
    
    words = {w.word: w for w in result}
    assert "apple" in words
    assert "banana" in words
    assert words["apple"].tf == 1
    assert words["banana"].tf == 1

def test_duplicate_documents_are_ignored():
    calculator = TFIDFCalculator()
    calculator.calculate_tfidf("test document")
    calculator.calculate_tfidf("test document")  # дубликат, не должен влиять
    result = calculator.calculate_tfidf("another test")
    
    words = {w.word: w for w in result}
    assert "test" in words
    assert words["test"].idf == math.log(2 / 2) 

def test_idf_sorting_desc():
    calculator = TFIDFCalculator()
    calculator.calculate_tfidf("a b c")
    calculator.calculate_tfidf("b c")
    result = calculator.calculate_tfidf("a b c")
    
    idfs = [ws.idf for ws in result]
    assert idfs == sorted(idfs, reverse=True)
