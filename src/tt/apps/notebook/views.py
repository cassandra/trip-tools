import json
import logging
from datetime import date as date_class, datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from tt.apps.trips.models import Trip

from .forms import NotebookEntryForm
from .models import NotebookEntry

logger = logging.getLogger(__name__)


class NotebookListView(LoginRequiredMixin, View):
    """Show all notebook entries for a trip (chronological order)."""

    def get(self, request, trip_id: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404(Trip, pk=trip_id, user=request.user)
        entries = trip.notebook_entries.all()

        context = {
            'trip': trip,
            'entries': entries,
        }

        return render(request, 'notebook/pages/list.html', context)


class NotebookEditView(LoginRequiredMixin, View):
    """Edit or create a notebook entry."""

    def get(self, request, trip_id: int, entry_pk: int = None, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404(Trip, pk=trip_id, user=request.user)

        if entry_pk:
            # Editing existing entry
            entry = get_object_or_404(
                NotebookEntry,
                pk=entry_pk,
                trip=trip,
                user=request.user
            )
        else:
            # Creating new entry - create it immediately so auto-save works
            entry = NotebookEntry.objects.create(
                user=request.user,
                trip=trip,
                date=date_class.today(),
                text=''
            )
            return redirect('notebook_edit', trip_id=trip.pk, entry_pk=entry.pk)

        form = NotebookEntryForm(instance=entry, trip=trip)

        context = {
            'trip': trip,
            'form': form,
            'entry': entry,
        }

        return render(request, 'notebook/pages/editor.html', context)

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> HttpResponse:
        trip = get_object_or_404(Trip, pk=trip_id, user=request.user)
        entry = get_object_or_404(
            NotebookEntry,
            pk=entry_pk,
            trip=trip,
            user=request.user
        )

        form = NotebookEntryForm(request.POST, instance=entry, trip=trip)

        if form.is_valid():
            with transaction.atomic():
                form.save()

            return redirect('notebook_edit', trip_id=trip.pk, entry_pk=entry.pk)

        context = {
            'trip': trip,
            'form': form,
            'entry': entry,
        }

        return render(request, 'notebook/pages/editor.html', context, status=400)


class NotebookAutoSaveView(LoginRequiredMixin, View):
    """AJAX endpoint for auto-saving notebook entries."""

    def get(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        # Return 405 Method Not Allowed for GET requests
        return JsonResponse(
            {'status': 'error', 'message': 'Method not allowed'},
            status=405
        )

    def post(self, request, trip_id: int, entry_pk: int, *args, **kwargs) -> JsonResponse:
        trip = get_object_or_404(Trip, pk=trip_id, user=request.user)
        entry = get_object_or_404(
            NotebookEntry,
            pk=entry_pk,
            trip=trip,
            user=request.user
        )

        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            date_str = data.get('date')
        except json.JSONDecodeError:
            logger.warning('Invalid JSON in auto-save request')
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON'},
                status=400
            )

        if date_str:
            try:
                new_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f'Invalid date format: {date_str}')
                return JsonResponse(
                    {'status': 'error', 'message': 'Invalid date format'},
                    status=400
                )

            if new_date != entry.date:
                existing = NotebookEntry.objects.filter(
                    trip=trip,
                    date=new_date
                ).exclude(pk=entry.pk)

                if existing.exists():
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': f'An entry for {new_date.strftime("%B %d, %Y")} already exists.'
                        },
                        status=400
                    )
        try:
            with transaction.atomic():
                entry.text = text
                if date_str:
                    entry.date = new_date
                entry.save()

            return JsonResponse({
                'status': 'success',
                'modified_datetime': entry.modified_datetime.isoformat(),
            })

        except (IntegrityError, DatabaseError) as e:
            logger.error(f'Error auto-saving notebook entry: {e}')
            return JsonResponse(
                {'status': 'error', 'message': 'Failed to save entry'},
                status=500
            )
