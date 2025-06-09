import math
import re
from collections import Counter

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, WordFrequency


async def process_new_document(session: AsyncSession, document: Document):
    text = document.text
    # Tokenize and count terms
    words = re.findall(r"\b\w+\b", text.lower())
    word_counts = Counter(words)
    total_terms = sum(word_counts.values())

    # Insert WordFrequency with TF
    for word, count in word_counts.items():
        tf = count / total_terms
        wf = WordFrequency(
            word=word, frequency=count, tf_score=tf, document_id=document.id
        )
        session.add(wf)
    await session.commit()

    # Get total number of documents in the corpus
    total_docs = (
        await session.execute(
            select(func.count()).where(Document.corpus_id == document.corpus_id)
        )
    ).scalar_one()

    # Get affected words
    affected_words = list(word_counts.keys())

    # Get updated DF for affected words (within the same corpus only)
    result = await session.execute(
        select(WordFrequency.word, func.count(distinct(WordFrequency.document_id)))
        .join(Document)
        .where(
            WordFrequency.word.in_(affected_words),
            Document.corpus_id == document.corpus_id,
        )
        .group_by(WordFrequency.word)
    )

    df_dict = {row[0]: row[1] for row in result.all()}

    # Recompute IDF for affected words
    idf_dict = {word: math.log(total_docs / (1 + df)) for word, df in df_dict.items()}

    # Update all TF-IDF values for affected words in the corpus
    from sqlalchemy import update

    for word in affected_words:
        idf = idf_dict[word]

        # Update IDF and TF-IDF scores for all WordFrequency records with this word in the corpus
        await session.execute(
            update(WordFrequency)
            .where(
                WordFrequency.word == word,
                WordFrequency.document_id.in_(
                    select(Document.id).where(Document.corpus_id == document.corpus_id)
                ),
            )
            .values(idf_score=idf, tfidf_score=WordFrequency.tf_score * idf)
        )

    # Commit changes after all updates
    await session.commit()
