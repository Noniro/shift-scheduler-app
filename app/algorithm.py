from . import db
from .models import Worker, ScheduledShift, Constraint, ShiftDefinition, SchedulingPeriod # Added SchedulingPeriod
from datetime import datetime, timedelta
from flask import current_app

def is_worker_available(worker, scheduled_assignment_object, active_period: SchedulingPeriod):
    # scheduled_assignment_object is a ScheduledShift instance (placeholder)
    # It links to a ShiftDefinition instance (the actual slot to fill)
    slot_def = ShiftDefinition.query.get(scheduled_assignment_object.shift_definition_id)
    if not slot_def:
        current_app.logger.error(f"Algorithm Error: Could not find ShiftDefinition for ScheduledShift ID {scheduled_assignment_object.id}")
        return False # Should not happen

    # Check worker's general unavailability constraints
    for constraint in worker.constraints.filter_by(constraint_type="UNAVAILABLE_DAY_RANGE").all():
        # Slot (slot_def) overlaps with constraint if:
        # (SlotStart < ConstraintEnd) and (SlotEnd > ConstraintStart)
        if slot_def.slot_start_datetime < constraint.end_datetime and \
           slot_def.slot_end_datetime > constraint.start_datetime:
            # current_app.logger.debug(f"Worker {worker.name} unavailable for slot {slot_def.id} due to constraint {constraint.id}")
            return False
    return True

def assign_shifts_fairly(all_pending_assignments, workers, active_period: SchedulingPeriod):
    """
    Assigns workers to pending ScheduledShift objects for the given active_period.
    Modifies worker_id on these objects.
    Returns a tuple: (bool_success, list_of_messages)
    """
    algo_messages = []

    if not workers:
        algo_messages.append(("error", "No workers available to assign shifts."))
        return False, algo_messages
    if not all_pending_assignments:
        algo_messages.append(("info", f"No shifts were pending assignment for period '{active_period.name}'."))
        return True, algo_messages

    def get_start_time(assign_obj):
        # assign_obj.defined_slot should be pre-loaded or fetched efficiently
        # For simplicity, direct query if not eager loaded.
        sd = getattr(assign_obj, 'defined_slot', None) or ShiftDefinition.query.get(assign_obj.shift_definition_id)
        return sd.slot_start_datetime if sd else datetime.max
    
    all_pending_assignments.sort(key=get_start_time)

    worker_assignment_count = {w.id: 0 for w in workers}
    worker_assigned_hours_in_period = {w.id: 0.0 for w in workers} # Hours for this active_period
    unassigned_count = 0

    # Pre-fetch all slot definitions for the pending assignments to reduce DB queries in loop
    slot_ids = [pa.shift_definition_id for pa in all_pending_assignments]
    slot_definitions_map = {sd.id: sd for sd in ShiftDefinition.query.filter(ShiftDefinition.id.in_(slot_ids)).all()}


    for assignment_obj in all_pending_assignments: # These are ScheduledShift instances
        slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
        if not slot_def:
            current_app.logger.error(f"Algorithm: Pre-fetched ShiftDefinition not found for ID {assignment_obj.shift_definition_id}")
            unassigned_count += 1
            continue

        assigned_this_slot = False
        # Sort workers by current assigned hours to try and balance load
        sorted_workers = sorted(workers, key=lambda w: worker_assigned_hours_in_period[w.id])

        for worker in sorted_workers:
            if not is_worker_available(worker, assignment_obj, active_period):
                continue

            # Check for Overlapping Shifts for THIS WORKER within THIS BATCH of assignments
            is_overlapping = False
            # Iterate through all_pending_assignments again to find those already assigned to *this* worker
            for other_assignment_obj in all_pending_assignments:
                if other_assignment_obj.worker_id == worker.id and other_assignment_obj.id != assignment_obj.id:
                    other_slot_def = slot_definitions_map.get(other_assignment_obj.shift_definition_id)
                    if not other_slot_def: continue

                    if max(slot_def.slot_start_datetime, other_slot_def.slot_start_datetime) < \
                       min(slot_def.slot_end_datetime, other_slot_def.slot_end_datetime):
                        is_overlapping = True
                        break
            if is_overlapping:
                continue
            
            # Check Max Hours for the period (if worker.max_hours_per_week is set)
            if worker.max_hours_per_week: # Interpreting this as max hours for *this scheduling period*
                current_slot_hours = slot_def.duration_total_seconds / 3600.0
                if (worker_assigned_hours_in_period[worker.id] + current_slot_hours) > worker.max_hours_per_week:
                    continue # Worker would exceed max hours for this period

            # If all hard constraints pass, assign the worker
            assignment_obj.worker_id = worker.id
            worker_assignment_count[worker.id] += 1
            worker_assigned_hours_in_period[worker.id] += (slot_def.duration_total_seconds / 3600.0)
            assigned_this_slot = True
            break # Move to the next slot (assignment_obj)

        if not assigned_this_slot:
            unassigned_count += 1
            algo_messages.append(("warning", f"Could not assign worker to slot: {slot_def.name} starting {slot_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}"))
    
    try:
        db.session.commit() # Commit all worker_id changes to ScheduledShift instances
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Algorithm: Error committing shift assignments: {e}")
        algo_messages.append(("error", f"Database error during assignment commit: {e}"))
        return False, algo_messages

    if unassigned_count > 0:
        algo_messages.append(("info", f"{unassigned_count} of {len(all_pending_assignments)} shifts remain unassigned for period '{active_period.name}'."))
        # It's not necessarily a failure if some are unassigned, but good to note.
        # The definition of "success" depends on whether all shifts *must* be filled.
        # For now, let's say it's a partial success if some are assigned.
        return False, algo_messages 
            
    algo_messages.append(("success", f"All {len(all_pending_assignments)} shifts assigned for period '{active_period.name}'."))
    return True, algo_messages