import re
from collections import Counter
import math

special_symbol_clean_regex = re.compile(r"[^\w\s]")

class WordStat:
    def __init__(self, word, tf, idf):
        self.word = word
        self.tf = tf
        self.idf = idf

class TFIDFCalculator:
    def __init__(self):
        self.document_hashes = []
        self.document_count = 0
        self.word_count = Counter()


    def calculate_tfidf(self, document) -> list[WordStat]:
        document_hash = hash(document)
        
        text = re.sub(special_symbol_clean_regex, "", document.lower())
        document_word_count = Counter(text.split())

        if document_hash not in self.document_hashes:
            self.document_hashes.append(document_hash)
            self.document_count += 1
            self.word_count.update(document_word_count)
        
        idf = {
            word: math.log(self.document_count / (1 + self.word_count[word])) if self.document_count > 1 else 1.0
            for word in document_word_count
        }

        results = [WordStat(word, count, idf[word]) for word, count in document_word_count.items()]
        results.sort(key=lambda x: x.idf, reverse=True)
        return results[:50]