from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ParagraphBlock(BaseModel):
    kind: Literal["paragraph"] = "paragraph"
    text: str


class ListItem(BaseModel):
    text: str
    href: str | None = None


class HeadingBlock(BaseModel):
    kind: Literal["heading"] = "heading"
    level: int
    text: str


class ListBlock(BaseModel):
    kind: Literal["list"] = "list"
    ordered: bool
    items: list[ListItem]


class ImageBlock(BaseModel):
    kind: Literal["image"] = "image"
    title: str
    alt: str
    caption: str | None = None
    role: Literal["infobox", "body"] = "body"


class InfoboxLink(BaseModel):
    text: str
    href: str


class InfoboxField(BaseModel):
    label: str
    text: str
    links: list[InfoboxLink] = Field(default_factory=list)


class InfoboxImage(BaseModel):
    title: str
    path: str | None = None
    alt: str
    caption: str | None = None


class InfoboxData(BaseModel):
    title: str
    image: InfoboxImage | None = None
    fields: list[InfoboxField] = Field(default_factory=list)


class SectionEvidenceSource(BaseModel):
    id: str | None = None
    text: str
    primary_url: str | None = None
    link_kinds: list[str] = Field(default_factory=list)


class SectionEvidence(BaseModel):
    section_id: str
    heading: str
    level: int
    paragraph_count: int = 0
    reference_ids: list[str] = Field(default_factory=list)
    reference_count: int = 0
    primary_urls: list[str] = Field(default_factory=list)
    sources: list[SectionEvidenceSource] = Field(default_factory=list)


DocumentBlock = Annotated[
    ParagraphBlock | HeadingBlock | ListBlock | ImageBlock,
    Field(discriminator="kind"),
]


class Document(BaseModel):
    title: str
    infobox: InfoboxData | None = None
    summary: list[str] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)
    references: list["ReferenceEntry"] = Field(default_factory=list)
    section_evidence: list[SectionEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReferenceLink(BaseModel):
    text: str
    href: str
    kind: Literal["external", "wiki", "archive", "identifier", "other"]


class ReferenceEntry(BaseModel):
    id: str | None = None
    text: str
    primary_url: str | None = None
    links: list[ReferenceLink] = Field(default_factory=list)
