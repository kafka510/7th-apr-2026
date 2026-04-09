"""Celery hooks: optional completion email for user-initiated tasks (see user_task_completion_email)."""

import logging

from celery.signals import task_postrun

logger = logging.getLogger(__name__)


@task_postrun.connect
def _email_user_after_task(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    try:
        task_obj = task if task is not None else sender
        if task_obj is None:
            return
        name = getattr(task_obj, "name", None) or ""
        name = str(name).strip()
        if not name:
            return
        from data_collection.services.user_task_completion_email import maybe_notify_from_postrun

        maybe_notify_from_postrun(
            task_name=name,
            task_id=str(task_id) if task_id else None,
            task=task_obj,
            state=state,
            retval=retval,
        )
    except Exception:
        logger.debug("task_postrun completion email hook failed", exc_info=True)
