"""
Background Jobs (django-celery-beat) admin page + APIs.

Superuser-only.
"""

import io
import json
import sys
from typing import Any, Dict, Optional

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from .shared.decorators import superuser_required


@login_required
def background_jobs_view(request):
    """Render the Background Jobs React page (superuser-only)."""
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only superusers can access Background Jobs.")
    return render(request, "main/background_jobs_react.html")


def _json_body(request) -> Dict[str, Any]:
    try:
        return json.loads(request.body or "{}")
    except Exception:
        return {}


def _completion_notify_headers_from_request(request, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
    """
    When the UI sends send_completion_email, attach Celery message headers so the worker
    can email request.user (or completion_email override) after task_postrun.
    """
    from data_collection.services.user_task_completion_email import NOTIFY_COMPLETION_HEADER

    data = data or {}
    flag = data.get("send_completion_email")
    if flag not in (True, 1, "1", "true", "True", "yes", "on"):
        return None
    override = str(data.get("completion_email") or "").strip()
    user_em = (getattr(request.user, "email", None) or "").strip()
    email = override if (override and "@" in override) else user_em
    if not email:
        return None
    return {NOTIFY_COMPLETION_HEADER: email}


def _safe_json_dumps(value: Any, fallback: str) -> str:
    try:
        return json.dumps(value)
    except Exception:
        return fallback


def _safe_json_loads(text: Any, fallback: Any) -> Any:
    try:
        if text is None:
            return fallback
        if isinstance(text, (dict, list)):
            return text
        s = str(text).strip()
        if not s:
            return fallback
        return json.loads(s)
    except Exception:
        return fallback


def _serialize_periodic_task(obj) -> Dict[str, Any]:
    schedule_type = "unknown"
    interval_seconds: Optional[int] = None
    crontab: Optional[Dict[str, str]] = None

    if getattr(obj, "interval_id", None):
        schedule_type = "interval"
        interval = obj.interval
        try:
            if interval and str(interval.period).lower().startswith("second"):
                interval_seconds = int(interval.every)
            else:
                # For now keep only seconds in UI; still serialize as string fallback.
                interval_seconds = int(interval.every)
        except Exception:
            interval_seconds = None
    elif getattr(obj, "crontab_id", None):
        schedule_type = "crontab"
        c = obj.crontab
        if c:
            crontab = {
                "minute": str(c.minute),
                "hour": str(c.hour),
                "day_of_week": str(c.day_of_week),
                "day_of_month": str(c.day_of_month),
                "month_of_year": str(c.month_of_year),
            }

    return {
        "id": obj.id,
        "name": obj.name,
        "task": obj.task,
        "enabled": bool(obj.enabled),
        "queue": getattr(obj, "queue", None),
        "schedule_type": schedule_type,
        "interval_seconds": interval_seconds,
        "crontab": crontab,
        "args": obj.args or "[]",
        "kwargs": obj.kwargs or "{}",
        "description": getattr(obj, "description", None),
        "last_run_at": obj.last_run_at.isoformat() if getattr(obj, "last_run_at", None) else None,
        "total_run_count": int(getattr(obj, "total_run_count", 0) or 0),
    }


def _normalize_import_args(args_value: Any) -> str:
    return _safe_json_dumps(_safe_json_loads(args_value, []), "[]")


def _normalize_import_kwargs(kwargs_value: Any) -> str:
    return _safe_json_dumps(_safe_json_loads(kwargs_value, {}), "{}")


@superuser_required
@login_required
def api_background_jobs_data(request):
    """List background jobs (PeriodicTask). Superuser-only."""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask

        items = PeriodicTask.objects.all().order_by("name")
        data = [_serialize_periodic_task(obj) for obj in items]
        return JsonResponse({"data": data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_background_jobs_export(request):
    """Export all schedules and task names as JSON for download (superuser-only)."""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask

        items = PeriodicTask.objects.all().order_by("name")
        schedules = [_serialize_periodic_task(obj) for obj in items]
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    try:
        from web_app.celery_app import app

        _old_stdout = sys.stdout
        _old_stderr = sys.stderr
        try:
            _devnull = io.StringIO()
            sys.stdout = _devnull
            sys.stderr = _devnull
            try:
                app.autodiscover_tasks(force=True)
            except TypeError:
                app.autodiscover_tasks()
            try:
                app.loader.import_default_modules()
            except Exception:
                pass
            names = sorted(set(app.tasks.keys()))
        finally:
            sys.stdout = _old_stdout
            sys.stderr = _old_stderr
        hidden_prefixes = (
            "celery.",
            "kombu.",
            "amqp.",
            "django_celery_results.",
            "django_celery_beat.",
        )
        tasks = [n for n in names if not n.startswith(hidden_prefixes)]
    except Exception as e:
        tasks = []

    payload = {
        "exported_at": timezone.now().isoformat(),
        "schedules": schedules,
        "tasks": tasks,
    }
    json_str = json.dumps(payload, indent=2)
    response = HttpResponse(json_str, content_type="application/json")
    filename = f"background-jobs-export-{timezone.now().strftime('%Y-%m-%d-%H%M')}.json"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@superuser_required
@login_required
def api_background_jobs_import(request):
    """
    Import schedules from exported JSON (superuser-only).

    Safe behavior by default:
    - Creates only NEW jobs
    - Never modifies existing jobs unless replace_existing=true is provided
    - Validates task names against registered Celery tasks
    - Returns detailed created/skipped/errors report
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
        from web_app.celery_app import app

        uploaded = request.FILES.get("file")
        if not uploaded:
            return JsonResponse({"error": "file is required"}, status=400)
        if uploaded.size > 5 * 1024 * 1024:
            return JsonResponse({"error": "file is too large (max 5MB)"}, status=400)

        try:
            raw_text = uploaded.read().decode("utf-8")
        except UnicodeDecodeError:
            return JsonResponse({"error": "file must be UTF-8 encoded JSON"}, status=400)

        try:
            payload = json.loads(raw_text)
        except Exception:
            return JsonResponse({"error": "invalid JSON file"}, status=400)

        schedules = payload.get("schedules")
        if not isinstance(schedules, list):
            return JsonResponse({"error": "invalid format: expected top-level 'schedules' array"}, status=400)

        replace_existing_raw = (request.POST.get("replace_existing") or "").strip().lower()
        replace_existing = replace_existing_raw in ("1", "true", "yes", "on")

        _old_stdout, _old_stderr = sys.stdout, sys.stderr
        try:
            _devnull = io.StringIO()
            sys.stdout = _devnull
            sys.stderr = _devnull
            try:
                app.autodiscover_tasks(force=True)
            except TypeError:
                app.autodiscover_tasks()
            try:
                app.loader.import_default_modules()
            except Exception:
                pass
            registered_tasks = set(app.tasks.keys())
        finally:
            sys.stdout = _old_stdout
            sys.stderr = _old_stderr

        hidden_prefixes = (
            "celery.",
            "kombu.",
            "amqp.",
            "django_celery_results.",
            "django_celery_beat.",
        )
        allowed_tasks = {t for t in registered_tasks if not t.startswith(hidden_prefixes)}

        created_count = 0
        updated_count = 0
        skipped: list[Dict[str, str]] = []
        errors: list[Dict[str, str]] = []

        for index, item in enumerate(schedules):
            row_id = f"row_{index + 1}"
            if not isinstance(item, dict):
                errors.append({"item": row_id, "reason": "schedule entry must be an object"})
                continue

            name = str(item.get("name") or "").strip()
            task = str(item.get("task") or "").strip()
            if not name:
                errors.append({"item": row_id, "reason": "name is required"})
                continue
            if not task:
                errors.append({"item": name, "reason": "task is required"})
                continue
            if task not in allowed_tasks:
                errors.append({"item": name, "reason": f"task is not registered: {task}"})
                continue

            enabled = bool(item.get("enabled", True))
            queue = (str(item.get("queue")).strip() if item.get("queue") is not None else None) or None
            description = item.get("description", None)
            schedule_type = str(item.get("schedule_type") or "").strip().lower()
            args = _normalize_import_args(item.get("args"))
            kwargs = _normalize_import_kwargs(item.get("kwargs"))

            if schedule_type not in ("interval", "crontab"):
                errors.append({"item": name, "reason": "schedule_type must be interval or crontab"})
                continue

            try:
                interval = None
                crontab = None
                if schedule_type == "interval":
                    seconds = int(item.get("interval_seconds") or 0)
                    if seconds <= 0:
                        errors.append({"item": name, "reason": "interval_seconds must be > 0"})
                        continue
                    interval, _ = IntervalSchedule.objects.get_or_create(
                        every=seconds,
                        period=IntervalSchedule.SECONDS,
                    )
                else:
                    c = item.get("crontab") or {}
                    if not isinstance(c, dict):
                        errors.append({"item": name, "reason": "crontab must be an object"})
                        continue
                    fields = dict(
                        minute=str(c.get("minute", "*")),
                        hour=str(c.get("hour", "*")),
                        day_of_week=str(c.get("day_of_week", "*")),
                        day_of_month=str(c.get("day_of_month", "*")),
                        month_of_year=str(c.get("month_of_year", "*")),
                    )
                    if any(f.name == "timezone" for f in CrontabSchedule._meta.fields):
                        tz_name = str(
                            getattr(settings, "CELERY_TIMEZONE", None)
                            or getattr(settings, "TIME_ZONE", None)
                            or "UTC"
                        )
                        fields["timezone"] = tz_name
                    crontab, _ = CrontabSchedule.objects.get_or_create(**fields)

                existing = PeriodicTask.objects.filter(name=name).first()
                if existing and not replace_existing:
                    skipped.append({"item": name, "reason": "already exists"})
                    continue

                if existing and replace_existing:
                    existing.task = task
                    existing.enabled = enabled
                    existing.queue = queue
                    existing.description = description
                    existing.args = args
                    existing.kwargs = kwargs
                    existing.interval = interval
                    existing.crontab = crontab
                    existing.save()
                    updated_count += 1
                    continue

                PeriodicTask.objects.create(
                    name=name,
                    task=task,
                    enabled=enabled,
                    interval=interval,
                    crontab=crontab,
                    args=args,
                    kwargs=kwargs,
                    queue=queue,
                    description=description,
                )
                created_count += 1
            except Exception as ex:
                errors.append({"item": name or row_id, "reason": str(ex)})

        return JsonResponse(
            {
                "success": True,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped,
                "errors": errors,
                "replace_existing": replace_existing,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_background_job_tasks(request):
    """List registered Celery task names (superuser-only)."""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)

    try:
        from web_app.celery_app import app

        # Ensure tasks are discovered/imported in the current process.
        # In some deployments, only a subset of tasks are loaded until explicitly autodiscovered.
        # Suppress stdout and stderr during discovery to avoid Celery/introspection dumping
        # task signatures (e.g. "def task_name(...): return 1") to web logs.
        _old_stdout = sys.stdout
        _old_stderr = sys.stderr
        try:
            _devnull = io.StringIO()
            sys.stdout = _devnull
            sys.stderr = _devnull
            try:
                app.autodiscover_tasks(force=True)
            except TypeError:
                app.autodiscover_tasks()
            try:
                app.loader.import_default_modules()
            except Exception:
                pass
            names = sorted(set(app.tasks.keys()))
        finally:
            sys.stdout = _old_stdout
            sys.stderr = _old_stderr

        # Hide internal Celery/broker housekeeping tasks; keep app-level tasks visible.
        hidden_prefixes = (
            "celery.",
            "kombu.",
            "amqp.",
            "django_celery_results.",
            "django_celery_beat.",
        )
        filtered = [n for n in names if not n.startswith(hidden_prefixes)]

        return JsonResponse({"data": filtered})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_create_background_job(request):
    """Create a PeriodicTask. Superuser-only."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule

        data = _json_body(request)
        name = str(data.get("name") or "").strip()
        task = str(data.get("task") or "").strip()
        enabled = bool(data.get("enabled", True))
        queue = (str(data.get("queue")).strip() if data.get("queue") is not None else None) or None
        schedule_type = str(data.get("schedule_type") or "").strip().lower()
        args = data.get("args", "[]")
        kwargs = data.get("kwargs", "{}")
        description = data.get("description", None)

        if not name:
            return JsonResponse({"error": "name is required"}, status=400)
        if not task:
            return JsonResponse({"error": "task is required"}, status=400)
        if schedule_type not in ("interval", "crontab"):
            return JsonResponse({"error": "schedule_type must be 'interval' or 'crontab'"}, status=400)

        if PeriodicTask.objects.filter(name=name).exists():
            return JsonResponse({"error": f"A job with name '{name}' already exists"}, status=400)

        interval = None
        crontab = None
        if schedule_type == "interval":
            seconds = int(data.get("interval_seconds") or 0)
            if seconds <= 0:
                return JsonResponse({"error": "interval_seconds must be a positive integer"}, status=400)
            interval, _ = IntervalSchedule.objects.get_or_create(
                every=seconds,
                period=IntervalSchedule.SECONDS,
            )
        else:
            c = data.get("crontab") or {}
            minute = str(c.get("minute", "*"))
            hour = str(c.get("hour", "*"))
            day_of_week = str(c.get("day_of_week", "*"))
            day_of_month = str(c.get("day_of_month", "*"))
            month_of_year = str(c.get("month_of_year", "*"))

            fields = dict(
                minute=minute,
                hour=hour,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
            )
            # timezone field may exist depending on package version
            if any(f.name == "timezone" for f in CrontabSchedule._meta.fields):
                tz_name = str(getattr(settings, "CELERY_TIMEZONE", None) or getattr(settings, "TIME_ZONE", None) or "UTC")
                fields["timezone"] = tz_name
            crontab, _ = CrontabSchedule.objects.get_or_create(**fields)

        obj = PeriodicTask.objects.create(
            name=name,
            task=task,
            enabled=enabled,
            interval=interval,
            crontab=crontab,
            args=_safe_json_dumps(_safe_json_loads(args, []), "[]"),
            kwargs=_safe_json_dumps(_safe_json_loads(kwargs, {}), "{}"),
            queue=queue,
            description=description,
        )
        return JsonResponse({"success": True, "id": obj.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_update_background_job(request):
    """Update a PeriodicTask. Superuser-only."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule

        data = _json_body(request)
        job_id = data.get("id")
        if not job_id:
            return JsonResponse({"error": "id is required"}, status=400)

        obj = PeriodicTask.objects.get(id=job_id)

        if "name" in data:
            name = str(data.get("name") or "").strip()
            if not name:
                return JsonResponse({"error": "name cannot be empty"}, status=400)
            if PeriodicTask.objects.exclude(id=obj.id).filter(name=name).exists():
                return JsonResponse({"error": f"A job with name '{name}' already exists"}, status=400)
            obj.name = name

        if "task" in data:
            task = str(data.get("task") or "").strip()
            if not task:
                return JsonResponse({"error": "task cannot be empty"}, status=400)
            obj.task = task

        if "enabled" in data:
            obj.enabled = bool(data.get("enabled"))

        if "queue" in data:
            queue = (str(data.get("queue")).strip() if data.get("queue") is not None else None) or None
            obj.queue = queue

        if "description" in data:
            obj.description = data.get("description", None)

        if "args" in data:
            obj.args = _safe_json_dumps(_safe_json_loads(data.get("args"), []), "[]")

        if "kwargs" in data:
            obj.kwargs = _safe_json_dumps(_safe_json_loads(data.get("kwargs"), {}), "{}")

        if "schedule_type" in data:
            schedule_type = str(data.get("schedule_type") or "").strip().lower()
            if schedule_type not in ("interval", "crontab"):
                return JsonResponse({"error": "schedule_type must be 'interval' or 'crontab'"}, status=400)

            if schedule_type == "interval":
                seconds = int(data.get("interval_seconds") or 0)
                if seconds <= 0:
                    return JsonResponse({"error": "interval_seconds must be a positive integer"}, status=400)
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=seconds,
                    period=IntervalSchedule.SECONDS,
                )
                obj.interval = interval
                obj.crontab = None
            else:
                c = data.get("crontab") or {}
                minute = str(c.get("minute", "*"))
                hour = str(c.get("hour", "*"))
                day_of_week = str(c.get("day_of_week", "*"))
                day_of_month = str(c.get("day_of_month", "*"))
                month_of_year = str(c.get("month_of_year", "*"))

                fields = dict(
                    minute=minute,
                    hour=hour,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year,
                )
                if any(f.name == "timezone" for f in CrontabSchedule._meta.fields):
                    tz_name = str(getattr(settings, "CELERY_TIMEZONE", None) or getattr(settings, "TIME_ZONE", None) or "UTC")
                    fields["timezone"] = tz_name
                crontab, _ = CrontabSchedule.objects.get_or_create(**fields)
                obj.crontab = crontab
                obj.interval = None

        obj.save()
        return JsonResponse({"success": True})
    except PeriodicTask.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_delete_background_job(request, job_id: int):
    """Delete a PeriodicTask. Superuser-only."""
    if request.method != "DELETE":
        return JsonResponse({"error": "Only DELETE method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask

        obj = PeriodicTask.objects.get(id=job_id)
        obj.delete()
        return JsonResponse({"success": True})
    except PeriodicTask.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_run_background_job_now(request, job_id: int):
    """Enqueue the job once immediately (superuser-only)."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        from django_celery_beat.models import PeriodicTask
        from web_app.celery_app import app

        obj = PeriodicTask.objects.get(id=job_id)
        args = _safe_json_loads(obj.args, [])
        kwargs = _safe_json_loads(obj.kwargs, {})
        # Use high-priority queue for acquisition tasks (5-min, 30-min, hourly); others default.
        queue = getattr(obj, "queue", None) or None
        if obj.task not in (
            "data_collection.tasks.run_data_acquisition",
            "data_collection.tasks.run_data_acquisition_30min",
            "data_collection.tasks.run_data_acquisition_hourly",
            "data_collection.tasks.run_laplace_span_historical_backfill",
        ):
            queue = None  # default queue

        notify_headers = _completion_notify_headers_from_request(request, _json_body(request))
        send_kw: Dict[str, Any] = {
            "args": args if isinstance(args, list) else [],
            "kwargs": kwargs if isinstance(kwargs, dict) else {},
            "queue": queue,
        }
        if notify_headers:
            send_kw["headers"] = notify_headers
        async_result = app.send_task(obj.task, **send_kw)
        return JsonResponse({"success": True, "task_id": async_result.id})
    except PeriodicTask.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_run_task_on_demand(request):
    """
    Run any Celery task on demand by name (superuser-only).
    Does not require a PeriodicTask schedule.
    POST body: { "task": "module.path.task_name", "args": [], "kwargs": {}, "queue": "optional" }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        from web_app.celery_app import app

        data = _json_body(request)
        task_name = str(data.get("task") or "").strip()
        if not task_name:
            return JsonResponse({"error": "task is required"}, status=400)

        args = _safe_json_loads(data.get("args"), [])
        kwargs = _safe_json_loads(data.get("kwargs"), {}) or {}
        if not isinstance(kwargs, dict):
            kwargs = {}
        queue = (str(data.get("queue")).strip() if data.get("queue") is not None else None) or None
        # On-demand: acquisition tasks use high-priority queue; others use default.
        acquisition_tasks = {
            "data_collection.tasks.run_data_acquisition",
            "data_collection.tasks.run_data_acquisition_30min",
            "data_collection.tasks.run_data_acquisition_hourly",
            "data_collection.tasks.run_laplace_span_historical_backfill",
        }
        if queue is None:
            queue = "data_acquisition" if task_name in acquisition_tasks else "default"

        # When running run_solargis_daily_ingest on demand, inject on_demand=True and
        # ensure date_from/date_to and optional asset_codes from body are passed through.
        if task_name == "data_collection.tasks.run_solargis_daily_ingest":
            kwargs["on_demand"] = True
            # Solargis runs on default queue so multiple assets can be processed in parallel
            for key in ("date_from", "date_to"):
                val = data.get(key)
                if val is not None and str(val).strip():
                    kwargs[key] = str(val).strip()
            raw_asset_codes = data.get("asset_codes")
            if raw_asset_codes is not None:
                if isinstance(raw_asset_codes, str):
                    try:
                        raw_asset_codes = json.loads(raw_asset_codes)
                    except (TypeError, ValueError):
                        raw_asset_codes = []
                if isinstance(raw_asset_codes, list) and len(raw_asset_codes) > 0:
                    kwargs["asset_codes"] = [str(c).strip() for c in raw_asset_codes if c is not None and str(c).strip()]
        # Daily KPI backfill: merge top-level date range and optional asset_codes into task kwargs.
        if task_name == "main.tasks.compute_daily_kpis_previous_day":
            for key in ("date_from", "date_to"):
                val = data.get(key)
                if val is not None and str(val).strip():
                    kwargs[key] = str(val).strip()
            raw_asset_codes = data.get("asset_codes")
            if raw_asset_codes is not None:
                if isinstance(raw_asset_codes, str):
                    try:
                        raw_asset_codes = json.loads(raw_asset_codes)
                    except (TypeError, ValueError):
                        raw_asset_codes = []
                if isinstance(raw_asset_codes, list) and len(raw_asset_codes) > 0:
                    kwargs["asset_codes"] = [str(c).strip() for c in raw_asset_codes if c is not None and str(c).strip()]
        # On-demand acquisition runs always execute; inject sun_hours_check=False.
        if task_name in (
            "data_collection.tasks.run_data_acquisition",
            "data_collection.tasks.run_data_acquisition_30min",
            "data_collection.tasks.run_data_acquisition_hourly",
        ):
            kwargs["sun_hours_check"] = False

        # Ensure task registry is populated in this process (e.g. other gunicorn workers
        # may not have loaded tasks yet), so the "not registered" check is reliable.
        _old_stdout, _old_stderr = sys.stdout, sys.stderr
        try:
            _devnull = io.StringIO()
            sys.stdout = sys.stderr = _devnull
            try:
                app.autodiscover_tasks(force=True)
            except TypeError:
                app.autodiscover_tasks()
            try:
                app.loader.import_default_modules()
            except Exception:
                pass
        finally:
            sys.stdout, sys.stderr = _old_stdout, _old_stderr

        if task_name not in app.tasks:
            return JsonResponse({"error": f"Task '{task_name}' is not registered"}, status=400)

        notify_headers = _completion_notify_headers_from_request(request, data)
        send_kw: Dict[str, Any] = {
            "args": args if isinstance(args, list) else [],
            "kwargs": kwargs if isinstance(kwargs, dict) else {},
            "queue": queue,
        }
        if notify_headers:
            send_kw["headers"] = notify_headers
        async_result = app.send_task(task_name, **send_kw)
        return JsonResponse({"success": True, "task_id": async_result.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_solargis_source_assets(request):
    """
    Return list of Solargis-configured asset codes (superuser-only).
    All assets with adapter_id=solargis, enabled=True, and present in AssetList are treated
    as sources (they run the ingest). Linking to other assets as consumers is done later.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)

    try:
        from data_collection.models import AssetAdapterConfig
        from main.models import AssetList

        configs = list(
            AssetAdapterConfig.objects.filter(adapter_id="solargis", enabled=True).values_list(
                "asset_code", flat=True
            )
        )
        asset_codes = []
        for asset_code in configs:
            try:
                AssetList.objects.get(asset_code=asset_code)
            except AssetList.DoesNotExist:
                continue
            asset_codes.append(asset_code)
        return JsonResponse({
            "asset_codes": sorted(asset_codes),
            "all_configured_count": len(asset_codes),
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_solargis_daily_api_calls(request):
    """Return total Solargis API calls made today (superuser-only). Stored in data_collection_last_written_reading."""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)

    try:
        from data_collection.services.solargis_daily_calls import get_solargis_daily_api_calls
        from django.utils import timezone

        today = timezone.now().date().isoformat()
        total = get_solargis_daily_api_calls()
        return JsonResponse({"date": today, "total_api_calls": int(total)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_fusion_solar_backfill_assets(request):
    """
    Return list of adapter-configured asset codes (superuser-only) for Fusion Solar backfill UI.

    Optional query params:
    - adapter_id (default "fusion_solar")
    - adapter_account_id (int, optional) to restrict to a specific account.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)
    try:
        from data_collection.models import AssetAdapterConfig
        from main.models import AssetList

        adapter_id = request.GET.get("adapter_id", "fusion_solar").strip() or "fusion_solar"
        adapter_account_id_raw = request.GET.get("adapter_account_id")
        adapter_account_id = None
        if adapter_account_id_raw not in (None, ""):
            try:
                adapter_account_id = int(adapter_account_id_raw)
            except (TypeError, ValueError):
                return JsonResponse({"error": "adapter_account_id must be an integer"}, status=400)

        qs = AssetAdapterConfig.objects.filter(adapter_id=adapter_id)
        if adapter_account_id is not None:
            qs = qs.filter(adapter_account_id=adapter_account_id)
        configs = list(qs.values_list("asset_code", flat=True))
        asset_codes = []
        for asset_code in configs:
            try:
                AssetList.objects.get(asset_code=asset_code)
            except AssetList.DoesNotExist:
                continue
            asset_codes.append(asset_code)
        return JsonResponse({"asset_codes": sorted(asset_codes)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_laplace_backfill_assets(request):
    """
    Return list of adapter-configured asset codes (superuser-only) for Laplace span backfill UI.

    Optional query params:
    - adapter_id (default "laplaceid")
    - adapter_account_id (int, optional) to restrict to a specific account.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)
    try:
        from data_collection.models import AssetAdapterConfig
        from main.models import AssetList

        adapter_id = request.GET.get("adapter_id", "laplaceid").strip() or "laplaceid"
        adapter_account_id_raw = request.GET.get("adapter_account_id")
        adapter_account_id = None
        if adapter_account_id_raw not in (None, ""):
            try:
                adapter_account_id = int(adapter_account_id_raw)
            except (TypeError, ValueError):
                return JsonResponse({"error": "adapter_account_id must be an integer"}, status=400)

        qs = AssetAdapterConfig.objects.filter(adapter_id=adapter_id, enabled=True)
        if adapter_account_id is not None:
            qs = qs.filter(adapter_account_id=adapter_account_id)
        configs = list(qs.values_list("asset_code", flat=True))
        asset_codes = []
        for asset_code in configs:
            try:
                AssetList.objects.get(asset_code=asset_code)
            except AssetList.DoesNotExist:
                continue
            asset_codes.append(asset_code)
        return JsonResponse({"asset_codes": sorted(asset_codes)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_fusion_solar_backfill_run(request):
    """
    Start Fusion Solar backfill task (superuser-only).
    POST body: { "asset_codes": ["A1","A2"], "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD" }
    Returns { "success": true, "task_id": "..." }.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        from web_app.celery_app import app

        data = _json_body(request)
        asset_codes = data.get("asset_codes")
        if not isinstance(asset_codes, list):
            asset_codes = []
        asset_codes = [str(c).strip() for c in asset_codes if c and str(c).strip()]
        date_from = (data.get("date_from") or "").strip()
        date_to = (data.get("date_to") or "").strip()
        if not date_from or not date_to:
            return JsonResponse({"error": "date_from and date_to are required (YYYY-MM-DD)"}, status=400)
        if not asset_codes:
            return JsonResponse({"error": "Select at least one asset"}, status=400)

        adapter_id = (data.get("adapter_id") or "fusion_solar").strip() or "fusion_solar"
        adapter_account_id = data.get("adapter_account_id")
        if adapter_account_id in ("", None):
            adapter_account_id = None

        task_name = "data_collection.tasks.run_fusion_solar_backfill"
        _old_stdout, _old_stderr = sys.stdout, sys.stderr
        try:
            _devnull = io.StringIO()
            sys.stdout = sys.stderr = _devnull
            try:
                app.autodiscover_tasks(force=True)
            except TypeError:
                app.autodiscover_tasks()
            try:
                app.loader.import_default_modules()
            except Exception:
                pass
        finally:
            sys.stdout, sys.stderr = _old_stdout, _old_stderr

        if task_name not in app.tasks:
            return JsonResponse({"error": "Backfill task not registered"}, status=500)

        notify_headers = _completion_notify_headers_from_request(request, data)
        send_kw: Dict[str, Any] = {
            "kwargs": {
                "asset_codes": asset_codes,
                "date_from": date_from,
                "date_to": date_to,
                "adapter_id": adapter_id,
                "adapter_account_id": adapter_account_id,
            },
            "queue": "default",
        }
        if notify_headers:
            send_kw["headers"] = notify_headers
        async_result = app.send_task(task_name, **send_kw)
        return JsonResponse({"success": True, "task_id": async_result.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@superuser_required
@login_required
def api_fusion_solar_oem_daily_kpi_run(request):
    """
    Start Fusion Solar OEM daily KPI sync only: getDevKpiDay for devTypeId 1 (string inverters) → upsert kpis.oem_daily_product_kwh.
    Does not run 5-minute historical backfill. Superuser-only.
    POST body: asset_codes, adapter_id, adapter_account_id; date_from/date_to = inclusive month range (YYYY-MM or YYYY-MM-DD).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        from web_app.celery_app import app

        data = _json_body(request)
        asset_codes = data.get("asset_codes")
        if not isinstance(asset_codes, list):
            asset_codes = []
        asset_codes = [str(c).strip() for c in asset_codes if c and str(c).strip()]
        date_from = (data.get("date_from") or "").strip()
        date_to = (data.get("date_to") or "").strip()
        if not date_from or not date_to:
            return JsonResponse(
                {"error": "date_from and date_to are required (YYYY-MM or YYYY-MM-DD month range)"},
                status=400,
            )
        if not asset_codes:
            return JsonResponse({"error": "Select at least one asset"}, status=400)

        adapter_id = (data.get("adapter_id") or "fusion_solar").strip() or "fusion_solar"
        adapter_account_id = data.get("adapter_account_id")
        if adapter_account_id in ("", None):
            adapter_account_id = None
        elif isinstance(adapter_account_id, str) and adapter_account_id.isdigit():
            adapter_account_id = int(adapter_account_id)

        task_name = "data_collection.tasks.run_fusion_solar_oem_daily_kpi"
        _old_stdout, _old_stderr = sys.stdout, sys.stderr
        try:
            _devnull = io.StringIO()
            sys.stdout = sys.stderr = _devnull
            try:
                app.autodiscover_tasks(force=True)
            except TypeError:
                app.autodiscover_tasks()
            try:
                app.loader.import_default_modules()
            except Exception:
                pass
        finally:
            sys.stdout, sys.stderr = _old_stdout, _old_stderr

        if task_name not in app.tasks:
            return JsonResponse({"error": "OEM daily KPI task not registered"}, status=500)

        notify_headers = _completion_notify_headers_from_request(request, data)
        send_kw: Dict[str, Any] = {
            "kwargs": {
                "asset_codes": asset_codes,
                "date_from": date_from,
                "date_to": date_to,
                "adapter_id": adapter_id,
                "adapter_account_id": adapter_account_id,
            },
            "queue": "default",
        }
        if notify_headers:
            send_kw["headers"] = notify_headers
        async_result = app.send_task(task_name, **send_kw)
        return JsonResponse({"success": True, "task_id": async_result.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

