"""
Loss analytics API views.

Trigger endpoints enqueue Celery tasks and return task_id only (no long-running
work in the request). Client polls task status endpoint to avoid timeouts.
Read endpoints (results, summary, metric-mappings) delegate to main services.
"""
import json
import logging
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q

from accounts.decorators import login_required, role_required, role_required_api

from loss_analytics.tasks import transpose_asset_ghi_to_gii, run_asset_loss_pipeline
from loss_analytics.models import LossEvent, LossEventConfirmationLog
from main.models import AssetList, timeseries_data, LossCalculationTask, log_loss_task_enqueued

logger = logging.getLogger(__name__)


def _get_task_status(task_id: str) -> dict:
    """Return status dict for a Celery task (state, result, error)."""
    try:
        from celery.result import AsyncResult
        from web_app.celery_app import app
        ar = AsyncResult(task_id, app=app)
        try:
            state = ar.state
        except AttributeError as e:
            # When result backend is disabled/misconfigured, AsyncResult.state can raise.
            # Fall back to LossCalculationTask (DB) if available.
            msg = str(e)
            if "_get_task_meta_for" in msg or "DisabledBackend" in msg:
                obj = LossCalculationTask.objects.filter(task_id=task_id).first()
                if obj:
                    mapped = {
                        "pending": "PENDING",
                        "running": "STARTED",
                        "success": "SUCCESS",
                        "failure": "FAILURE",
                    }.get((obj.status or "").lower(), "UNKNOWN")
                    return {
                        "task_id": task_id,
                        "status": mapped,
                        "result": None,
                        "error": obj.error_message if mapped == "FAILURE" else None,
                    }
                return {
                    "task_id": task_id,
                    "status": "UNKNOWN",
                    "result": None,
                    "error": "Task result backend is disabled; configure CELERY_RESULT_BACKEND (recommended: django-db).",
                }
            raise
        result = None
        error = None
        if state == "SUCCESS":
            result = ar.result
        elif state == "FAILURE":
            try:
                error = str(ar.result) if ar.result else "Task failed"
            except Exception:
                error = "Task failed"
        return {
            "task_id": task_id,
            "status": state,
            "result": result,
            "error": error,
        }
    except Exception as e:
        # Avoid noisy traceback spam during polling for known backend/config issues.
        logger.warning("get_task_status failed: %s", e)
        return {"task_id": task_id, "status": "UNKNOWN", "error": str(e)}


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_transpose_trigger(request):
    """
    Trigger GHI→GII transposition. Enqueues a Celery task and returns immediately
    with task_id. Client should poll GET /api/loss/task/<task_id>/ for status.

    POST body (JSON):
      asset_code: str
      irradiance_device_id: str
      start_date: str (ISO or date)
      end_date: str (ISO or date)
      metric: str (default "ghi")
    """
    try:
        body = json.loads(request.body) if request.body else {}
        asset_code = (body.get("asset_code") or "").strip()
        irradiance_device_id = (body.get("irradiance_device_id") or "").strip()
        start_date = body.get("start_date")
        end_date = body.get("end_date")
        metric = (body.get("metric") or "ghi").strip() or "ghi"

        if not asset_code:
            return JsonResponse({"error": "asset_code is required"}, status=400)
        if not irradiance_device_id:
            return JsonResponse({"error": "irradiance_device_id is required"}, status=400)
        if not start_date or not end_date:
            return JsonResponse({"error": "start_date and end_date are required"}, status=400)

        task = transpose_asset_ghi_to_gii.apply_async(
            kwargs={
                "asset_code": asset_code,
                "irradiance_device_id": irradiance_device_id,
                "start_date": start_date,
                "end_date": end_date,
                "metric": metric,
            },
            queue="default",
        )
        try:
            log_loss_task_enqueued(
                task_id=task.id,
                task_name="loss_analytics.transpose_asset_ghi_to_gii",
                asset_code=asset_code,
                user=getattr(request, "user", None),
            )
        except Exception:
            # Best-effort only; task status can still be fetched via result backend.
            pass
        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "message": "Transposition task queued. Poll /api/loss/task/<task_id>/ for status.",
        })
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)
    except Exception as e:
        logger.exception("api_transpose_trigger: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required_api(allowed_roles=["admin"])
@require_http_methods(["GET"])
def api_task_status(request, task_id):
    """
    Get status of a loss_analytics Celery task (e.g. transposition, asset pipeline). Use for
    polling after triggering. Returns status (PENDING|SUCCESS|FAILURE|...),
    result when SUCCESS, error when FAILURE.
    """
    if not task_id:
        return JsonResponse({"error": "task_id is required"}, status=400)
    data = _get_task_status(task_id)
    return JsonResponse(data)


@login_required
@role_required_api(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_asset_range_trigger(request):
    """
    Trigger loss pipeline for an asset over a date range. Enqueues run_asset_loss_pipeline:
    optionally runs transposition, then one Celery task per string and per inverter.
    Returns orchestrator task_id immediately. Poll GET /api/loss/task/<task_id>/ for status;
    when SUCCESS, result contains string_tasks and inverter_tasks (each with device_id and task_id).

    POST body (JSON):
      asset_code: str
      start_date: str (ISO or date)
      end_date: str (ISO or date)
      time_interval_minutes: int (optional, default 15)
      run_transpose: bool (optional, default false)
      irradiance_device_id: str (required if run_transpose true)
      transpose_metric: str (optional, default "ghi")
    """
    try:
        body = json.loads(request.body) if request.body else {}
        asset_code = (body.get("asset_code") or "").strip()
        start_date = body.get("start_date")
        end_date = body.get("end_date")
        time_interval_minutes = int(body.get("time_interval_minutes", 15))
        run_transpose = bool(body.get("run_transpose", False))
        irradiance_device_id = (body.get("irradiance_device_id") or "").strip()
        transpose_metric = (body.get("transpose_metric") or "ghi").strip() or "ghi"

        if not asset_code:
            return JsonResponse({"error": "asset_code is required"}, status=400)
        if not start_date or not end_date:
            return JsonResponse({"error": "start_date and end_date are required"}, status=400)
        if run_transpose and not irradiance_device_id:
            return JsonResponse({"error": "irradiance_device_id is required when run_transpose is true"}, status=400)

        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return JsonResponse({"error": f"Asset {asset_code} not found"}, status=404)

        task = run_asset_loss_pipeline.apply_async(
            kwargs={
                "asset_code": asset_code,
                "start_date": start_date,
                "end_date": end_date,
                "time_interval_minutes": time_interval_minutes,
                "run_transpose": run_transpose,
                "irradiance_device_id": irradiance_device_id,
                "transpose_metric": transpose_metric,
            },
            queue="default",
        )
        try:
            log_loss_task_enqueued(
                task_id=task.id,
                task_name="loss_analytics.run_asset_loss_pipeline",
                asset_code=asset_code,
                user=getattr(request, "user", None),
            )
        except Exception:
            pass
        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "asset_code": asset_code,
            "asset_name": getattr(asset, "asset_name", None),
            "start_date": start_date,
            "end_date": end_date,
            "message": "Asset loss pipeline queued. Poll /api/loss/task/<task_id>/ for status.",
        })
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)
    except Exception as e:
        logger.exception("api_asset_range_trigger: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["GET"])
def api_get_loss_results(request):
    """
    Get loss calculation results for a device.
    GET /api/loss/results/?device_id=...&start_time=...&end_time=...&metric=...
    """
    try:
        device_id = request.GET.get("device_id")
        start_time_str = request.GET.get("start_time")
        end_time_str = request.GET.get("end_time")
        metric = request.GET.get("metric")

        if not device_id:
            return JsonResponse({"error": "device_id is required"}, status=400)

        end_time = timezone.now()
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            except ValueError:
                return JsonResponse({"error": "Invalid end_time format"}, status=400)
        start_time = end_time - timedelta(days=7)
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            except ValueError:
                return JsonResponse({"error": "Invalid start_time format"}, status=400)

        query = Q(device_id=device_id, ts__gte=start_time, ts__lte=end_time)
        if metric:
            query &= Q(metric=metric)
        else:
            query &= (
                Q(metric__icontains="expected_power")
                | Q(metric__icontains="actual_power")
                | Q(metric__icontains="power_loss")
                | Q(metric__icontains="loss_percentage")
            )
        data = timeseries_data.objects.filter(query).order_by("ts")
        results = []
        for row in data:
            try:
                value = float(row.value)
            except (ValueError, TypeError):
                continue
            results.append({
                "timestamp": row.ts.isoformat(),
                "metric": row.metric,
                "oem_metric": row.oem_metric,
                "value": value,
            })
        return JsonResponse({
            "success": True,
            "device_id": device_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "count": len(results),
            "data": results,
        })
    except Exception as e:
        logger.exception("api_get_loss_results: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["GET"])
def api_get_loss_summary(request):
    """
    Get loss calculation summary for a device or asset.
    GET /api/loss/summary/?device_id=...&hours=24
    GET /api/loss/summary/?asset_code=...&hours=24
    """
    try:
        device_id = request.GET.get("device_id")
        asset_code = request.GET.get("asset_code")
        hours = int(request.GET.get("hours", 24))
        if not device_id and not asset_code:
            return JsonResponse({"error": "device_id or asset_code is required"}, status=400)
        from loss_analytics.calculations import CalculationService
        calc_service = CalculationService()
        summary = calc_service.get_loss_summary(
            device_id=device_id,
            asset_code=asset_code,
            hours=hours,
        )
        return JsonResponse({"success": True, "summary": summary})
    except Exception as e:
        logger.exception("api_get_loss_summary: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["GET"])
def api_get_metric_mappings(request):
    """
    Get current metric mappings from device_mapping.
    GET /api/loss/metric-mappings/
    """
    try:
        from main.models import device_mapping
        from loss_analytics.calculations import MetricMappingService
        total_count = device_mapping.objects.filter(asset_code="loss_metrics").count()
        sample_rows = list(
            device_mapping.objects.filter(asset_code="loss_metrics").values(
                "device_type", "metric", "oem_tag", "asset_code"
            )[:10]
        )
        all_asset_codes = list(
            device_mapping.objects.values_list("asset_code", flat=True).distinct()[:20]
        )
        mapper = MetricMappingService()
        mappings = mapper.get_metric_mappings(force_refresh=True)
        formatted = {}
        for device_type, metrics in mappings.items():
            formatted[device_type] = {
                metric_name: {
                    "oem_tag": info["oem_tag"],
                    "units": info["units"],
                    "description": info["description"],
                }
                for metric_name, info in metrics.items()
            }
        validation = mapper.validate_mappings()
        return JsonResponse({
            "success": True,
            "debug": {
                "total_rows_with_loss_metrics": total_count,
                "sample_rows": sample_rows,
                "all_asset_codes_sample": all_asset_codes,
            },
            "mappings": formatted,
            "validation": validation,
        })
    except Exception as e:
        logger.exception("api_get_metric_mappings: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required_api(allowed_roles=["admin"])
@require_http_methods(["GET"])
def api_loss_events_list(request):
    """
    List loss events with filters and simple pagination.

    GET /api/loss/events/?asset_code=...&device_id=...&start_time=...&end_time=...&
        internal_state=...&is_legitimate=(true|false|null|pending)&page=1&page_size=50
    """
    try:
        asset_code = (request.GET.get("asset_code") or "").strip()
        device_id = (request.GET.get("device_id") or "").strip()
        internal_state = (request.GET.get("internal_state") or "").strip()
        legit_param = (request.GET.get("is_legitimate") or "").strip().lower()
        start_time_str = request.GET.get("start_time")
        end_time_str = request.GET.get("end_time")
        try:
            page = int(request.GET.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get("page_size", 50))
        except (TypeError, ValueError):
            page_size = 50
        page = max(page, 1)
        page_size = max(min(page_size, 500), 1)

        qs = LossEvent.objects.all()
        if asset_code:
            qs = qs.filter(asset_code=asset_code)
        if device_id:
            qs = qs.filter(device_id=device_id)
        if internal_state:
            qs = qs.filter(internal_state=internal_state)

        if legit_param in {"true", "false", "null", "pending"}:
            if legit_param == "true":
                qs = qs.filter(is_legitimate=True)
            elif legit_param == "false":
                qs = qs.filter(is_legitimate=False)
            else:
                qs = qs.filter(is_legitimate__isnull=True)

        if start_time_str:
            try:
                start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            except ValueError:
                return JsonResponse({"error": "Invalid start_time format"}, status=400)
            qs = qs.filter(end_ts__gte=start_dt)
        if end_time_str:
            try:
                end_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            except ValueError:
                return JsonResponse({"error": "Invalid end_time format"}, status=400)
            qs = qs.filter(start_ts__lte=end_dt)

        total = qs.count()
        offset = (page - 1) * page_size
        events = list(
            qs.order_by("-start_ts")[offset : offset + page_size].values(
                "id",
                "asset_code",
                "device_id",
                "start_ts",
                "end_ts",
                "internal_state",
                "oem_state_label",
                "loss_kwh",
                "is_legitimate",
                "confirmed_at",
                "confirmed_by_id",
            )
        )

        def _format_event(ev: dict) -> dict:
            return {
                "id": ev["id"],
                "asset_code": ev["asset_code"],
                "device_id": ev["device_id"],
                "start_ts": ev["start_ts"].isoformat() if ev["start_ts"] else None,
                "end_ts": ev["end_ts"].isoformat() if ev["end_ts"] else None,
                "internal_state": ev["internal_state"],
                "oem_state_label": ev["oem_state_label"],
                "loss_kwh": float(ev["loss_kwh"]) if ev["loss_kwh"] is not None else None,
                "is_legitimate": ev["is_legitimate"],
                "confirmed_at": ev["confirmed_at"].isoformat() if ev["confirmed_at"] else None,
                "confirmed_by_id": ev["confirmed_by_id"],
            }

        data = [_format_event(ev) for ev in events]
        total_pages = (total + page_size - 1) // page_size if total else 0

        return JsonResponse(
            {
                "success": True,
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        )
    except Exception as e:
        logger.exception("api_loss_events_list: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required_api(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_loss_event_update_legitimacy(request):
    """
    Update is_legitimate for a loss event and write an audit log entry.

    POST /api/loss/events/update-legitimacy/
    {
      "id": 123,
      "is_legitimate": true   // or false or null
    }
    """
    try:
        body = json.loads(request.body or "{}")
        event_id = body.get("id")
        if not event_id:
            return JsonResponse({"error": "id is required"}, status=400)
        if "is_legitimate" not in body:
            return JsonResponse({"error": "is_legitimate is required"}, status=400)
        raw_val = body.get("is_legitimate")
        if raw_val is None:
            new_value = None
        elif isinstance(raw_val, bool):
            new_value = raw_val
        elif isinstance(raw_val, str):
            v = raw_val.strip().lower()
            if v in {"true", "1", "yes"}:
                new_value = True
            elif v in {"false", "0", "no"}:
                new_value = False
            elif v in {"null", "none", "pending"}:
                new_value = None
            else:
                return JsonResponse({"error": "Invalid is_legitimate value"}, status=400)
        else:
            return JsonResponse({"error": "Invalid is_legitimate value type"}, status=400)

        try:
            ev = LossEvent.objects.get(id=event_id)
        except LossEvent.DoesNotExist:
            return JsonResponse({"error": f"LossEvent {event_id} not found"}, status=404)

        old_value = ev.is_legitimate
        if old_value == new_value:
            return JsonResponse(
                {
                    "success": True,
                    "message": "No change",
                    "id": ev.id,
                    "is_legitimate": ev.is_legitimate,
                }
            )

        ev.is_legitimate = new_value
        ev.confirmed_by = getattr(request, "user", None)
        ev.confirmed_at = timezone.now()
        ev.save(update_fields=["is_legitimate", "confirmed_by", "confirmed_at", "updated_at"])

        try:
            LossEventConfirmationLog.objects.create(
                loss_event=ev,
                user=getattr(request, "user", None),
                old_value=old_value,
                new_value=new_value,
            )
        except Exception:
            # Best-effort audit; do not fail the main update on logging error.
            logger.exception(
                "Failed to create LossEventConfirmationLog for event %s", ev.id
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Legitimacy updated",
                "id": ev.id,
                "is_legitimate": ev.is_legitimate,
                "confirmed_at": ev.confirmed_at.isoformat() if ev.confirmed_at else None,
                "confirmed_by_id": ev.confirmed_by_id,
            }
        )
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)
    except Exception as e:
        logger.exception("api_loss_event_update_legitimacy: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required_api(allowed_roles=["admin"])
@require_http_methods(["GET"])
def api_loss_event_logs(request, event_id: int):
    """
    Return confirmation/audit logs for a single LossEvent.

    GET /api/loss/events/<event_id>/logs/
    """
    try:
        try:
            ev = LossEvent.objects.get(id=event_id)
        except LossEvent.DoesNotExist:
            return JsonResponse({"error": f"LossEvent {event_id} not found"}, status=404)

        logs_qs = (
            LossEventConfirmationLog.objects.filter(loss_event=ev)
            .select_related("user")
            .order_by("created_at")
            .values("id", "created_at", "old_value", "new_value", "user__username", "user_id")
        )

        logs = [
            {
                "id": row["id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "old_value": row["old_value"],
                "new_value": row["new_value"],
                "user_id": row["user_id"],
                "username": row["user__username"],
            }
            for row in logs_qs
        ]

        return JsonResponse({"success": True, "data": logs})
    except Exception as e:
        logger.exception("api_loss_event_logs: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required_api(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_inverter_expected_power_trigger(request):
    """
    Trigger inverter expected power calculation via Celery for one or more inverters.

    POST /api/loss/inverter/expected-power/
    {
      "asset_code": "ASSET_CODE",
      "inverter_ids": ["INV1", "INV2"],
      "start_date": "2026-03-01T00:00:00",
      "end_date": "2026-03-02T00:00:00",
      "inverter_efficiency": 0.97  // optional
    }

    Returns:
      {
        "success": true,
        "asset_code": "...",
        "tasks": [
          {"inverter_id": "INV1", "task_id": "..."},
          {"inverter_id": "INV2", "task_id": "..."}
        ]
      }
    """
    try:
        body = json.loads(request.body or "{}")
        asset_code = (body.get("asset_code") or "").strip()
        inverter_ids = body.get("inverter_ids") or []
        start_date = body.get("start_date")
        end_date = body.get("end_date")
        inverter_efficiency = float(body.get("inverter_efficiency", 0.97))

        if not asset_code:
            return JsonResponse({"error": "asset_code is required"}, status=400)
        if not inverter_ids or not isinstance(inverter_ids, list):
            return JsonResponse({"error": "inverter_ids (list) is required"}, status=400)
        if not start_date or not end_date:
            return JsonResponse({"error": "start_date and end_date are required"}, status=400)

        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return JsonResponse({"error": f"Asset {asset_code} not found"}, status=404)

        tasks_info = []
        from loss_analytics.tasks import run_inverter_expected_power_for_date_range

        for inv_id in inverter_ids:
            inv_id_str = (inv_id or "").strip()
            if not inv_id_str:
                continue
            t = run_inverter_expected_power_for_date_range.apply_async(
                kwargs={
                    "inverter_id": inv_id_str,
                    "asset_code": asset_code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "inverter_efficiency": inverter_efficiency,
                },
                queue="default",
            )
            tasks_info.append({"inverter_id": inv_id_str, "task_id": t.id})

        if not tasks_info:
            return JsonResponse({"error": "No valid inverter_ids provided"}, status=400)

        return JsonResponse(
            {
                "success": True,
                "asset_code": asset_code,
                "asset_name": getattr(asset, "asset_name", None),
                "start_date": start_date,
                "end_date": end_date,
                "tasks": tasks_info,
                "message": "Inverter expected power tasks queued. Poll /api/loss/task/<task_id>/ for status.",
            }
        )
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)
    except Exception as e:
        logger.exception("api_inverter_expected_power_trigger: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


# --- Legacy endpoints (api/loss-calculation/string/, strings/batch/, asset/) ---
# These are wired from main.urls so main.views does not need loss_calculation_views
# (which depends on main.calculations). Keeps URL names and paths unchanged.


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_trigger_string_calculation(request):
    """
    Trigger loss calculation for a single string device (synchronous for testing).
    POST /api/loss-calculation/string/
    """
    try:
        data = json.loads(request.body) if request.body else {}
        device_id = data.get("device_id")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        time_interval_minutes = int(data.get("time_interval_minutes", 15))

        if not device_id:
            return JsonResponse({"error": "device_id is required"}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({"error": "start_date and end_date are required"}, status=400)

        try:
            if "Z" in start_date_str or "+" in start_date_str or start_date_str.count("-") > 2:
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            else:
                start_date = datetime.fromisoformat(start_date_str)
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            if "Z" in end_date_str or "+" in end_date_str or end_date_str.count("-") > 2:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            else:
                end_date = datetime.fromisoformat(end_date_str)
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)

        from loss_analytics.calculations import CalculationService
        calc_service = CalculationService()
        result = calc_service.calculate_string_loss_sync(
            device_id=device_id,
            start_date=start_date,
            end_date=end_date,
            time_interval_minutes=time_interval_minutes,
        )
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("api_trigger_string_calculation: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_trigger_strings_batch(request):
    """
    Legacy: batch string loss by timestamp. Prefer POST /api/loss/asset/range/ with
    start_date and end_date. Returns task_id: null and a message.
    POST /api/loss-calculation/strings/batch/
    """
    try:
        data = json.loads(request.body) if request.body else {}
        device_ids = data.get("device_ids", [])
        if not device_ids:
            return JsonResponse({"error": "device_ids is required"}, status=400)
        return JsonResponse({
            "success": True,
            "task_id": None,
            "device_count": len(device_ids),
            "message": "Use POST /api/loss/asset/range/ or POST /api/loss-calculation/asset/range/ with start_date and end_date for loss calculation.",
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("api_trigger_strings_batch: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required(allowed_roles=["admin"])
@require_http_methods(["POST"])
def api_trigger_asset_calculation(request):
    """
    Trigger loss calculations for all devices in an asset. Converts optional
    timestamp to that day's date range and enqueues run_asset_loss_pipeline.
    POST /api/loss-calculation/asset/
    """
    try:
        data = json.loads(request.body) if request.body else {}
        asset_code = data.get("asset_code")
        timestamp_str = data.get("timestamp")
        if not asset_code:
            return JsonResponse({"error": "asset_code is required"}, status=400)
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return JsonResponse({"error": f"Asset {asset_code} not found"}, status=404)

        if timestamp_str:
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timezone.is_naive(ts):
                    ts = timezone.make_aware(ts)
            except ValueError:
                return JsonResponse({"error": "Invalid timestamp format"}, status=400)
            start_date = ts.date().isoformat()
            end_dt = ts.replace(hour=23, minute=59, second=59, microsecond=999999)
            end_dt = end_dt + timedelta(seconds=1)
            end_date = end_dt.date().isoformat()
        else:
            from django.utils import timezone as django_tz
            now = django_tz.now()
            start_date = now.date().isoformat()
            end_date = start_date

        task = run_asset_loss_pipeline.apply_async(
            kwargs={
                "asset_code": asset_code,
                "start_date": start_date,
                "end_date": end_date,
            },
            queue="default",
        )
        try:
            log_loss_task_enqueued(
                task_id=task.id,
                task_name="loss_analytics.run_asset_loss_pipeline",
                asset_code=asset_code,
                user=getattr(request, "user", None),
            )
        except Exception:
            pass
        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "asset_code": asset_code,
            "asset_name": asset.asset_name,
            "message": "Asset loss calculation task queued. Poll /api/loss/task/<task_id>/ for status.",
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("api_trigger_asset_calculation: %s", e)
        return JsonResponse({"error": str(e)}, status=500)
