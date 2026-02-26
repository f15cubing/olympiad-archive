from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, func, Table
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
    country = Column(Text)
    url = Column(Text)
    problems = relationship("Problem", back_populates="competition")

class Problem(Base):
    __tablename__ = "problems"
    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"))
    year = Column(Integer, nullable=False)
    problem_number = Column(Integer, nullable=False)
    statement = Column(Text, nullable=False) # LaTeX source [cite: 82]
    difficulty = Column(Integer) # 1-10 [cite: 83]
    source_url = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    competition = relationship("Competition", back_populates="problems")
    solutions = relationship("Solution", back_populates="problem", cascade="all, delete")
    tags = relationship("Tag", secondary=problem_tags, back_populates="problems")

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
