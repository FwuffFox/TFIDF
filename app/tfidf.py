import re
from collections import Counter
import math

special_symbol_clean_regex = re.compile(r"[^\w\s]")

class WordStat:
    def __init__(self, word, tf, idf):
        self.word = word
        self.tf = tf
        self.idf = idf

class DocumentStat:
    def __init__(self, hashed_contents, words):
        self.hashed_contents = hashed_contents
        self.words = words

    def has_word(self, word: str):
        return word in self.words

class TFIDFCalculator:
    def __init__(self):
        self.document_stats = []


    def calculate_tfidf(self, document) -> list[WordStat]:
        text = re.sub(special_symbol_clean_regex, "", document.lower())
        words = text.split()

        if not self.is_duplicate(document):
            self.document_stats.append(DocumentStat(hash(document), words))

        document_word_count = Counter(words)

        idf = {}
        for word, count in document_word_count.items():
            word_in_other_docs = 0
            for document_stat in self.document_stats:
                if document_stat.has_word(word):
                    word_in_other_docs += 1
            
            idf[word] = (math.log(len(self.document_stats) / word_in_other_docs)
                            if len(self.document_stats) > 1 and word_in_other_docs > 0
                            else 1.0)

        results = [WordStat(word, count, idf[word]) for word, count in document_word_count.items()]
        results.sort(key=lambda x: x.idf, reverse=True)
        return results[:50]
    
    def is_duplicate(self, document) -> bool:
        document_hash = hash(document)

        return any(document_hash == doc.hashed_contents for doc in self.document_stats)