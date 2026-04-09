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


DocumentBlock = Annotated[
    ParagraphBlock | HeadingBlock | ListBlock | ImageBlock,
    Field(discriminator="kind"),
]


class Document(BaseModel):
    title: str
    summary: list[str] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)
    references: list["ReferenceEntry"] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReferenceLink(BaseModel):
    text: str
    href: str


class ReferenceEntry(BaseModel):
    id: str | None = None
    text: str
    links: list[ReferenceLink] = Field(default_factory=list)
