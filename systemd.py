import asyncio
from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from langchain_core.tools import tool
import logging
from typing import List, Dict, Any

async def _get_systemd_objects():
    """Helper to get systemd bus and manager objects."""
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    introspection = await bus.introspect('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    obj = bus.get_proxy_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1', introspection)
    manager = obj.get_interface('org.freedesktop.systemd1.Manager')
    return bus, manager

@tool
async def get_unit_status(unit_name: str) -> str:
    """Gets the status of a single systemd unit. Wildcards are not supported. If the unit name has no suffix, '.service' is appended."""
    if '.' not in unit_name:
        unit_name = f"{unit_name}.service"
    try:
        bus, manager = await _get_systemd_objects()

        unit_path = await manager.call_get_unit(unit_name)  # type: ignore
        unit_introspection = await bus.introspect('org.freedesktop.systemd1', unit_path)
        unit_obj = bus.get_proxy_object('org.freedesktop.systemd1', unit_path, unit_introspection)
        unit_props = unit_obj.get_interface('org.freedesktop.DBus.Properties')

        active_state = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'ActiveState')  # type: ignore
        return active_state.value
    except Exception as e:
        logging.error(f"Error getting status for unit '{unit_name}':", exc_info=True)
        return f"An error occurred while getting status for {unit_name}: {e}"

@tool
async def get_journal_logs(unit_name: str, lines: int = 10) -> str:
    """Gets the last N lines of the journal for a systemd unit. If the unit name has no suffix, '.service' is appended."""
    if '.' not in unit_name:
        unit_name = f"{unit_name}.service"
    try:
        command = ['journalctl', '-u', unit_name, '-n', str(lines), '--no-pager']
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_message = stderr.decode().strip()
            logging.error(f"Error getting journal logs for unit '{unit_name}': {error_message}")
            return f"Error getting journal logs for {unit_name}: {error_message}"

        return stdout.decode().strip()

    except FileNotFoundError:
        logging.error("`journalctl` command not found.")
        return "`journalctl` command not found. Please ensure it is installed and in the system's PATH."
    except Exception as e:
        logging.error(f"Error getting journal logs for unit '{unit_name}':", exc_info=True)
        return f"An unexpected error occurred while getting journal logs for {unit_name}: {e}"

@tool
async def get_unit_dependencies(unit_name: str) -> Dict[str, Any]:
    """Gets the dependency information of a systemd unit via D-Bus as structured data. If the unit name has no suffix, '.service' is appended."""
    if '.' not in unit_name:
        unit_name = f"{unit_name}.service"
    try:
        bus, manager = await _get_systemd_objects()

        unit_path = await manager.call_get_unit(unit_name)  # type: ignore
        unit_introspection = await bus.introspect('org.freedesktop.systemd1', unit_path)
        unit_obj = bus.get_proxy_object('org.freedesktop.systemd1', unit_path, unit_introspection)
        unit_props = unit_obj.get_interface('org.freedesktop.DBus.Properties')

        # Get various dependency properties
        requires = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'Requires')  # type: ignore
        wants = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'Wants')  # type: ignore
        after = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'After')  # type: ignore
        before = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'Before')  # type: ignore
        required_by = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'RequiredBy')  # type: ignore
        wanted_by = await unit_props.call_get('org.freedesktop.systemd1.Unit', 'WantedBy')  # type: ignore

        # Create structured dependency data
        dependency_data: Dict[str, Any] = {
            "unit_name": unit_name,
            "dependencies": {
                "requires": list(requires.value) if requires.value else [],
                "wants": list(wants.value) if wants.value else [],
                "after": list(after.value) if after.value else [],
                "before": list(before.value) if before.value else [],
                "required_by": list(required_by.value) if required_by.value else [],
                "wanted_by": list(wanted_by.value) if wanted_by.value else []
            },
            "summary": {
                "total_dependencies": len(requires.value or []) + len(wants.value or []),
                "total_dependents": len(required_by.value or []) + len(wanted_by.value or []),
                "has_hard_dependencies": bool(requires.value),
                "has_soft_dependencies": bool(wants.value),
                "has_dependents": bool(required_by.value or wanted_by.value)
            }
        }

        return dependency_data

    except Exception as e:
        logging.error(f"Error getting dependencies for unit '{unit_name}':", exc_info=True)
        return {
            "unit_name": unit_name,
            "error": str(e),
            "dependencies": None
        }

@tool
async def list_failed_units() -> List[str]:
    """Gets a list of failed systemd units."""
    try:
        _, manager = await _get_systemd_objects()

        units = await manager.call_list_units()  # type: ignore

        failed_units = [unit[0] for unit in units if unit[3] == 'failed']

        return failed_units
    except Exception:
        logging.error("Error listing failed units:", exc_info=True)
        raise