import logging
from typing import Any
from uuid import UUID

from langchain.tools import tool
from tortoise.exceptions import IntegrityError

from src.common.base_repo import BaseRepository
from src.modules.application.models import Application
from src.modules.application.repository import ApplicationRepository
from src.modules.jd.models import JobDescription
from src.modules.jd.repository import JDRepository
from src.modules.response.models import Response, ResponseStatus
from src.modules.response.repository import ResponseRepository

logger = logging.getLogger(__name__)

application_repo = ApplicationRepository()
jd_repo = JDRepository()
response_repo = ResponseRepository()

ALLOWED_FALLBACK_LABELS = {"needs_info", "unclear"}


def serialize_model(obj: Any) -> Any:
    """Convert Pydantic DTOs and ordinary values into tool-friendly data."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    return obj


@tool("get_applicant", description="Retrieve an application by its UUID.")
async def get_applicant(application_id: str) -> dict[str, Any]:
    """Retrieve the applicant and associated job information."""
    try:
        UUID(application_id)
        applicant = await application_repo.agent_fetch(id=application_id)
        return serialize_model(applicant)
    except ValueError:
        raise ValueError("application_id must be a valid UUID.")
    except Exception:
        logger.exception("Failed to retrieve application %s", application_id)
        raise


@tool(
    "get_job_description",
    description=(
        "Retrieve a job description, its requirements, and its saved "
        "classification scheme by UUID."
    ),
)
async def get_job_description(jd_id: str) -> dict[str, Any]:
    """Retrieve a job description for classification or screening."""
    try:
        UUID(jd_id)
        jd = await jd_repo.agent_fetch(id=jd_id)
        return serialize_model(jd)
    except ValueError:
        raise ValueError("jd_id must be a valid UUID.")
    except Exception:
        logger.exception("Failed to retrieve job description %s", jd_id)
        raise


@tool(
    "submit_scheme",
    description=(
        "Save the complete classification scheme for a job description. "
        "Call only after designing and validating all categories."
    ),
)
async def submit_scheme(
    jd_id: str,
    categories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist the generated job-specific classification scheme."""
    try:
        UUID(jd_id)

        if not 3 <= len(categories) <= 6:
            raise ValueError("The scheme must contain 3 to 6 categories.")

        required_fields = {"label", "description", "criteria", "reply_goal"}
        labels: list[str] = []

        for category in categories:
            if not isinstance(category, dict):
                raise ValueError("Each category must be an object.")

            missing = required_fields - category.keys()
            if missing:
                raise ValueError(
                    f"Category is missing fields: {', '.join(sorted(missing))}"
                )

            label = category["label"]
            if not isinstance(label, str) or not label.strip():
                raise ValueError("Every category must have a non-empty label.")

            if label in ALLOWED_FALLBACK_LABELS:
                raise ValueError(
                    f"{label!r} is reserved for downstream classification."
                )

            if not all(
                isinstance(category[field], str) and category[field].strip()
                for field in ("description", "reply_goal")
            ):
                raise ValueError(
                    "Category description and reply_goal must be non-empty strings."
                )

            criteria = category["criteria"]
            if (
                not isinstance(criteria, list)
                or not criteria
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in criteria
                )
            ):
                raise ValueError(
                    "Each category must have a non-empty list of criteria."
                )

            labels.append(label)

        if len(labels) != len(set(labels)):
            raise ValueError("Category labels must be unique.")

        # Fetch the actual ORM model, not a DTO.
        jd = await JobDescription.get_or_none(id=jd_id)
        if jd is None:
            raise ValueError(f"Job description {jd_id} was not found.")

        await jd_repo.update(
            jd,
            generated_classification=categories,
        )

        return {
            "success": True,
            "jd_id": jd_id,
            "message": "Classification scheme saved successfully.",
            "categories_saved": len(categories),
        }

    except Exception:
        logger.exception("Failed to save classification scheme for %s", jd_id)
        raise


@tool(
    "generate_application_response",
    description=(
        "Create a draft reply for an application. Provide its UUID, "
        "a valid classification label, reviewer-only reason, and email draft."
    ),
)
async def generate_application_response(
    application_id: str,
    classification: str,
    classification_reason: str,
    generated_response: str,
) -> dict[str, Any]:
    """Save a draft for human review. Never send the email."""
    try:
        UUID(application_id)

        if not classification.strip():
            raise ValueError("Classification cannot be empty.")

        if not generated_response.strip():
            raise ValueError("The email draft cannot be empty.")

        # Confirm that the application exists.
        application = await Application.get_or_none(id=application_id)
        if application is None:
            raise ValueError(f"Application {application_id} was not found.")

        # Store the original draft in both fields so the reviewer can
        # edit authored_response independently later.
        response = await response_repo.create(
            application_id=application_id,
            classification=classification,
            classification_reason=classification_reason,
            generated_response=generated_response,
            authored_response=generated_response,
            status=ResponseStatus.DRAFT,
        )

        return {
            "success": True,
            "response_id": str(response.id),
            "application_id": application_id,
            "status": ResponseStatus.DRAFT.value,
            "message": "Draft saved for human review.",
        }

    except Exception:
        logger.exception(
            "Failed to create response draft for application %s",
            application_id,
        )
        raise


screening_tools = [
    get_applicant,
    get_job_description,
    generate_application_response,
]

classifying_tools = [
    get_job_description,
    submit_scheme,
]
