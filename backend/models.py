from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, func, Table, JSON, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", Integer, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Competition(Base):
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False) # e.g. 'IMO' [cite: 73]
    description = Column(Text, nullable=True)  # optional long description supplied by frontend
    country = Column(Text)
    url = Column(Text)
    problems = relationship("Problem", back_populates="competition")

class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        # One row per contest problem; the importer upserts on this key.
        UniqueConstraint("competition_id", "year", "problem_number",
                         name="uq_problem_comp_year_number"),
    )
    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"))
    year = Column(Integer, nullable=False)
    problem_number = Column(Integer, nullable=False)
    statement = Column(Text, nullable=False) # LaTeX source [cite: 82]
    author = Column(Text, nullable=True) # Problem author (optional)
    difficulty = Column(Integer) # 1-10 [cite: 83]
    source_url = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # AI-generated metadata (from Gemini)
    ai_metadata = Column(JSON, nullable=True)  # Stores complete AI response: {field, difficulty, techniques, topics, analysis, confidence_score}
    tagged_at = Column(TIMESTAMP, nullable=True)  # Timestamp of when AI tagging was performed

    # Parallel Claude tagging (stored separately so Gemini's ai_metadata is never touched;
    # the two can be compared per problem to decide a routing policy). Same AITagMetadata shape.
    claude_metadata = Column(JSON, nullable=True)
    claude_tagged_at = Column(TIMESTAMP, nullable=True)

    # Semantic-search embedding of the statement (Phase C). Vector stored as a JSON list of
    # floats; numpy-cosine ranking is fine at a few-thousand rows.
    embedding = Column(JSON, nullable=True)
    embedding_model = Column(Text, nullable=True)
    embedded_at = Column(TIMESTAMP, nullable=True)

    competition = relationship("Competition", back_populates="problems", lazy="selectin")
    solutions = relationship("Solution", back_populates="problem", cascade="all, delete", lazy="selectin")
    tags = relationship("Tag", secondary=problem_tags, back_populates="problems", lazy="selectin")

class Solution(Base):
    __tablename__ = "solutions"
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False) # LaTeX source [cite: 91]
    author = Column(Text, default="Official")
    created_at = Column(TIMESTAMP, server_default=func.now())

    problem = relationship("Problem", back_populates="solutions")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False, unique=True)

    problems = relationship("Problem", secondary=problem_tags, back_populates="tags")
