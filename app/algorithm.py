from . import db
from .models import Worker, ScheduledShift, Constraint, ShiftDefinition, SchedulingPeriod, JobRole
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.orm import joinedload

def is_worker_qualified_for_slot(worker: Worker, slot_def: ShiftDefinition):
    """Checks if a worker is qualified for the job role of a given shift slot."""
    if not slot_def.job_role:
        current_app.logger.error(f"Slot Definition {slot_def.id} has no associated JobRole.")
        return False
    
    worker_qualified_role_ids = {role.id for role in worker.qualified_roles}
    return slot_def.job_role_id in worker_qualified_role_ids


def is_worker_available_for_slot(worker: Worker, slot_def: ShiftDefinition):
    """
    Checks all of a worker's hard constraints:
    1. Role Qualification
    2. Unavailability periods (from worker constraints)
    This function replaces the old 'is_worker_available' to be more direct.
    """
    # 1. Check Role Qualification
    if not is_worker_qualified_for_slot(worker, slot_def):
        return False

    # 2. Check Unavailability Constraints
    # Assumes constraints are loaded with worker or queried efficiently.
    # The `worker` object passed in should have its constraints pre-loaded.
    for constraint in worker.constraints:
        # Check for any overlap between the shift and the constraint period
        if slot_def.slot_start_datetime < constraint.end_datetime and \
           slot_def.slot_end_datetime > constraint.start_datetime:
            return False
            
    return True


def assign_shifts_fairly(all_pending_assignments, workers, active_period: SchedulingPeriod):
    algo_messages = []
    if not workers:
        algo_messages.append(("error", "No workers available to assign shifts."))
        return False, algo_messages
    if not all_pending_assignments:
        algo_messages.append(("info", f"No shifts were pending assignment for period '{active_period.name}'."))
        return True, algo_messages

    # Eagerly load all required data to minimize DB queries inside the loop.
    # We need workers with their constraints and qualified roles.
    # The 'workers' object passed in should already have this eager-loaded.
    
    # Pre-fetch all slot definitions and their job roles for the pending assignments
    slot_ids = [pa.shift_definition_id for pa in all_pending_assignments]
    slot_definitions_map = {
        sd.id: sd for sd in ShiftDefinition.query.options(
            joinedload(ShiftDefinition.job_role)  # Eager load job_role which contains the multiplier
        ).filter(ShiftDefinition.id.in_(slot_ids)).all()
    }

    # Sort pending assignments by their underlying slot's start time
    def get_start_time(assign_obj):
        sd = slot_definitions_map.get(assign_obj.shift_definition_id)
        return sd.slot_start_datetime if sd else datetime.max
    all_pending_assignments.sort(key=get_start_time)

    # --- KEY CHANGE: INITIALIZE TWO DICTIONARIES ---
    # 1. For REAL hours (for max hour constraints and stats)
    worker_assigned_hours_in_period = {w.id: 0.0 for w in workers}
    
    # 2. For WEIGHTED hours (for balancing the workload fairly)
    worker_weighted_hours = {w.id: 0.0 for w in workers}
    
    # Track which assignments have been given to which worker in this run
    # to prevent double-booking within the loop.
    worker_shift_assignments_in_run = {w.id: [] for w in workers}

    unassigned_count = 0

    for assignment_obj in all_pending_assignments:
        slot_def = slot_definitions_map.get(assignment_obj.shift_definition_id)
        if not slot_def:
            current_app.logger.error(f"Algorithm: Pre-fetched ShiftDefinition not found for ID {assignment_obj.shift_definition_id}")
            algo_messages.append(("warning", f"Could not process a shift because its definition was missing. Please regenerate slots."))
            unassigned_count += 1
            continue

        assigned_this_slot = False
        
        # --- KEY CHANGE: SORT WORKERS BY WEIGHTED HOURS ---
        # Sort workers by their current WEIGHTED hours to find the one with the least effort assigned so far.
        sorted_workers = sorted(workers, key=lambda w: worker_weighted_hours[w.id])

        for worker in sorted_workers:
            # 1. Check hard constraints (availability, qualification)
            if not is_worker_available_for_slot(worker, slot_def):
                continue

            # 2. Check for overlapping shifts assigned *in this algorithm run*
            is_overlapping = False
            for other_assigned_slot in worker_shift_assignments_in_run[worker.id]:
                if max(slot_def.slot_start_datetime, other_assigned_slot.slot_start_datetime) < \
                   min(slot_def.slot_end_datetime, other_assigned_slot.slot_end_datetime):
                    is_overlapping = True
                    break
            if is_overlapping:
                continue
            
            # 3. Check max hours constraint using REAL hours
            if worker.max_hours_per_week:
                current_slot_real_hours = slot_def.duration_total_seconds / 3600.0
                if (worker_assigned_hours_in_period[worker.id] + current_slot_real_hours) > worker.max_hours_per_week:
                    continue

            # --- ASSIGN THE SHIFT AND UPDATE BOTH COUNTERS ---
            assignment_obj.worker_id = worker.id
            
            # Calculate real duration in hours
            real_duration_hours = slot_def.duration_total_seconds / 3600.0
            
            # Get the difficulty multiplier from the job role
            multiplier = slot_def.job_role.difficulty_multiplier
            
            # Update REAL hours
            worker_assigned_hours_in_period[worker.id] += real_duration_hours
            
            # Update WEIGHTED hours
            worker_weighted_hours[worker.id] += real_duration_hours * multiplier
            
            # Record this assignment for overlap checking in this run
            worker_shift_assignments_in_run[worker.id].append(slot_def)
            
            assigned_this_slot = True
            break  # Move to the next shift assignment

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