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
    "dimension": "Batters",
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

taxbrain_tags = {
    "dimension": "Years",
    "tags": [
        Tag(
            key="table_type",
            hidden=False,
            values=[
                TagOption(
                    value="dist",
                    title="Distribution Table",
                    tooltip="Distribution tooltip",
                    children=[
                        Tag(
                            key="law",
                            hidden=True,
                            values=[
                                TagOption(
                                    value="current",
                                    title="Current Law",
                                    active=True,
                                    tooltip="base tooltip",
                                ),
                                TagOption(
                                    value="reform",
                                    title="Reform",
                                    tooltip="reform tooltip",
                                ),
                            ],
                        )
                    ],
                ),
                TagOption(
                    value="diff",
                    title="Difference Table",
                    tooltip="difference tooltip",
                    active=True,
                    children=[
                        Tag(
                            key="tax_type",
                            hidden=False,
                            values=[
                                TagOption(
                                    value="payroll",
                                    title="Payroll Tax",
                                    tooltip="income tooltip",
                                ),
                                TagOption(
                                    value="ind_income",
                                    title="Income Tax",
                                    tooltip="income tooltip",
                                ),
                                TagOption(
                                    value="combined",
                                    title="Combined",
                                    active=True,
                                    tooltip="",
                                ),
                            ],
                        )
                    ],
                ),
            ],
        ),
        Tag(
            key="grouping",
            hidden=False,
            values=[
                TagOption(
                    value="bins",
                    title="Income Bins",
                    active=True,
                    tooltip="income bins tooltip",
                ),
                TagOption(
                    value="deciles",
                    title="Income Deciles",
                    tooltip="income deciles tooltip",
                ),
            ],
        ),
    ],
    "aggr_tags": [
        Tag(
            key="law",
            hidden=False,
            values=[
                TagOption(value="current", title="Current Law"),
                TagOption(value="reform", title="Reform"),
                TagOption(value="change", title="Change", active=True),
            ],
        )
    ],
}

TAGS = {"Matchups": matchups_tags, "Tax-Brain": taxbrain_tags}
