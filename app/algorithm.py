from . import db
from .models import Worker, ScheduledShift, Constraint, ShiftDefinition, SchedulingPeriod, JobRole
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.orm import joinedload

# TODO: Understand the app.db session management and how to handle transactions properly, and converting more files (csv, json) to this format

def is_worker_qualified_for_slot(worker: Worker, slot_def: ShiftDefinition):
    # worker.qualified_roles is a list of JobRole objects if eager loaded with 'subquery' or 'selectinload'
    # slot_def.job_role is a JobRole object if eager loaded or accessed (triggering a load)
    if not slot_def.job_role: # Should not happen if data is consistent
        current_app.logger.error(f"Slot Definition {slot_def.id} has no associated JobRole.")
        return False
    
    # Check if the specific job_role object of the slot is in the worker's list of qualified_roles
    # This relies on object identity or proper __eq__ if they are different instances representing same DB row.
    # Using IDs is safer if instances might differ.
    worker_qualified_role_ids = {role.id for role in worker.qualified_roles}
    return slot_def.job_role_id in worker_qualified_role_ids


def is_worker_available(worker: Worker, scheduled_assignment_object: ScheduledShift, active_period: SchedulingPeriod, slot_def_map):
    # slot_def = getattr(scheduled_assignment_object, 'defined_slot', None)
    # if not slot_def: # Fallback if not preloaded via relationship
    slot_def = slot_def_map.get(scheduled_assignment_object.shift_definition_id)
    
    if not slot_def:
        current_app.logger.error(f"Algorithm Error: Could not find ShiftDefinition for ScheduledShift ID {scheduled_assignment_object.id}")
        return False

    # 1. Check Role Qualification
    if not is_worker_qualified_for_slot(worker, slot_def):
        # current_app.logger.debug(f"Worker {worker.name} not qualified for role {slot_def.job_role.name} of slot {slot_def.id}")
        return False

    # 2. Check Unavailability Constraints
    for constraint in worker.constraints: # Assumes constraints are loaded with worker or queried efficiently
        if slot_def.slot_start_datetime < constraint.end_datetime and \
           slot_def.slot_end_datetime > constraint.start_datetime:
            # current_app.logger.debug(f"Worker {worker.name} unavailable for slot {slot_def.id} due to constraint {constraint.id}")
            return False
    return True


def assign_shifts_fairly(all_pending_assignments, workers, active_period: SchedulingPeriod):
    algo_messages = []
    if not workers:
        algo_messages.append(("error", "No workers available to assign shifts.")); return False, algo_messages
    if not all_pending_assignments:
        algo_messages.append(("info", f"No shifts were pending assignment for period '{active_period.name}'."))
        return True, algo_messages

    # Pre-fetch all slot definitions and their job roles for the pending assignments
    slot_ids = [pa.shift_definition_id for pa in all_pending_assignments]
    slot_definitions_map = {
        sd.id: sd for sd in ShiftDefinition.query.options(
            joinedload(ShiftDefinition.job_role) # Eager load job_role for each slot_def
        ).filter(ShiftDefinition.id.in_(slot_ids)).all()
    }

    # Sort pending assignments by their underlying slot's start time
    def get_start_time(assign_obj):
        sd = slot_definitions_map.get(assign_obj.shift_definition_id)
        return sd.slot_start_datetime if sd else datetime.max
    all_pending_assignments.sort(key=get_start_time)

    worker_assignment_count = {w.id: 0 for w in workers}
    worker_assigned_hours_in_period = {w.id: 0.0 for w in workers}
    unassigned_count = 0


    for assignment_obj in all_pending_assignments:
        slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
        if not slot_def:
            current_app.logger.error(f"Algorithm: Pre-fetched ShiftDefinition not found for ID {assignment_obj.shift_definition_id}")
            unassigned_count += 1
            continue

        assigned_this_slot = False
        # Workers should have their qualified_roles eager loaded when fetched before calling this function
        sorted_workers = sorted(workers, key=lambda w: worker_assigned_hours_in_period[w.id])

        for worker in sorted_workers:
            if not is_worker_available(worker, assignment_obj, active_period, slot_definitions_map): # Pass map
                continue

            is_overlapping = False
            for other_ass_obj in all_pending_assignments:
                if other_ass_obj.worker_id == worker.id and other_ass_obj.id != assignment_obj.id:
                    other_slot_def = slot_definitions_map.get(other_ass_obj.shift_definition_id)
                    if not other_slot_def: continue
                    if max(slot_def.slot_start_datetime, other_slot_def.slot_start_datetime) < \
                       min(slot_def.slot_end_datetime, other_slot_def.slot_end_datetime):
                        is_overlapping = True; break
            if is_overlapping: continue
            
            if worker.max_hours_per_week:
                current_slot_hours = slot_def.duration_total_seconds / 3600.0
                if (worker_assigned_hours_in_period[worker.id] + current_slot_hours) > worker.max_hours_per_week:
                    continue

            assignment_obj.worker_id = worker.id
            worker_assignment_count[worker.id] += 1
            worker_assigned_hours_in_period[worker.id] += (slot_def.duration_total_seconds / 3600.0)
            assigned_this_slot = True; break 

        if not assigned_this_slot:
            unassigned_count += 1
            algo_messages.append(("warning", f"Could not assign worker to: {slot_def.name} starting {slot_def.slot_start_datetime.strftime('%Y-%m-%d %H:%M')}"))
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Algorithm: Error committing assignments: {e}")
        algo_messages.append(("error", f"Database error during assignment commit: {e}"))
        return False, algo_messages

    if unassigned_count > 0:
        algo_messages.append(("info", f"{unassigned_count} of {len(all_pending_assignments)} shifts remain unassigned for period '{active_period.name}'."))
        return False, algo_messages # False indicates not all were assigned
            
    algo_messages.append(("success", f"All {len(all_pending_assignments)} shifts assigned for period '{active_period.name}'."))
    return True, algo_messages