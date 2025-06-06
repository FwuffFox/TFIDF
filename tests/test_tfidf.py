import hashlib
import math

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.db.models import Base, Corpus, Document, User, WordFrequency
from app.tfidf import process_new_document

# Test database URL - use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_factory() as session:
        yield session
    
    await engine.dispose()

@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_corpus(async_session: AsyncSession, test_user: User):
    """Create a test corpus."""
    corpus = Corpus(
        name="Test Corpus",
        description="A test corpus",
        user_id=test_user.id
    )
    async_session.add(corpus)
    await async_session.commit()
    await async_session.refresh(corpus)
    return corpus

@pytest_asyncio.fixture
async def test_corpus_2(async_session: AsyncSession, test_user: User):
    """Create a second test corpus."""
    corpus = Corpus(
        name="Test Corpus 2",
        description="A second test corpus",
        user_id=test_user.id
    )
    async_session.add(corpus)
    await async_session.commit()
    await async_session.refresh(corpus)
    return corpus

async def create_and_process_document(session: AsyncSession, corpus: Corpus, text: str, filename: str = "") -> Document:
    """Helper function to create a document and process it through TF-IDF calculation."""
    # Include corpus ID in hash to ensure uniqueness across corpuses
    hash_content = f"{corpus.id}_{text}"
    doc_hash = hashlib.md5(hash_content.encode()).hexdigest()
    document = Document(
        filename=filename or f"doc_{doc_hash[:8]}.txt",
        text=text,
        hash=doc_hash,
        corpus_id=corpus.id
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    # Process the document through TF-IDF calculation
    await process_new_document(session, document)
    
    return document

class TestTFIDFWithCorpuses:
    """Test TF-IDF calculations with database models and corpuses."""

    @pytest.mark.asyncio
    async def test_single_document_tfidf(self, async_session: AsyncSession, test_corpus: Corpus):
        """Test TF-IDF calculation for a single document."""
        document = await create_and_process_document(async_session, test_corpus, "hello world hello")
        
        # Check word frequencies were created
        word_freqs = (await async_session.execute(
            select(WordFrequency).where(WordFrequency.document_id == document.id)
        )).scalars().all()
        
        assert len(word_freqs) == 2  # "hello" and "world"
        
        word_freq_dict = {wf.word: wf for wf in word_freqs}
        
        # Check TF scores
        assert abs(word_freq_dict["hello"].tf_score - (2/3)) < 1e-10  # type: ignore
        assert abs(word_freq_dict["world"].tf_score - (1/3)) < 1e-10  # type: ignore
        
        # Check IDF scores (only 1 document in corpus)
        expected_idf = math.log(1 / (1 + 1))  # log(total_docs / (1 + df))
        assert abs(word_freq_dict["hello"].idf_score - expected_idf) < 1e-10  # type: ignore
        assert abs(word_freq_dict["world"].idf_score - expected_idf) < 1e-10  # type: ignore
        
        # Check TF-IDF scores
        assert abs(word_freq_dict["hello"].tfidf_score - ((2/3) * expected_idf)) < 1e-10  # type: ignore
        assert abs(word_freq_dict["world"].tfidf_score - ((1/3) * expected_idf)) < 1e-10  # type: ignore

    @pytest.mark.asyncio
    async def test_multiple_documents_same_corpus(self, async_session: AsyncSession, test_corpus: Corpus):
        """Test IDF calculation with multiple documents in the same corpus."""
        # Create documents
        doc1 = await create_and_process_document(async_session, test_corpus, "hello world")
        doc2 = await create_and_process_document(async_session, test_corpus, "hello python")
        doc3 = await create_and_process_document(async_session, test_corpus, "world python programming")
        
        # Check IDF values
        word_freqs = (await async_session.execute(
            select(WordFrequency).where(WordFrequency.document_id == doc3.id)
        )).scalars().all()
        
        word_freq_dict = {wf.word: wf for wf in word_freqs}
        
        # "world" appears in doc1 and doc3 (2 out of 3 documents)
        # "python" appears in doc2 and doc3 (2 out of 3 documents)
        # "programming" appears only in doc3 (1 out of 3 documents)
        
        expected_idf_common = math.log(3 / (1 + 2))  # log(3 / 3) for words in 2 docs
        expected_idf_rare = math.log(3 / (1 + 1))    # log(3 / 2) for words in 1 doc
        
        assert abs(word_freq_dict["world"].idf_score - expected_idf_common) < 1e-10  # type: ignore
        assert abs(word_freq_dict["python"].idf_score - expected_idf_common) < 1e-10  # type: ignore
        assert abs(word_freq_dict["programming"].idf_score - expected_idf_rare) < 1e-10  # type: ignore

    @pytest.mark.asyncio
    async def test_idf_corpus_isolation(self, async_session: AsyncSession, test_corpus: Corpus, test_corpus_2: Corpus):
        """Test that IDF calculations are isolated per corpus."""
        # Add documents to first corpus
        doc1_c1 = await create_and_process_document(async_session, test_corpus, "hello world")
        doc2_c1 = await create_and_process_document(async_session, test_corpus, "hello python")
        
        # Add documents to second corpus
        doc1_c2 = await create_and_process_document(async_session, test_corpus_2, "hello machine learning")
        doc2_c2 = await create_and_process_document(async_session, test_corpus_2, "deep learning neural networks")
        doc3_c2 = await create_and_process_document(async_session, test_corpus_2, "hello world")
        
        # Get "hello" word frequency from both corpuses
        hello_freqs = (await async_session.execute(
            select(WordFrequency)
            .join(Document)
            .where(WordFrequency.word == "hello")
        )).scalars().all()
        
        # Group by corpus
        corpus1_hello = [wf for wf in hello_freqs if wf.document.corpus_id == test_corpus.id]
        corpus2_hello = [wf for wf in hello_freqs if wf.document.corpus_id == test_corpus_2.id]
        
        # In corpus 1: "hello" appears in 2 out of 2 documents
        expected_idf_c1 = math.log(2 / (1 + 2))  # log(2/3) = negative value
        
        # In corpus 2: "hello" appears in 2 out of 3 documents  
        expected_idf_c2 = math.log(3 / (1 + 2))  # log(3/3) = log(1) = 0
        
        # Check that all instances in corpus 1 have the same IDF
        for wf in corpus1_hello:
            assert abs(wf.idf_score - expected_idf_c1) < 1e-10  # type: ignore
            
        # Check that all instances in corpus 2 have the same IDF
        for wf in corpus2_hello:
            assert abs(wf.idf_score - expected_idf_c2) < 1e-10  # type: ignore
        
        # Verify they are different
        assert abs(expected_idf_c1 - expected_idf_c2) > 1e-10

    @pytest.mark.asyncio
    async def test_idf_updates_on_new_document(self, async_session: AsyncSession, test_corpus: Corpus):
        """Test that IDF values are updated when new documents are added."""
        # Add first document
        doc1 = await create_and_process_document(async_session, test_corpus, "hello world")
        
        # Check initial IDF
        hello_wf_initial = (await async_session.execute(
            select(WordFrequency).where(
                WordFrequency.word == "hello",
                WordFrequency.document_id == doc1.id
            )
        )).scalar_one()
        
        initial_idf = hello_wf_initial.idf_score
        expected_initial_idf = math.log(1 / (1 + 1))  # 1 doc total, "hello" in 1 doc
        assert abs(initial_idf - expected_initial_idf) < 1e-10  # type: ignore
        
        # Add second document with "hello"
        doc2 = await create_and_process_document(async_session, test_corpus, "hello python")
        
        # Check updated IDF for both documents
        hello_wfs = (await async_session.execute(
            select(WordFrequency)
            .join(Document)
            .where(
                WordFrequency.word == "hello",
                Document.corpus_id == test_corpus.id
            )
        )).scalars().all()
        
        expected_updated_idf = math.log(2 / (1 + 2))  # 2 docs total, "hello" in 2 docs
        
        for wf in hello_wfs:
            assert abs(wf.idf_score - expected_updated_idf) < 1e-10  # type: ignore
            assert abs(wf.tfidf_score - (wf.tf_score * expected_updated_idf)) < 1e-10  # type: ignore

    @pytest.mark.asyncio
    async def test_empty_document_handling(self, async_session: AsyncSession, test_corpus: Corpus):
        """Test handling of empty documents."""
        document = await create_and_process_document(async_session, test_corpus, "")
        
        # Check that no word frequencies were created
        word_freqs = (await async_session.execute(
            select(WordFrequency).where(WordFrequency.document_id == document.id)
        )).scalars().all()
        
        assert len(word_freqs) == 0

    @pytest.mark.asyncio
    async def test_special_characters_and_case_handling(self, async_session: AsyncSession, test_corpus: Corpus):
        """Test handling of special characters and case normalization."""
        document = await create_and_process_document(async_session, test_corpus, "Hello, WORLD! Python-Programming")
        
        word_freqs = (await async_session.execute(
            select(WordFrequency).where(WordFrequency.document_id == document.id)
        )).scalars().all()
        
        words = {wf.word for wf in word_freqs}
        
        # Check case normalization and punctuation handling
        assert "hello" in words
        assert "world" in words
        assert "python" in words
        assert "programming" in words
        
        # Verify no uppercase or punctuation remains
        assert "Hello" not in words
        assert "WORLD" not in words
        assert "Python-Programming" not in words

    @pytest.mark.asyncio
    async def test_tf_calculation_accuracy(self, async_session: AsyncSession, test_corpus: Corpus):
        """Test accuracy of TF calculations."""
        document = await create_and_process_document(async_session, test_corpus, "the quick brown fox jumps over the lazy dog the")
        
        word_freqs = (await async_session.execute(
            select(WordFrequency).where(WordFrequency.document_id == document.id)
        )).scalars().all()
        
        word_freq_dict = {wf.word: wf for wf in word_freqs}
        total_words = 10
        
        # "the" appears 3 times
        assert word_freq_dict["the"].frequency == 3  # type: ignore
        assert abs(word_freq_dict["the"].tf_score - (3/total_words)) < 1e-10  # type: ignore
        
        # Other words appear 1 time each
        for word in ["quick", "brown", "fox", "jumps", "over", "lazy", "dog"]:
            assert word_freq_dict[word].frequency == 1  # type: ignore
            assert abs(word_freq_dict[word].tf_score - (1/total_words)) < 1e-10  # type: ignore
