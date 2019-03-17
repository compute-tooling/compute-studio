from dataclasses import dataclass, field
from typing import List, Union


@dataclass
class Tag:
    key: str
    values: List["TagOption"]
    hidden: bool = True


@dataclass
class TagOption:
    value: str
    title: str
    tooltip: Union[str, None] = None
    active: bool = False
    children: List[Tag] = field(default_factory=list)


matchups_tags = {
    "tags": [
        Tag(
            key="attribute",
            hidden=False,
            values=[
                TagOption(
                    value="pitch-outcome",
                    title="Pitch Outcome Table",
                    tooltip="Pitch outcome tooltip",
                    active=True,
                ),
                TagOption(
                    value="pitch-type",
                    title="Pitch Type Table",
                    tooltip="Pitch type tooltip",
                ),
            ],
        ),
        Tag(
            key="count",
            hidden=False,
            values=[
                TagOption(title="Normalized", value="normalized", tooltip="Normalized"),
                TagOption(
                    title="Count", value="raw-count", active=True, tooltip="Count"
                ),
            ],
        ),
    ],
    "aggr_tags": [
        Tag(
            key="attribute",
            hidden=False,
            values=[
                TagOption(title="Pitch Outcome", value="pitch-outcome"),
                TagOption(title="Pitch Type", value="pitch-type", active=True),
            ],
        )
    ],
}

TAGS = {"Matchups": matchups_tags}
