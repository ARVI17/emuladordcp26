from typing import Literal
from pydantic import Field
from app.schemas.api import InputModel


class WorkflowAction(InputModel):
    action: Literal['pause', 'resume', 'cancel']


class ViewState(InputModel):
    # Only enumerated facts, never arbitrary page text, URLs or credentials.
    code: Literal['permission_required', 'context_required', 'sensitive_screen', 'profile_required',
        'authorization_required', 'ready_sample', 'loading', 'offline', 'structure_changed', 'paused']
    candidate_regions: int = Field(default=0, ge=0, le=12)
    profile_verified: bool = False
    source: Literal['unknown', 'synthetic_dom', 'user_export_dom', 'observed_page_dom'] = 'unknown'
