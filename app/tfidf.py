import re
from collections import Counter, defaultdict
import math

special_symbol_clean_regex = re.compile(r"[^\w\s]")

class WordStat:
    def __init__(self, word, tf, idf):
        self.word = word
        self.tf = tf
        self.idf = idf

class TFIDFCalculator:
    def __init__(self):
        self.document_hashes = set()
        self.word_to_docs = defaultdict(int)  
        self.total_documents = 0
        
    def calculate_tfidf(self, document) -> list[WordStat]:
        text = re.sub(special_symbol_clean_regex, "", document.lower())
        words = text.split()
        
        if not words:
            return []
            
        document_hash = hash(document)
        
        is_new_document = document_hash not in self.document_hashes
        
        if is_new_document:
            self.document_hashes.add(document_hash)
            self.total_documents += 1
            
            unique_words = set(words)
            for word in unique_words:
                self.word_to_docs[word] += 1
        
        document_word_count = Counter(words)
        
        results = []
        for word, count in document_word_count.items():
            docs_with_word = self.word_to_docs.get(word, 0)
            
            if docs_with_word > 0 and self.total_documents > 1:
                idf = math.log(self.total_documents / docs_with_word)
            else:
                idf = 1.0
                
            results.append(WordStat(word, count, idf))
        
        results.sort(key=lambda x: x.idf, reverse=True)
        return results