from typing import TypedDict, NotRequired, Required

#Define the input state
class InputState(TypedDict, total=False):
    company: Required[str]
    company_url: NotRequired[str]
    hq_location: NotRequired[str]
    industry: NotRequired[str]

class ResearchState(TypedDict):
    site_scrape: dict
    messages: list

class OutputState(TypedDict):
    report: str