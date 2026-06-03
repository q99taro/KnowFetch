import uuid
import enum
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class NodeLabel(enum.Enum):
    Technology = "Technology"
    Library = "Library"
    Concept = "Concept"
    Method = "Method"
    Syntax_Example = "Syntax_Example"

class EdgeRelation(enum.Enum):
    BELONGS_TO = "BELONGS_TO"
    IMPLEMENTS = "IMPLEMENTS"
    ILLUSTRATES = "ILLUSTRATES"

class Node(Base):
    __tablename__ = "nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(Enum(NodeLabel), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)

    # FSRS 排程參數
    difficulty = Column(Float, default=0.0)
    stability = Column(Float, default=0.0)
    retrievability = Column(Float, default=0.0)
    due_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 設置 SQLAlchemy 的關係，方便查詢關聯的目標與來源節點
    edges_out = relationship("Edge", foreign_keys="Edge.source_id", back_populates="source_node", cascade="all, delete-orphan")
    edges_in = relationship("Edge", foreign_keys="Edge.target_id", back_populates="target_node", cascade="all, delete-orphan")

class Edge(Base):
    __tablename__ = "edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(Enum(EdgeRelation), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'relation_type', name='uix_source_target_relation'),
    )

    source_node = relationship("Node", foreign_keys=[source_id], back_populates="edges_out")
    target_node = relationship("Node", foreign_keys=[target_id], back_populates="edges_in")
