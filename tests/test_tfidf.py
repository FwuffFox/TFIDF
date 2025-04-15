import pytest
from tfidf import TFIDFCalculator, WordStat

def test_tfidf():
    calculator = TFIDFCalculator()
    document = "Apple - это фрукт. Apple - это также технологическая компания. Apple"
    results = calculator.calculate_tfidf(document)

    assert len(results) > 0, "Результаты TFIDF не должны быть пустыми"
    assert all(isinstance(stat, WordStat) for stat in results), "Все результаты должны быть экземплярами WordStat"
    assert results[0].idf >= results[-1].idf, "Результаты должны быть отсортированы по IDF в порядке убывания"
    assert results[0].word == "apple", "Самым значимым словом должно быть 'apple'"
    assert results[0].tf == 3, "Частота термина 'apple' должна быть равна 3"

def test_tfidf_multiple():
    calculator = TFIDFCalculator()
    doc1 = "Это первый документ."
    doc2 = "Это второй документ с большим количеством слов."
    _ = calculator.calculate_tfidf(doc1)
    results = calculator.calculate_tfidf(doc2)

    assert len(results) > 0, "Результаты TFIDF не должны быть пустыми"
    assert results[0].idf >= results[-1].idf, "Результаты должны быть отсортированы по IDF в порядке убывания"
    assert calculator.document_count == 2, "Количество документов должно быть равно 2 после обработки двух документов"
    assert "второй" in [stat.word for stat in results], "'второй' должно быть в результатах для второго документа"
